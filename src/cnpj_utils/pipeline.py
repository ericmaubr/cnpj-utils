from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
import aiosqlite
import pandas as pd
from tqdm.asyncio import tqdm_asyncio

from .api_parser import extract_cnaes_from_payload
from .classification import SecondaryCnae, classificar_com_fallback
from .cnae_catalog import build_cnae_lookup, fill_missing_descriptions
from .utils import limpar_cnpj

CnpjResult = tuple[str | None, str | None, list[SecondaryCnae]]
logger = logging.getLogger("cnpj_utils.pipeline")
ENRICHMENT_FIXED_COLUMNS = {"SETOR_IBGE", "CNAE_PRINCIPAL", "CNAE_PRINCIPAL_DESC"}
TRANSIENT_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cnpj_cache (
    cnpj TEXT PRIMARY KEY,
    principal TEXT,
    principal_desc TEXT,
    secundarios TEXT
)
"""


def _is_enrichment_column(column_name: str) -> bool:
    if column_name in ENRICHMENT_FIXED_COLUMNS:
        return True
    return bool(re.fullmatch(r"CNAE_SEC_\d+(_DESC)?", column_name))


@dataclass(slots=True)
class PipelineConfig:
    api_url: str = "https://api.opencnpj.org/{}"
    concurrency: int = 10
    retries: int = 3
    sleep_between_retries: float = 1.0


@dataclass(slots=True)
class PipelineStats:
    success: int = 0
    error: int = 0
    cache_hit: int = 0
    max_concurrency_reached: int = 0
    current_concurrency: int = 0


async def init_db(db_path: Path) -> aiosqlite.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(db_path.as_posix())
    await db.execute(CREATE_TABLE_SQL)
    await db.execute(
        """
        DELETE FROM cnpj_cache
        WHERE (principal IS NULL OR principal = '')
          AND (secundarios IS NULL OR secundarios = '' OR secundarios = '[]')
        """
    )
    await db.commit()
    logger.debug("SQLite cache inicializado em %s", db_path)
    return db


async def get_cache(
    db: aiosqlite.Connection,
    cnpj: str,
    stats: PipelineStats,
) -> CnpjResult | None:
    async with db.execute(
        "SELECT principal, principal_desc, secundarios FROM cnpj_cache WHERE cnpj = ?",
        (cnpj,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        return None

    principal, principal_desc, secundarios_raw = row
    secundarios = json.loads(secundarios_raw) if secundarios_raw else []
    secundarios_typed = [(str(cnae), str(desc)) for cnae, desc in secundarios]

    # Nao reutiliza entradas antigas salvas em falha (sem principal e sem secundarios).
    if not principal and not secundarios_typed:
        return None

    stats.cache_hit += 1
    return principal, principal_desc, secundarios_typed


async def save_cache(
    db: aiosqlite.Connection,
    cnpj: str,
    principal: str | None,
    principal_desc: str | None,
    secundarios: list[SecondaryCnae],
) -> None:
    await db.execute(
        "INSERT OR REPLACE INTO cnpj_cache VALUES (?, ?, ?, ?)",
        (cnpj, principal, principal_desc, json.dumps(secundarios)),
    )
    await db.commit()


async def fetch_cnpj(
    session: aiohttp.ClientSession,
    cnpj: str,
    config: PipelineConfig,
) -> CnpjResult:
    url = config.api_url.format(cnpj)

    for attempt in range(config.retries):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 404:
                    logger.warning(
                        "CNPJ nao encontrado (HTTP 404), sem retry | cnpj=%s",
                        cnpj,
                    )
                    return None, None, []

                if response.status in TRANSIENT_HTTP_STATUS:
                    raise RuntimeError(f"HTTP transitório {response.status}")

                if 400 <= response.status < 500:
                    logger.error(
                        "Erro permanente na API, sem retry | cnpj=%s | status=%s",
                        cnpj,
                        response.status,
                    )
                    return None, None, []

                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")

                data = await response.json()
                return extract_cnaes_from_payload(data)
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
            tentativa = attempt + 1
            logger.warning(
                (
                    "Falha transitoria na chamada da API | cnpj=%s | tentativa=%s/%s "
                    "| erro=%s"
                ),
                cnpj,
                tentativa,
                config.retries,
                exc,
            )
            if attempt < config.retries - 1:
                delay = config.sleep_between_retries * (attempt + 1)
                await asyncio.sleep(delay)
        except Exception as exc:
            logger.error(
                "Erro permanente ao processar resposta da API | cnpj=%s | erro=%s",
                cnpj,
                exc,
            )
            return None, None, []

    logger.error("Erro final apos retries | cnpj=%s", cnpj)
    return None, None, []


async def processar_cnpj(
    semaphore: asyncio.Semaphore,
    lock: asyncio.Lock,
    session: aiohttp.ClientSession,
    db: aiosqlite.Connection,
    cnpj: Any,
    config: PipelineConfig,
    stats: PipelineStats,
    cnae_lookup: dict[str, str] | None = None,
) -> CnpjResult:
    cnpj_normalizado = limpar_cnpj(str(cnpj))
    if len(cnpj_normalizado) != 14:
        stats.error += 1
        logger.warning("CNPJ invalido ignorado | valor_original=%s", cnpj)
        return None, None, []

    cache = await get_cache(db, cnpj_normalizado, stats)
    if cache is not None:
        logger.debug("Cache hit | cnpj=%s", cnpj_normalizado)
        principal, principal_desc, secundarios = cache
        principal, principal_desc, secundarios = fill_missing_descriptions(
            principal=principal,
            principal_desc=principal_desc,
            secundarios=secundarios,
            cnae_lookup=cnae_lookup,
        )
        if (principal, principal_desc, secundarios) != cache:
            await save_cache(
                db,
                cnpj_normalizado,
                principal,
                principal_desc,
                secundarios,
            )
            logger.debug(
                "Cache enriquecido com descricao CNAE | cnpj=%s", cnpj_normalizado
            )
        return principal, principal_desc, secundarios

    async with semaphore:
        async with lock:
            stats.current_concurrency += 1
            stats.max_concurrency_reached = max(
                stats.max_concurrency_reached,
                stats.current_concurrency,
            )

        principal, principal_desc, secundarios = await fetch_cnpj(
            session=session,
            cnpj=cnpj_normalizado,
            config=config,
        )
        principal, principal_desc, secundarios = fill_missing_descriptions(
            principal=principal,
            principal_desc=principal_desc,
            secundarios=secundarios,
            cnae_lookup=cnae_lookup,
        )

        async with lock:
            stats.current_concurrency -= 1

    if principal or secundarios:
        stats.success += 1
    else:
        stats.error += 1
        logger.warning("Sem retorno util da API | cnpj=%s", cnpj_normalizado)

    if principal or secundarios:
        await save_cache(db, cnpj_normalizado, principal, principal_desc, secundarios)
        logger.debug("Cache salvo | cnpj=%s", cnpj_normalizado)

    return principal, principal_desc, secundarios


async def processar_excel_async(
    arquivo_entrada: str | Path,
    arquivo_saida: str | Path,
    db_path: str | Path = "data/cache/cnpj_cache.db",
    cnae_table_path: (
        str | Path | None
    ) = "data/raw/CNAE_Subclasses_2_3_Estrutura_Detalhada.xlsx",
    config: PipelineConfig | None = None,
    show_progress: bool = True,
) -> PipelineStats:
    config = config or PipelineConfig()
    entrada_path = Path(arquivo_entrada)
    saida_path = Path(arquivo_saida)
    cache_path = Path(db_path)

    if not entrada_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {entrada_path}")

    df = pd.read_excel(entrada_path)
    if "CNPJ" not in df.columns:
        raise ValueError("Coluna 'CNPJ' nao encontrada.")

    cnae_lookup: dict[str, str] | None = None
    if cnae_table_path:
        table_path = Path(cnae_table_path)
        if table_path.exists():
            cnae_lookup = build_cnae_lookup(table_path)
            logger.info(
                "Tabela CNAE carregada | path=%s | itens=%s",
                table_path,
                len(cnae_lookup),
            )
        else:
            logger.warning(
                "Tabela CNAE nao encontrada, seguindo sem descricao local | path=%s",
                table_path,
            )

    logger.info(
        "Arquivo carregado | linhas=%s | input=%s",
        len(df),
        entrada_path,
    )

    stats = PipelineStats()
    db = await init_db(cache_path)
    semaphore = asyncio.Semaphore(config.concurrency)
    lock = asyncio.Lock()

    try:
        async with aiohttp.ClientSession() as session:
            tasks = [
                processar_cnpj(
                    semaphore=semaphore,
                    lock=lock,
                    session=session,
                    db=db,
                    cnpj=cnpj,
                    config=config,
                    stats=stats,
                    cnae_lookup=cnae_lookup,
                )
                for cnpj in df["CNPJ"]
            ]

            if tasks:
                if show_progress:
                    resultados = await tqdm_asyncio.gather(*tasks)
                else:
                    resultados = await asyncio.gather(*tasks)
            else:
                resultados = []
    finally:
        await db.close()

    max_sec = max((len(r[2]) for r in resultados), default=0)

    setor_ibge = [classificar_com_fallback(r[0], r[2]) for r in resultados]

    base_columns = [col for col in df.columns if not _is_enrichment_column(str(col))]
    if len(base_columns) != len(df.columns):
        df = df[base_columns].copy()

    # Primeira coluna nova: entra logo apos as colunas originais de entrada.
    df.insert(len(base_columns), "SETOR_IBGE", setor_ibge)

    df["CNAE_PRINCIPAL"] = [r[0] for r in resultados]
    df["CNAE_PRINCIPAL_DESC"] = [r[1] for r in resultados]

    for i in range(max_sec):
        df[f"CNAE_SEC_{i + 1}"] = [
            r[2][i][0] if i < len(r[2]) else None for r in resultados
        ]
        df[f"CNAE_SEC_{i + 1}_DESC"] = [
            r[2][i][1] if i < len(r[2]) else None for r in resultados
        ]

    saida_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(saida_path, index=False)
    logger.info("Arquivo de saida salvo | output=%s", saida_path)
    return stats
