from __future__ import annotations

from typing import Any

from .classification import SecondaryCnae

CnpjResult = tuple[str | None, str | None, list[SecondaryCnae]]


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_secundarios(secundarios_data: Any) -> list[SecondaryCnae]:
    secundarios: list[SecondaryCnae] = []
    if not secundarios_data:
        return secundarios

    if isinstance(secundarios_data, list):
        for item in secundarios_data:
            if isinstance(item, dict):
                cnae = _to_optional_str(item.get("id"))
                descricao = _to_optional_str(item.get("descricao")) or ""
                if cnae:
                    secundarios.append((cnae, descricao))
            else:
                cnae = _to_optional_str(item)
                if cnae:
                    secundarios.append((cnae, ""))

    return secundarios


def extract_cnaes_from_payload(data: dict[str, Any]) -> CnpjResult:
    # Formato antigo: data.estabelecimento.atividade_principal / atividades_secundarias
    est = data.get("estabelecimento")
    if isinstance(est, dict):
        principal_data = est.get("atividade_principal") or {}
        principal = _to_optional_str(principal_data.get("id"))
        principal_desc = _to_optional_str(principal_data.get("descricao"))
        secundarios = _parse_secundarios(est.get("atividades_secundarias"))

        if principal or secundarios:
            return principal, principal_desc, secundarios

    # Formato atual da api.opencnpj.org: cnae_principal / cnaes_secundarios
    principal = _to_optional_str(data.get("cnae_principal"))
    principal_desc = _to_optional_str(data.get("cnae_principal_descricao"))
    secundarios = _parse_secundarios(data.get("cnaes_secundarios"))
    return principal, principal_desc, secundarios
