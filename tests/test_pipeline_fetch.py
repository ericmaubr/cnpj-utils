import asyncio

from cnpj_utils.pipeline import PipelineConfig, fetch_cnpj


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def json(self) -> dict:
        return {}


class _FakeSession:
    def __init__(self, status: int) -> None:
        self.status = status
        self.calls = 0

    def get(self, url: str, timeout: int = 10) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(status=self.status)


def test_fetch_cnpj_404_nao_faz_retry() -> None:
    session = _FakeSession(status=404)
    config = PipelineConfig(retries=3)

    result = asyncio.run(
        fetch_cnpj(session=session, cnpj="26808974000190", config=config)
    )

    assert session.calls == 1
    assert result == (None, None, [])
