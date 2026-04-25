from __future__ import annotations

import unicodedata
from collections.abc import Sequence

SecondaryCnae = tuple[str, str]
HOLDINGS_CNAE = {"6461100", "6462000"}
SERVICOS_SECOES = {"I", "J", "K", "M", "N", "O", "P", "Q", "R", "S"}
SEM_FINS_LUCRATIVOS_DIVISOES = {94}
SERVICOS_MEDICOS_GRUPOS = {861, 862}
PROFISSIONAIS_SAUDE_GRUPOS = {863}
SEM_FINS_LUCRATIVOS_KEYWORDS = (
    "associacao",
    "fundacao",
    "organizacaoreligiosa",
    "partidopolitico",
    "sindicato",
)
IMPORTACAO_KEYWORDS = (
    "importacao",
    "importad",
    "equiparadoindustria",
    "equiparacaoindustria",
)

COMERCIO = "Comércio"
INDUSTRIA = "Indústria"
SERVICOS_DEMAIS = "Prestador de Serviço - Demais Serviços"
PROFISSIONAIS_SAUDE = "Prestador de Serviço - Profissionais da Saúde"
SERVICOS_MEDICOS = "Prestador de Serviço - Serviços Médicos"
IMOBILIARIAS = "Prestador de Serviço - Administração de Bens/Imobiliárias"
SEM_FINS_LUCRATIVOS = "Sem Fins Lucrativos"
IMPORTACAO_INDUSTRIA = "Importação de Produtos ou Equiparação a Indústria"
PRODUTOR_RURAL = "Produtor Rural"
HOLDING = "Holding"
TRANSPORTES = "Transportes / Transportadora"


def normalizar_cnae(cnae: str | None) -> str | None:
    if not cnae:
        return None
    return "".join(ch for ch in str(cnae) if ch.isdigit()) or None


def is_holding_cnae(cnae: str | None) -> bool:
    cnae_digits = normalizar_cnae(cnae)
    return cnae_digits in HOLDINGS_CNAE


def normalizar_texto(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    no_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return "".join(ch for ch in no_marks.lower() if ch.isalnum())


def cnae_para_divisao(cnae: str | None) -> int | None:
    cnae_digits = normalizar_cnae(cnae)
    if not cnae_digits or len(cnae_digits) < 2:
        return None

    try:
        return int(cnae_digits[:2])
    except ValueError:
        return None


def cnae_para_grupo(cnae: str | None) -> int | None:
    cnae_digits = normalizar_cnae(cnae)
    if not cnae_digits or len(cnae_digits) < 3:
        return None

    try:
        return int(cnae_digits[:3])
    except ValueError:
        return None


def cnae_para_secao(cnae: str | None) -> str | None:
    div = cnae_para_divisao(cnae)
    if div is None:
        return None

    if 1 <= div <= 3:
        return "A"
    if 5 <= div <= 9:
        return "B"
    if 10 <= div <= 33:
        return "C"
    if div == 35:
        return "D"
    if 36 <= div <= 39:
        return "E"
    if 41 <= div <= 43:
        return "F"
    if 45 <= div <= 47:
        return "G"
    if 49 <= div <= 53:
        return "H"
    if 55 <= div <= 56:
        return "I"
    if 58 <= div <= 63:
        return "J"
    if 64 <= div <= 66:
        return "K"
    if div == 68:
        return "L"
    if 69 <= div <= 75:
        return "M"
    if 77 <= div <= 82:
        return "N"
    if div == 84:
        return "O"
    if 85 <= div <= 88:
        return "P"
    if 90 <= div <= 93:
        return "R"
    if 94 <= div <= 96:
        return "S"
    return None


def _contains_any_keyword(text: str, keywords: Sequence[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def classificar_setor_ibge(
    cnae: str | None,
    descricao: str | None = None,
) -> str | None:
    descricao_normalizada = normalizar_texto(descricao)

    if is_holding_cnae(cnae):
        return HOLDING

    divisao = cnae_para_divisao(cnae)
    grupo = cnae_para_grupo(cnae)
    secao = cnae_para_secao(cnae)

    if divisao in SEM_FINS_LUCRATIVOS_DIVISOES or _contains_any_keyword(
        descricao_normalizada,
        SEM_FINS_LUCRATIVOS_KEYWORDS,
    ):
        return SEM_FINS_LUCRATIVOS

    if secao == "A":
        return PRODUTOR_RURAL
    if secao == "H":
        return TRANSPORTES
    if secao == "L":
        return IMOBILIARIAS
    if grupo in SERVICOS_MEDICOS_GRUPOS:
        return SERVICOS_MEDICOS
    if grupo in PROFISSIONAIS_SAUDE_GRUPOS:
        return PROFISSIONAIS_SAUDE
    if _contains_any_keyword(descricao_normalizada, IMPORTACAO_KEYWORDS):
        return IMPORTACAO_INDUSTRIA
    if secao == "G":
        return COMERCIO
    if secao in {"B", "C", "D", "E", "F"}:
        return INDUSTRIA
    if secao in SERVICOS_SECOES:
        return SERVICOS_DEMAIS
    return None


def classificar_com_fallback(
    principal: str | None,
    principal_desc: str | None,
    secundarios: Sequence[SecondaryCnae],
) -> str | None:
    if principal:
        setor_principal = classificar_setor_ibge(principal, principal_desc)
        if setor_principal:
            return setor_principal

    for cnae, descricao in secundarios:
        setor = classificar_setor_ibge(cnae, descricao)
        if setor:
            return setor

    return None
