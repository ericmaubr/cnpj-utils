from __future__ import annotations

from collections.abc import Sequence

SecondaryCnae = tuple[str, str]
HOLDINGS_CNAE = {"6461100", "6462000"}


def normalizar_cnae(cnae: str | None) -> str | None:
    if not cnae:
        return None
    return "".join(ch for ch in str(cnae) if ch.isdigit()) or None


def is_holding_cnae(cnae: str | None) -> bool:
    cnae_digits = normalizar_cnae(cnae)
    return cnae_digits in HOLDINGS_CNAE


def cnae_para_secao(cnae: str | None) -> str | None:
    cnae_digits = normalizar_cnae(cnae)
    if not cnae_digits or len(cnae_digits) < 2:
        return None

    try:
        div = int(cnae_digits[:2])
    except ValueError:
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


def classificar_setor_ibge(cnae: str | None) -> str | None:
    if is_holding_cnae(cnae):
        return "Holdings"

    secao = cnae_para_secao(cnae)

    if secao in {"B", "C", "D", "E"}:
        return "Industria"
    if secao == "F":
        return "Construcao"
    if secao == "G":
        return "Comercio"
    if secao:
        return "Servicos"
    return None


def classificar_com_fallback(
    principal: str | None,
    secundarios: Sequence[SecondaryCnae],
) -> str | None:
    if principal:
        return classificar_setor_ibge(principal)

    for cnae, _descricao in secundarios:
        setor = classificar_setor_ibge(cnae)
        if setor:
            return setor

    return None
