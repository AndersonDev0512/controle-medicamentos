from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from services.estoque_service import get_estoque
from utils.constants import STATUS_VENCIDO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK, CORES_STATUS
from utils.helpers import safe_int


@dataclass
class Alerta:
    medicamento: str
    lote: str
    quantidade: int
    data_vencimento: str
    dias_para_vencer: Optional[int]
    status: str
    cor: str


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
            )
        )

    _ordem = {STATUS_VENCIDO: 0, STATUS_ATENCAO: 1, STATUS_PROXIMO: 2}
    alertas.sort(
        key=lambda a: (
            _ordem.get(a.status, 3),
            a.dias_para_vencer if a.dias_para_vencer is not None else 9999,
        )
    )
    return alertas


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
