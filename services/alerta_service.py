from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from services.estoque_service import get_estoque
from services.sheets_service import ler_materiais
from utils.constants import STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK, CORES_STATUS
from utils.helpers import safe_int, calcular_dias_para_vencer, calcular_status


@dataclass
class Alerta:
    medicamento: str
    lote: str
    quantidade: int
    data_vencimento: str
    dias_para_vencer: Optional[int]
    status: str
    cor: str
    tipo: str = "Medicamento"
    unidade: str = ""


def get_alertas() -> list[Alerta]:
    df = get_estoque()
    alertas: list[Alerta] = []

    for _, row in df.iterrows():
        status = str(row.get("Status", STATUS_OK))
        if status == STATUS_OK:
            continue
        dias = row.get("Dias para Vencer")
        alertas.append(
            Alerta(
                medicamento=str(row.get("Medicamento", "")),
                lote=str(row.get("Lote", "")),
                quantidade=safe_int(row.get("Quantidade", 0)),
                data_vencimento=str(row.get("Data de Vencimento", "")),
                dias_para_vencer=int(dias) if dias is not None else None,
                status=status,
                cor=CORES_STATUS.get(status, "#6b7280"),
                unidade=str(row.get("Unidade de Medida", "") or ""),
            )
        )

    return ordenar_alertas(alertas)


def get_alertas_materiais() -> list[Alerta]:
    df = ler_materiais()
    alertas: list[Alerta] = []
    if df.empty:
        return alertas

    for _, row in df.iterrows():
        dias = calcular_dias_para_vencer(row.get("Data de Vencimento"))
        status = calcular_status(dias)
        if status == STATUS_OK:
            continue
        alertas.append(
            Alerta(
                medicamento=str(row.get("Material", "")),
                lote=str(row.get("Lote", "")),
                quantidade=safe_int(row.get("Quantidade", 0)),
                data_vencimento=str(row.get("Data de Vencimento", "")),
                dias_para_vencer=dias,
                status=status,
                cor=CORES_STATUS.get(status, "#6b7280"),
                tipo="Material",
                unidade=str(row.get("Unidade de Medida", "") or ""),
            )
        )

    return ordenar_alertas(alertas)


_ORDEM_STATUS = {STATUS_VENCIDO: 0, STATUS_CRITICO: 1, STATUS_ATENCAO: 2, STATUS_PROXIMO: 3}


def ordenar_alertas(alertas: list[Alerta]) -> list[Alerta]:
    return sorted(
        alertas,
        key=lambda a: (
            _ORDEM_STATUS.get(a.status, 4),
            a.dias_para_vencer if a.dias_para_vencer is not None else 9999,
        ),
    )


# ── Skeleton for future notification channels ──────────────────────────────────

class NotificationService:
    """Placeholder for future notification integrations."""

    @staticmethod
    def send_email(to: str, subject: str, body: str) -> bool:
        # TODO: implement via smtplib or SendGrid
        raise NotImplementedError

    @staticmethod
    def send_whatsapp(phone: str, message: str) -> bool:
        # TODO: implement via Twilio or Z-API
        raise NotImplementedError

    @staticmethod
    def notify_expiring(days_threshold: int = 30) -> None:
        # TODO: query get_alertas() and dispatch via preferred channel
        raise NotImplementedError
