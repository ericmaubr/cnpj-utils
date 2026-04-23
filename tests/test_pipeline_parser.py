from cnpj_utils.api_parser import extract_cnaes_from_payload


def test_extract_cnaes_formato_atual_api() -> None:
    payload = {
        "cnpj": "04959158000144",
        "cnae_principal": "6201501",
        "cnaes_secundarios": ["6202300", "6203100"],
    }

    principal, principal_desc, secundarios = extract_cnaes_from_payload(payload)

    assert principal == "6201501"
    assert principal_desc is None
    assert secundarios == [("6202300", ""), ("6203100", "")]


def test_extract_cnaes_formato_antigo_estabelecimento() -> None:
    payload = {
        "estabelecimento": {
            "atividade_principal": {"id": "6462000", "descricao": "Holding"},
            "atividades_secundarias": [
                {"id": "6201501", "descricao": "Desenvolvimento de software"}
            ],
        }
    }

    principal, principal_desc, secundarios = extract_cnaes_from_payload(payload)

    assert principal == "6462000"
    assert principal_desc == "Holding"
    assert secundarios == [("6201501", "Desenvolvimento de software")]
