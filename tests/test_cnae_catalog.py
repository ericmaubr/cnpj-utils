import pandas as pd

from cnpj_utils.cnae_catalog import (
    _extract_lookup_from_raw_dataframe,
    fill_missing_descriptions,
    normalize_cnae_code,
)


def test_normalize_cnae_code() -> None:
    assert normalize_cnae_code("6201-5/01") == "6201501"
    assert normalize_cnae_code("6201501") == "6201501"
    assert normalize_cnae_code("62.01-5") is None
    assert normalize_cnae_code(None) is None


def test_fill_missing_descriptions_com_lookup() -> None:
    lookup = {
        "6201501": "Desenvolvimento de programas de computador sob encomenda",
        "6202300": (
            "Desenvolvimento e licenciamento de programas de computador "
            "customizaveis"
        ),
    }
    principal, principal_desc, secundarios = fill_missing_descriptions(
        principal="6201501",
        principal_desc=None,
        secundarios=[("6202300", ""), ("6203100", "")],
        cnae_lookup=lookup,
    )

    assert principal == "6201501"
    assert principal_desc == "Desenvolvimento de programas de computador sob encomenda"
    assert secundarios == [
        (
            "6202300",
            "Desenvolvimento e licenciamento de programas de computador customizaveis",
        ),
        ("6203100", ""),
    ]


def test_extract_lookup_from_raw_dataframe_layout_concla() -> None:
    df = pd.DataFrame(
        [
            [
                "Estrutura detalhada da CNAE-Subclasses 2.3",
                None,
                None,
                None,
                None,
                None,
            ],
            ["Seção", "Divisão", "Grupo", "Classe", "Subclasse", "Denominação"],
            [None, None, None, "01.11-3", None, "Cultivo de cereais"],
            [None, None, None, None, "0111-3/01", "Cultivo de arroz"],
            [None, None, None, None, "6201-5/01", "Desenvolvimento de software"],
        ]
    )

    lookup = _extract_lookup_from_raw_dataframe(df)

    assert lookup["0111301"] == "Cultivo de arroz"
    assert lookup["6201501"] == "Desenvolvimento de software"
