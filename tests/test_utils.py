from cnpj_utils.utils import limpar_cnpj


def test_limpar_cnpj_remove_caracteres_nao_numericos() -> None:
    assert limpar_cnpj("12.345.678/0001-90") == "12345678000190"


def test_limpar_cnpj_com_none() -> None:
    assert limpar_cnpj(None) == ""


def test_limpar_cnpj_float_excel() -> None:
    assert limpar_cnpj("12345678000190.0") == "12345678000190"
