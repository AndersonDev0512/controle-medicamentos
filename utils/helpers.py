from __future__ import annotations
import streamlit as st
from datetime import datetime, date
from typing import Optional, Union, Any, Dict
from collections.abc import Mapping
import unicodedata
from utils.constants import (
    STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK,
    CORES_STATUS, DIAS_CRITICO, DIAS_ATENCAO, DIAS_PROXIMO,
)
import json


def sanitize_service_account(raw: Union[Dict[str, Any], str, Mapping]) -> Dict[str, Any]:
    if isinstance(raw, Mapping) and not isinstance(raw, dict):
        raw = dict(raw)

    if isinstance(raw, str):
        s = raw.strip()
        try:
            parsed = json.loads(s)
            raw = parsed
        except Exception:
            raw = {"private_key": s} if "-----BEGIN" in s and "PRIVATE KEY" in s else {}

    if not isinstance(raw, dict):
        raise ValueError(f"Formato inválido para gcp_service_account (esperado dict ou JSON). Recebido: {type(raw)}")

    pk = raw.get("private_key")
    if pk and isinstance(pk, str):
        if "\\n" in pk:
            raw["private_key"] = pk.replace("\\n", "\n")
        if raw["private_key"].startswith('"""') and raw["private_key"].endswith('"""'):
            raw["private_key"] = raw["private_key"].strip('"')

    if not raw.get("client_email") or not raw.get("private_key"):
        raise ValueError("service account inválida: faltando 'client_email' ou 'private_key'.")

    return raw


def calcular_dias_para_vencer(
    data_vencimento: Union[str, date, datetime, None],
) -> Optional[int]:
    if not data_vencimento or str(data_vencimento).strip() == "":
        return None
    try:
        if isinstance(data_vencimento, datetime):
            dt = data_vencimento.date()
        elif isinstance(data_vencimento, date):
            dt = data_vencimento
        else:
            s = str(data_vencimento).strip()
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(s, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                return None
        return (dt - date.today()).days
    except Exception:
        return None


def calcular_status(dias: Optional[int]) -> str:
    if dias is None:
        return STATUS_OK
    if dias < 0:
        return STATUS_VENCIDO
    if dias <= DIAS_CRITICO:
        return STATUS_CRITICO
    if dias <= DIAS_ATENCAO:
        return STATUS_ATENCAO
    if dias <= DIAS_PROXIMO:
        return STATUS_PROXIMO
    return STATUS_OK


def formatar_data_hora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (ValueError, TypeError):
        return default


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return default


def normalizar_texto(value: object) -> str:
    """Normaliza texto para pesquisas sem diferença entre caixa ou acentos."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def load_css() -> None:
    try:
        with open("assets/style.css", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


def metric_card(title: str, value: object, icon: str, color: str) -> str:
    return (
        f'<div class="metric-card" style="border-left-color:{color};">'
        f'<div class="metric-icon">{icon}</div>'
        f'<div class="metric-content">'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{title}</div>'
        f"</div></div>"
    )


def status_badge(status: str) -> str:
    color = CORES_STATUS.get(status, "#6b7280")
    return (
        f'<span class="status-badge" '
        f'style="background:{color}20;color:{color};border:1px solid {color};">'
        f"{status}</span>"
    )


def status_label(status: str) -> str:
    status = (status or "").strip()
    mapping = {
        "Vencido": "⚫ VENCIDO",
        "Crítico": "🔴 CRÍTICO (até 15 dias)",
        "Atenção": "🟠 ATENÇÃO (16 a 89 dias)",
        "Próximo": "🟡 PRÓXIMO (90 a 120 dias)",
        "OK": "🟢 OK (+120 dias)",
    }
    return mapping.get(status, status)


def normalize_status(raw: object) -> str:
    """Normalize a status value coming from the sheet to one of the canonical STATUS_* constants.

    Handles emojis, extra text in parentheses, and common variations.
    """
    s = (str(raw) if raw is not None else "").strip()
    if s == "":
        return STATUS_OK

    # remove parenthetical content and extra whitespace
    import re

    s_clean = re.sub(r"\(.*?\)", "", s).strip()
    s_clean_lower = s_clean.lower()

    # map by keywords or emoji
    if any(k in s_clean_lower for k in ("venc", "expir", "expired", "expired")) or "⚫" in s_clean:
        return STATUS_VENCIDO
    if any(k in s_clean_lower for k in ("crit", "crít", "critico", "crítico")) or "🔴" in s_clean:
        return STATUS_CRITICO
    if any(k in s_clean_lower for k in ("aten", "atenção", "attention")) or "🟠" in s_clean or "🔶" in s_clean:
        return STATUS_ATENCAO
    if any(k in s_clean_lower for k in ("prox", "próx", "próximo", "next")) or "🟡" in s_clean or "⚠" in s_clean:
        return STATUS_PROXIMO
    if any(k in s_clean_lower for k in ("ok", "ok+", "bom", "good")) or "🟢" in s_clean or "✅" in s_clean:
        return STATUS_OK

    # default: try exact matches against canonical names
    if s_clean_lower in (STATUS_VENCIDO.lower(), STATUS_CRITICO.lower(), STATUS_ATENCAO.lower(), STATUS_PROXIMO.lower(), STATUS_OK.lower()):
        # return capitalized canonical form
        mapping = {
            STATUS_VENCIDO.lower(): STATUS_VENCIDO,
            STATUS_CRITICO.lower(): STATUS_CRITICO,
            STATUS_ATENCAO.lower(): STATUS_ATENCAO,
            STATUS_PROXIMO.lower(): STATUS_PROXIMO,
            STATUS_OK.lower(): STATUS_OK,
        }
        return mapping[s_clean_lower]

    # fallback: return OK to avoid missing counts
    return STATUS_OK


def check_credentials_configured() -> bool:
    try:
        _ = st.secrets["gcp_service_account"]
        return True
    except Exception:
        return False
