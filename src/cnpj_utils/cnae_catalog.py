from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

import pandas as pd

from .classification import SecondaryCnae

DEFAULT_CNAE_URL = (
    "https://concla.ibge.gov.br/images/concla/documentacao/"
    "CNAE_Subclasses_2_3_Estrutura_Detalhada.xlsx"
)


def normalize_cnae_code(value: Any) -> str | None:
    if value is None:
        return None

    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 7:
        return digits
    return None


def fill_missing_descriptions(
    principal: str | None,
    principal_desc: str | None,
    secundarios: Sequence[SecondaryCnae],
    cnae_lookup: dict[str, str] | None,
) -> tuple[str | None, str | None, list[SecondaryCnae]]:
    if not cnae_lookup:
        return principal, principal_desc, list(secundarios)

    principal_desc_final = principal_desc
    if principal and (principal_desc is None or not principal_desc.strip()):
        principal_desc_final = cnae_lookup.get(principal)

    secundarios_finais: list[SecondaryCnae] = []
    for cnae, desc in secundarios:
        desc_final = desc
        if not desc or not desc.strip():
            desc_final = cnae_lookup.get(cnae, "")
        secundarios_finais.append((cnae, desc_final))

    return principal, principal_desc_final, secundarios_finais


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    no_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", no_marks.lower())


def _find_code_column(columns: list[str]) -> str | None:
    best: str | None = None
    for column in columns:
        norm = _normalize_text(column)
        if "subclasse" in norm and "cnae" in norm:
            return column
        if "subclasse" in norm or "codigo" in norm and "cnae" in norm:
            best = column
    return best


def _find_desc_column(columns: list[str]) -> str | None:
    best: str | None = None
    for column in columns:
        norm = _normalize_text(column)
        if "denominacao" in norm:
            return column
        if "descricao" in norm:
            best = column
    return best


def _extract_lookup_from_raw_dataframe(df: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}

    for _, row in df.iterrows():
        values = ["" if pd.isna(v) else str(v).strip() for v in row.tolist()]
        if not any(values):
            continue

        code_idx = -1
        code: str | None = None
        for idx, value in enumerate(values):
            parsed = normalize_cnae_code(value)
            if parsed:
                code = parsed
                code_idx = idx
                break

        if not code:
            continue

        desc = ""
        for value in values[code_idx + 1 :]:
            if value:
                desc = value
        if not desc:
            continue

        # Ignora eventuais linhas de cabecalho em arquivos com estrutura irregular.
        if _normalize_text(desc) in {"denominacao", "descricao"}:
            continue

        lookup[code] = desc

    return lookup


def build_cnae_lookup(table_path: str | Path) -> dict[str, str]:
    path = Path(table_path)
    if not path.exists():
        raise FileNotFoundError(f"Tabela CNAE nao encontrada: {path}")

    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    lookup: dict[str, str] = {}

    for _sheet_name, df in sheets.items():
        if df.empty:
            continue

        columns = [str(col) for col in df.columns]
        code_col = _find_code_column(columns)
        desc_col = _find_desc_column(columns)
        if code_col is None or desc_col is None:
            continue

        for _, row in df[[code_col, desc_col]].iterrows():
            code = normalize_cnae_code(row.get(code_col))
            desc_raw = row.get(desc_col)
            if not code:
                continue
            if desc_raw is None:
                continue
            desc = str(desc_raw).strip()
            if not desc or desc.lower() == "nan":
                continue
            lookup[code] = desc

    if not lookup:
        raw_sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
        for _sheet_name, df_raw in raw_sheets.items():
            if df_raw.empty:
                continue
            lookup.update(_extract_lookup_from_raw_dataframe(df_raw))

    if not lookup:
        raise ValueError(
            "Nao foi possivel extrair codigos/descricoes da tabela CNAE informada."
        )

    return lookup


def download_cnae_table(
    output_path: str | Path,
    url: str = DEFAULT_CNAE_URL,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(url, path.as_posix())
    return path
