import pytest

from cnpj_utils.classification import (
    classificar_com_fallback,
    classificar_setor_ibge,
    cnae_para_secao,
)


@pytest.mark.parametrize(
    ("cnae", "secao"),
    [
        ("0111301", "A"),
        ("0511800", "B"),
        ("1011201", "C"),
        ("3511501", "D"),
        ("4120400", "F"),
        ("4711302", "G"),
        ("6201501", "J"),
        ("9602501", "S"),
        ("0000000", None),
        (None, None),
    ],
)
def test_cnae_para_secao(cnae: str | None, secao: str | None) -> None:
    assert cnae_para_secao(cnae) == secao


@pytest.mark.parametrize(
    ("cnae", "setor"),
    [
        ("1011201", "Industria"),
        ("4120400", "Construcao"),
        ("4711302", "Comercio"),
        ("6201501", "Servicos"),
        ("6462000", "Holdings"),
        ("6461-1/00", "Holdings"),
        (None, None),
    ],
)
def test_classificar_setor_ibge(cnae: str | None, setor: str | None) -> None:
    assert classificar_setor_ibge(cnae) == setor


def test_classificar_com_fallback_usa_principal() -> None:
    secundarios = [("4711302", "Comercio varejista"), ("6201501", "Software")]
    assert classificar_com_fallback("1011201", secundarios) == "Industria"


def test_classificar_com_fallback_usa_secundario() -> None:
    secundarios = [("6201501", "Software")]
    assert classificar_com_fallback(None, secundarios) == "Servicos"


def test_classificar_com_fallback_usa_secundario_quando_principal_invalido() -> None:
    secundarios = [("6201501", "Software")]
    assert classificar_com_fallback("0000000", secundarios) == "Servicos"


def test_classificar_com_fallback_usa_holding_no_secundario() -> None:
    secundarios = [("6462-0/00", "Holdings de instituicoes nao financeiras")]
    assert classificar_com_fallback(None, secundarios) == "Holdings"
