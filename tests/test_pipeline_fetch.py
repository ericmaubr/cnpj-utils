import asyncio
from pathlib import Path

import aiosqlite

from cnpj_utils.pipeline import (
    PipelineConfig,
    PipelineStats,
    fetch_cnpj,
    init_db,
    processar_cnpj,
)


class _FakeResponse:
    def __init__(self, status: int, payload: dict | None = None) -> None:
        self.status = status
        self.payload = payload or {}

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def json(self) -> dict:
        return self.payload


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = responses
        self.calls = 0

    def get(self, url: str, timeout: int = 10) -> _FakeResponse:
        del url, timeout
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def _run_processar_cnpj(
    db_path: Path,
    session: _FakeSession,
    cnpj: str = "26808974000190",
) -> tuple[tuple[str | None, str | None, list[tuple[str, str]]], PipelineStats]:
    async def _run() -> tuple[
        tuple[str | None, str | None, list[tuple[str, str]]],
        PipelineStats,
    ]:
        stats = PipelineStats()
        db = await init_db(db_path)
        try:
            result = await processar_cnpj(
                semaphore=asyncio.Semaphore(1),
                lock=asyncio.Lock(),
                session=session,
                db=db,
                cnpj=cnpj,
                config=PipelineConfig(retries=2, sleep_between_retries=0),
                stats=stats,
            )
        finally:
            await db.close()
        return result, stats

    return asyncio.run(_run())


def _count_cache_rows(db_path: Path) -> int:
    async def _run() -> int:
        async with (
            aiosqlite.connect(db_path.as_posix()) as db,
            db.execute("SELECT COUNT(*) FROM cnpj_cache") as cursor,
        ):
            row = await cursor.fetchone()
        assert row is not None
        return int(row[0])

    return asyncio.run(_run())


def test_fetch_cnpj_404_nao_faz_retry() -> None:
    session = _FakeSession([_FakeResponse(status=404)])
    config = PipelineConfig(retries=3)

    result = asyncio.run(
        fetch_cnpj(session=session, cnpj="26808974000190", config=config)
    )

    assert session.calls == 1
    assert result == (None, None, [])


def test_fetch_cnpj_400_nao_faz_retry() -> None:
    session = _FakeSession([_FakeResponse(status=400)])
    config = PipelineConfig(retries=3)

    result = asyncio.run(
        fetch_cnpj(session=session, cnpj="26808974000190", config=config)
    )

    assert session.calls == 1
    assert result == (None, None, [])


def test_fetch_cnpj_503_faz_retry_ate_sucesso() -> None:
    session = _FakeSession(
        [
            _FakeResponse(status=503),
            _FakeResponse(
                status=200,
                payload={
                    "cnae_principal": "6201501",
                    "cnaes_secundarios": ["6202300"],
                },
            ),
        ]
    )
    config = PipelineConfig(retries=3, sleep_between_retries=0)

    result = asyncio.run(
        fetch_cnpj(session=session, cnpj="26808974000190", config=config)
    )

    assert session.calls == 2
    assert result == ("6201501", None, [("6202300", "")])


def test_processar_cnpj_404_nao_persiste_cache(tmp_path: Path) -> None:
    db_path = tmp_path / "cache_404.db"
    session = _FakeSession([_FakeResponse(status=404), _FakeResponse(status=404)])

    result_1, stats_1 = _run_processar_cnpj(db_path=db_path, session=session)
    result_2, stats_2 = _run_processar_cnpj(db_path=db_path, session=session)

    assert result_1 == (None, None, [])
    assert result_2 == (None, None, [])
    assert stats_1.cache_hit == 0
    assert stats_2.cache_hit == 0
    assert session.calls == 2
    assert _count_cache_rows(db_path) == 0


def test_processar_cnpj_resposta_vazia_nao_persiste_cache(tmp_path: Path) -> None:
    db_path = tmp_path / "cache_empty.db"
    session = _FakeSession(
        [
            _FakeResponse(status=200, payload={}),
            _FakeResponse(status=200, payload={}),
        ]
    )

    result_1, stats_1 = _run_processar_cnpj(db_path=db_path, session=session)
    result_2, stats_2 = _run_processar_cnpj(db_path=db_path, session=session)

    assert result_1 == (None, None, [])
    assert result_2 == (None, None, [])
    assert stats_1.cache_hit == 0
    assert stats_2.cache_hit == 0
    assert session.calls == 2
    assert _count_cache_rows(db_path) == 0
