from __future__ import annotations

import re


def limpar_cnpj(cnpj: object) -> str:
    """Keep only digits from CNPJ values."""
    if cnpj is None:
        return ""

    cnpj_text = str(cnpj).strip()
    if cnpj_text.lower() in {"nan", "none"}:
        return ""

    if re.fullmatch(r"\d+\.0", cnpj_text):
        cnpj_text = cnpj_text[:-2]

    return re.sub(r"\D", "", cnpj_text)
