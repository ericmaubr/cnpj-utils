from __future__ import annotations

import argparse
import asyncio
import logging

from .cnae_catalog import DEFAULT_CNAE_URL, download_cnae_table
from .logging_config import setup_logging
from .pipeline import PipelineConfig, processar_excel_async


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enriquecer planilha com CNAE principal/secundario e setor IBGE.",
    )
    parser.add_argument(
        "--input",
        default="data/raw/entrada.xlsx",
        help="Arquivo Excel de entrada com coluna CNPJ.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/saida_cnaes.xlsx",
        help="Arquivo Excel de saida.",
    )
    parser.add_argument(
        "--db-path",
        default="data/cache/cnpj_cache.db",
        help="Caminho do SQLite para cache.",
    )
    parser.add_argument(
        "--cnae-table",
        default="data/raw/CNAE_Subclasses_2_3_Estrutura_Detalhada.xlsx",
        help="Tabela CNAE do IBGE (Excel) para preencher descricoes faltantes.",
    )
    parser.add_argument(
        "--download-cnae-table",
        action="store_true",
        help="Baixa a tabela CNAE oficial do IBGE antes do processamento.",
    )
    parser.add_argument(
        "--cnae-table-url",
        default=DEFAULT_CNAE_URL,
        help="URL da tabela CNAE para download.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Numero maximo de requisicoes simultaneas.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=10,
        help="Numero de tentativas por CNPJ.",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=5.0,
        help="Base de espera (segundos) entre retries.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Desativa barra de progresso no terminal.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de log.",
    )
    parser.add_argument(
        "--log-file",
        default="logs/cnpj_utils.log",
        help="Arquivo de log.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.concurrency < 1:
        parser.error("--concurrency deve ser >= 1")
    if args.retries < 1:
        parser.error("--retries deve ser >= 1")
    if args.retry_sleep < 0:
        parser.error("--retry-sleep deve ser >= 0")

    setup_logging(level=args.log_level, log_file=args.log_file)
    logger = logging.getLogger("cnpj_utils.cli")
    logger.info(
        "Iniciando processamento | input=%s | output=%s | db=%s",
        args.input,
        args.output,
        args.db_path,
    )

    if args.download_cnae_table:
        tabela_path = download_cnae_table(args.cnae_table, args.cnae_table_url)
        logger.info("Tabela CNAE baixada | path=%s", tabela_path)

    config = PipelineConfig(
        concurrency=args.concurrency,
        retries=args.retries,
        sleep_between_retries=args.retry_sleep,
    )

    stats = asyncio.run(
        processar_excel_async(
            arquivo_entrada=args.input,
            arquivo_saida=args.output,
            db_path=args.db_path,
            cnae_table_path=args.cnae_table,
            config=config,
            show_progress=not args.no_progress,
        )
    )

    print("\n===== RESUMO =====")
    print(f"Sucesso: {stats.success}")
    print(f"Erros: {stats.error}")
    print(f"Cache hits: {stats.cache_hit}")
    print(f"Max concorrencia atingida: {stats.max_concurrency_reached}")
    print(f"Arquivo salvo em: {args.output}")
    logger.info(
        (
            "Processamento concluido | sucesso=%s | erros=%s | cache_hits=%s | "
            "max_concorrencia=%s"
        ),
        stats.success,
        stats.error,
        stats.cache_hit,
        stats.max_concurrency_reached,
    )
    return 0
