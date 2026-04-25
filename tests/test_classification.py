import pytest

from cnpj_utils.classification import (
    COMERCIO,
    HOLDING,
    IMOBILIARIAS,
    IMPORTACAO_INDUSTRIA,
    INDUSTRIA,
    PRODUTOR_RURAL,
    PROFISSIONAIS_SAUDE,
    SEM_FINS_LUCRATIVOS,
    SERVICOS_DEMAIS,
    SERVICOS_MEDICOS,
    TRANSPORTES,
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
    ("cnae", "descricao", "setor"),
    [
        ("0111301", None, PRODUTOR_RURAL),
        ("1011201", None, INDUSTRIA),
        ("4110700", None, SERVICOS_DEMAIS),
        ("4329103", None, SERVICOS_DEMAIS),
        ("4711302", None, COMERCIO),
        ("4930202", None, TRANSPORTES),
        ("6821801", None, IMOBILIARIAS),
        ("6201501", None, SERVICOS_DEMAIS),
        ("8610101", None, SERVICOS_MEDICOS),
        ("8630503", None, PROFISSIONAIS_SAUDE),
        ("9493600", None, SEM_FINS_LUCRATIVOS),
        ("6201501", "Importacao de software sob encomenda", IMPORTACAO_INDUSTRIA),
        ("6462000", None, HOLDING),
        ("6461-1/00", None, HOLDING),
        (None, None, None),
    ],
)
def test_classificar_setor_ibge(
    cnae: str | None,
    descricao: str | None,
    setor: str | None,
) -> None:
    assert classificar_setor_ibge(cnae, descricao) == setor


def test_classificar_com_fallback_usa_principal() -> None:
    secundarios = [("4711302", "Comercio varejista"), ("6201501", "Software")]
    assert classificar_com_fallback("1011201", None, secundarios) == INDUSTRIA


def test_classificar_com_fallback_trata_construcao_como_servicos() -> None:
    secundarios = [("4711302", "Comercio varejista")]
    assert classificar_com_fallback("4329103", None, secundarios) == SERVICOS_DEMAIS


def test_classificar_com_fallback_usa_secundario() -> None:
    secundarios = [("6201501", "Software")]
    assert classificar_com_fallback(None, None, secundarios) == SERVICOS_DEMAIS


def test_classificar_com_fallback_usa_secundario_quando_principal_invalido() -> None:
    secundarios = [("6201501", "Software")]
    assert classificar_com_fallback("0000000", None, secundarios) == SERVICOS_DEMAIS


def test_classificar_com_fallback_usa_holding_no_secundario() -> None:
    secundarios = [("6462-0/00", "Holdings de instituicoes nao financeiras")]
    assert classificar_com_fallback(None, None, secundarios) == HOLDING


def test_classificar_com_fallback_considera_descricao_principal() -> None:
    secundarios = [("4711302", "Comercio varejista")]
    assert (
        classificar_com_fallback(
            "6201501",
            "Importacao de software sob encomenda",
            secundarios,
        )
        == IMPORTACAO_INDUSTRIA
    )
