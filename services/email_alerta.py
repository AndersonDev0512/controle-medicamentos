from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from io import BytesIO
from typing import Iterable

import pandas as pd

from services.estoque_service import get_estoque, get_materiais
from utils.helpers import safe_float

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

DESTINATARIOS_PADRAO = [
    "stephannyuniderp@gmail.com",
    "anderson.erdeval@gmail.com",
]


def data_hora_brasilia() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _config_email() -> dict[str, str]:
    try:
        import streamlit as st
        secrets = st.secrets
    except Exception:
        secrets = {}

    def value(name: str, default: str = "") -> str:
        return str(os.getenv(name) or (secrets.get(name, default) if hasattr(secrets, "get") else default)).strip()

    return {
        "host": value("SMTP_HOST"),
        "port": value("SMTP_PORT", "587"),
        "user": value("SMTP_USER"),
        "password": value("SMTP_PASSWORD"),
        "sender": value("ALERTA_EMAIL_REMETENTE") or value("SMTP_USER"),
    }


def texto_alerta(data_hora: str | None = None) -> str:
    emitido = data_hora or data_hora_brasilia()
    return (
        "Prezada Stephanny,\n\n"
        "Informamos que o monitoramento diário do estoque identificou materiais com prazo de validade próximo ao vencimento.\n\n"
        "Solicitamos a verificação dos itens destacados no relatório para adoção das medidas necessárias, visando minimizar perdas e garantir a adequada gestão dos insumos.\n\n"
        "Classificações utilizadas:\n\n"
        "- ⚫ Vencido\n"
        "- 🔴 Crítico (até 15 dias)\n"
        "- 🟠 Atenção (16 a 89 dias)\n"
        "- 🟡 Próximo (90 a 120 dias)\n"
        "- 🟢 OK (+120 dias)\n\n"
        f"Relatório gerado automaticamente em {emitido}."
    )


def _ordenar(dataframe: pd.DataFrame, nome_coluna: str) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe.copy()
    ordenado = dataframe.copy()
    ordenado["_dias_ordem"] = pd.to_numeric(ordenado.get("Dias para Vencer"), errors="coerce")
    ordenado["_nome_ordem"] = ordenado.get(nome_coluna, "").astype(str).str.casefold()
    return ordenado.sort_values(["_dias_ordem", "_nome_ordem"], ascending=[True, True], na_position="last").drop(columns=["_dias_ordem", "_nome_ordem"])


def gerar_pdf_estoque_alerta(medicamentos: pd.DataFrame | None = None, materiais: pd.DataFrame | None = None) -> bytes:
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab não está instalado no ambiente atual.")
    medicamentos = _ordenar(medicamentos if medicamentos is not None else get_estoque(), "Medicamento")
    materiais = _ordenar(materiais if materiais is not None else get_materiais(), "Material")
    buffer = BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=.35 * inch, rightMargin=.35 * inch, topMargin=.35 * inch, bottomMargin=.35 * inch)
    estilos = getSampleStyleSheet()
    titulo = estilos["Title"]
    titulo.fontSize = 16
    titulo.textColor = colors.HexColor("#12304A")
    celula = estilos["BodyText"]
    celula.fontSize = 7
    celula.leading = 8
    elementos = [
        Paragraph("RELATÓRIO DE ESTOQUE E VALIDADE", titulo),
        Paragraph(f"Relatório emitido dia {data_hora_brasilia()} | Ordenação: vencimento mais próximo e nome (A-Z)", estilos["Normal"]),
        Spacer(1, .14 * inch),
    ]

    def tabela(dataframe: pd.DataFrame, colunas: list[str], titulo_tabela: str) -> None:
        elementos.append(Paragraph(titulo_tabela, estilos["Heading2"]))
        valores = [[Paragraph(coluna, celula) for coluna in colunas]]
        for _, linha in dataframe.reindex(columns=colunas, fill_value="").iterrows():
            valores.append([Paragraph(str(linha.get(coluna, "")), celula) for coluna in colunas])
        tabela_pdf = Table(valores, repeatRows=1)
        tabela_pdf.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B87")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#B8CBD5")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF7F9")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elementos.append(tabela_pdf)
        elementos.append(Spacer(1, .16 * inch))

    tabela(medicamentos, ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Dias para Vencer", "Status"], "Medicamentos")
    tabela(materiais, ["Material", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Dias para Vencer", "Status"], "Materiais")
    documento.build(elementos)
    return buffer.getvalue()


def enviar_alerta_estoque(destinatarios: Iterable[str] = DESTINATARIOS_PADRAO) -> None:
    config = _config_email()
    ausentes = [campo for campo in ("host", "user", "password", "sender") if not config[campo]]
    if ausentes:
        raise RuntimeError("Configuração SMTP incompleta: " + ", ".join(ausentes))
    pdf = gerar_pdf_estoque_alerta()
    emitido = data_hora_brasilia()
    mensagem = EmailMessage()
    mensagem["Subject"] = "Alerta de validade - Controle de Enfermagem"
    mensagem["From"] = config["sender"]
    mensagem["To"] = ", ".join(destinatarios)
    mensagem.set_content(texto_alerta(emitido))
    mensagem.add_attachment(pdf, maintype="application", subtype="pdf", filename=f"relatorio_estoque_{datetime.now():%Y%m%d}.pdf")
    with smtplib.SMTP(config["host"], int(config["port"])) as servidor:
        servidor.starttls()
        servidor.login(config["user"], config["password"])
        servidor.send_message(mensagem)


if __name__ == "__main__":
    enviar_alerta_estoque()
