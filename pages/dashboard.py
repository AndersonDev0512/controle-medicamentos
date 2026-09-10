from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.estoque_service import get_estoque, get_materiais
from services.sheets_service import ler_registro_diario
from utils.constants import (
    STATUS_ATENCAO,
    STATUS_CRITICO,
    STATUS_OK,
    STATUS_PROXIMO,
    STATUS_VENCIDO,
)
from utils.helpers import render_responsive_table, safe_float

HAS_REPORTLAB = True
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:
    HAS_REPORTLAB = False

try:
    from streamlit_echarts import st_echarts
except ImportError:
    st_echarts = None

BG = "#0A0F1C"
PANEL = "#111827"
GRID = "#263247"
TEXT = "#E5F2FF"
MUTED = "#8EA4BE"
CYAN = "#00CFFF"
PURPLE = "#8B5CF6"
STATUS_COLORS = {
    STATUS_VENCIDO: "#64748B",
    STATUS_CRITICO: "#EF4444",
    STATUS_ATENCAO: "#F97316",
    STATUS_PROXIMO: "#FACC15",
    STATUS_OK: "#22C55E",
}
STATUS_ORDER = [STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK]


def _date_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame:
        return pd.Series(dtype="datetime64[ns]")
    return pd.to_datetime(frame[column], dayfirst=True, errors="coerce")


def _filtered_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    meds = get_estoque().copy()
    materials = get_materiais().copy()
    records = ler_registro_diario().copy()
    dates = pd.concat(
        [
            _date_column(meds, "Data de Inserção"),
            _date_column(materials, "Data de Inserção"),
            _date_column(records, "Data Hora"),
        ],
        ignore_index=True,
    ).dropna()
    min_date = dates.min().date() if not dates.empty else date.today()
    max_date = dates.max().date() if not dates.empty else date.today()

    with st.sidebar:
        st.markdown('<div class="dashboard-sidebar-marker"></div>', unsafe_allow_html=True)
        st.markdown("## Filtros fixos do dashboard")
        period = st.date_input(
            "Período de análise",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            format="DD/MM/YYYY",
        )
        years = ["Todos"] + sorted({str(item.year) for item in dates}, reverse=True)
        year = st.selectbox("Ano de referência", years)
        month_names = [
            "Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]
        month = st.radio("Mês de referência", month_names, horizontal=True)
        category = st.selectbox("Área monitorada", ["Todas", "Medicamentos", "Materiais"])
        status = st.selectbox("Situação do estoque", ["Todos"] + STATUS_ORDER)

    start, end = period if isinstance(period, tuple) and len(period) == 2 else (period, period)

    st.session_state.dashboard_filter_summary = {
        "periodo": f"{start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}",
        "ano": year,
        "mes": month,
        "area": category,
        "situacao": status,
    }

    def mask(frame: pd.DataFrame, column: str) -> pd.Series:
        values = _date_column(frame, column)
        result = (
            values.dt.normalize().between(pd.Timestamp(start), pd.Timestamp(end))
            if not values.empty
            else pd.Series(False, index=frame.index)
        )
        if year != "Todos":
            result &= values.dt.year.eq(int(year)).fillna(False)
        if month != "Todos":
            result &= values.dt.month.eq(month_names.index(month)).fillna(False)
        return result

    if not meds.empty:
        meds = meds.loc[mask(meds, "Data de Inserção")]
        if status != "Todos":
            meds = meds[meds["Status"].eq(status)]
    if not materials.empty:
        materials = materials.loc[mask(materials, "Data de Inserção")]
        if status != "Todos":
            materials = materials[materials["Status"].eq(status)]
    if not records.empty:
        records = records.loc[mask(records, "Data Hora")]
    if category == "Medicamentos":
        materials = materials.iloc[0:0]
    elif category == "Materiais":
        meds = meds.iloc[0:0]
    return meds, materials, records


def _base_option() -> dict:
    return {
        "animation": True,
        "animationDuration": 700,
        "textStyle": {"color": TEXT},
        "backgroundColor": "transparent",
        "tooltip": {"trigger": "axis"},
    }


def _chart(title: str, option: dict, height: int = 320) -> None:
    st.markdown(f'<div class="premium-chart-title">{title}</div>', unsafe_allow_html=True)
    if st_echarts:
        st_echarts(options=option, height=f"{height}px", key=f"echart-{title}")
        return
    figure = go.Figure()
    series = option.get("series", [{}])[0]
    if series.get("type") == "pie":
        figure.add_trace(go.Pie(labels=[item["name"] for item in series.get("data", [])], values=[item["value"] for item in series.get("data", [])], hole=0.58))
    elif series.get("type") == "bar":
        figure.add_trace(go.Bar(x=option.get("xAxis", {}).get("data", []), y=series.get("data", []), marker_color=CYAN))
    elif series.get("type") == "gauge":
        value = series.get("data", [{"value": 0}])[0]["value"]
        figure.add_trace(go.Indicator(mode="gauge+number", value=value, gauge={"axis": {"range": [0, series.get("max", 1)]}, "bar": {"color": "#EF4444"}}))
    else:
        figure.add_trace(go.Scatter(x=option.get("xAxis", {}).get("data", []), y=series.get("data", []), mode="lines+markers", line=dict(color=CYAN, width=3)))
    figure.update_layout(height=height, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor=PANEL, plot_bgcolor=PANEL, font_color=TEXT, showlegend=False, xaxis=dict(gridcolor=GRID), yaxis=dict(gridcolor=GRID))
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _kpi(label: str, value: object, accent: str) -> None:
    st.markdown(f'<div class="premium-kpi" style="--kpi-accent:{accent}"><span>{label}</span><strong>{value}</strong></div>', unsafe_allow_html=True)


def _pdf_table(dataframe: pd.DataFrame, columns: list[str]) -> Table:
    styles = getSampleStyleSheet()
    cell = styles["BodyText"]
    cell.fontName = "Helvetica"
    cell.fontSize = 7
    cell.leading = 8
    header = [[Paragraph(column, cell) for column in columns]]
    body = dataframe.reindex(columns=columns, fill_value="").fillna("").astype(str).values.tolist()
    table = Table(header + [[Paragraph(value, cell) for value in row] for row in body], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B87")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8CBD5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF7F9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def gerar_pdf_dashboard(meds: pd.DataFrame, materials: pd.DataFrame, records: pd.DataFrame) -> bytes:
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab não está instalado no ambiente atual.")
    summary = st.session_state.get("dashboard_filter_summary", {})
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.35 * inch,
        rightMargin=0.35 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )
    styles = getSampleStyleSheet()
    title = styles["Title"]
    title.fontSize = 17
    title.textColor = colors.HexColor("#12304A")
    subtitle = styles["Normal"]
    subtitle.fontSize = 8
    subtitle.textColor = colors.HexColor("#547086")
    status_values = meds["Status"].value_counts() if not meds.empty and "Status" in meds else pd.Series(dtype=int)
    kpis = [
        ["Medicamentos", str(len(meds)), "Materiais", str(len(materials)), "Aplicações", str(len(records)), "Vencidos", str(status_values.get(STATUS_VENCIDO, 0))],
    ]
    elementos = [
        Paragraph("DASHBOARD DE CONTROLE DE ENFERMAGEM", title),
        Paragraph(
            f"Período: {summary.get('periodo', 'Todos')} | Ano: {summary.get('ano', 'Todos')} | Mês: {summary.get('mes', 'Todos')} | Área: {summary.get('area', 'Todas')} | Situação: {summary.get('situacao', 'Todos')}",
            subtitle,
        ),
        Spacer(1, 0.14 * inch),
    ]
    kpi_table = Table(kpis, colWidths=[1.25 * inch, 0.55 * inch] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF5F8")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#12304A")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#9FC3CF")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C5DCE3")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(kpi_table)
    elementos.append(Spacer(1, 0.16 * inch))
    elementos.append(Paragraph("Medicamentos em atenção", styles["Heading2"]))
    critical = meds[meds["Status"].isin(STATUS_ORDER[:3])].copy() if not meds.empty and "Status" in meds else meds
    if not critical.empty:
        critical["Quantidade"] = critical["Quantidade"].map(safe_float)
        elementos.append(_pdf_table(critical.sort_values("Quantidade", ascending=False).head(15), ["Medicamento", "Lote", "Quantidade", "Data de Vencimento", "Status"]))
    else:
        elementos.append(Paragraph("Nenhum item crítico no filtro selecionado.", styles["Normal"]))
    elementos.append(Spacer(1, 0.16 * inch))
    elementos.append(Paragraph("Materiais em estoque", styles["Heading2"]))
    if not materials.empty:
        elementos.append(_pdf_table(materials.head(15), ["Material", "Lote", "Quantidade", "Data de Vencimento", "Status"]))
    else:
        elementos.append(Paragraph("Nenhum material no filtro selecionado.", styles["Normal"]))
    elementos.append(Spacer(1, 0.16 * inch))
    elementos.append(Paragraph("Aplicações registradas", styles["Heading2"]))
    if not records.empty:
        elementos.append(_pdf_table(records.head(20), ["Data Hora", "Paciente", "Medicamento", "Material", "Aplicador"]))
    else:
        elementos.append(Paragraph("Nenhuma aplicação no filtro selecionado.", styles["Normal"]))
    documento.build(elementos)
    return buffer.getvalue()


st.markdown('<div class="premium-dashboard"><div class="premium-eyebrow">PAINEL OPERACIONAL</div><h1 class="premium-title">Dashboard de Controle de Enfermagem</h1><p class="premium-subtitle">Acompanhamento de estoque, validade e aplicações.</p></div>', unsafe_allow_html=True)
meds, materials, records = _filtered_data()

if HAS_REPORTLAB:
    st.download_button(
        "🖨️ Baixar dashboard para impressão (PDF paisagem)",
        data=gerar_pdf_dashboard(meds, materials, records),
        file_name="dashboard_controle_enfermagem.pdf",
        mime="application/pdf",
        width="stretch",
    )
else:
    st.info("PDF indisponível: reportlab não está instalado.")

tabs = st.tabs(["Dashboard Geral", "Medicamentos", "Materiais", "Histórico de Aplicações"])

with tabs[0]:
    status_values = meds["Status"].value_counts() if not meds.empty else pd.Series(dtype=int)
    risk = sum(int(status_values.get(item, 0)) for item in STATUS_ORDER[:4])
    cols = st.columns(7)
    labels = ["Medicamentos", "Materiais", "Vencidos", "Críticos", "Atenção", "Próximos", "OK"]
    values = [len(meds), len(materials)] + [int(status_values.get(item, 0)) for item in STATUS_ORDER]
    accents = [CYAN, PURPLE, "#64748B", "#EF4444", "#F97316", "#FACC15", "#22C55E"]
    for column, label, value, accent in zip(cols, labels, values, accents):
        with column:
            _kpi(label, value, accent)

    left, right = st.columns(2)
    with left:
        gauge = _base_option()
        gauge["series"] = [{"type": "gauge", "max": max(len(meds), 1), "data": [{"value": risk, "name": "RISCO"}]}]
        _chart("Risco de vencimento", gauge, 300)
    with right:
        donut = _base_option()
        donut["legend"] = {"bottom": 0, "textStyle": {"color": MUTED}}
        donut["series"] = [{"type": "pie", "radius": ["48%", "74%"], "data": [{"name": item, "value": int(status_values.get(item, 0)), "itemStyle": {"color": STATUS_COLORS[item]}} for item in STATUS_ORDER if status_values.get(item, 0)]}]
        _chart("Distribuição de vencimentos", donut, 300)

    record_dates = _date_column(records, "Data Hora")
    timeline = records.assign(_date=record_dates).dropna(subset=["_date"]).groupby(record_dates.dt.strftime("%d/%m")).size() if not records.empty else pd.Series(dtype=int)
    line = _base_option()
    line["xAxis"] = {"type": "category", "data": timeline.index.tolist()}
    line["yAxis"] = {"type": "value"}
    line["series"] = [{"type": "line", "smooth": True, "data": timeline.tolist(), "itemStyle": {"color": CYAN}}]
    _chart("Evolução das aplicações por período", line, 300)

    critical = meds[meds["Status"].isin(STATUS_ORDER[:3])].copy() if not meds.empty else meds
    if not critical.empty:
        critical["Quantidade"] = critical["Quantidade"].map(safe_float)
        render_responsive_table(critical.sort_values("Quantidade", ascending=False).head(8)[["Medicamento", "Lote", "Quantidade", "Data de Vencimento", "Status"]])

with tabs[1]:
    _kpi("Itens monitorados", len(meds), CYAN)
    top = meds.assign(Quantidade=meds["Quantidade"].map(safe_float)).groupby("Medicamento")["Quantidade"].sum().sort_values(ascending=False).head(10) if not meds.empty else pd.Series(dtype=float)
    option = _base_option()
    option["xAxis"] = {"type": "category", "data": top.index.tolist()}
    option["yAxis"] = {"type": "value"}
    option["series"] = [{"type": "bar", "data": top.round(2).tolist(), "itemStyle": {"color": CYAN}}]
    _chart("Top medicamentos por quantidade", option, 360)
    render_responsive_table(meds[["Medicamento", "Lote", "Quantidade", "Data de Vencimento", "Status"]].head(15) if not meds.empty else meds)

with tabs[2]:
    _kpi("Itens monitorados", len(materials), PURPLE)
    top = materials.assign(Quantidade=materials["Quantidade"].map(safe_float)).groupby("Material")["Quantidade"].sum().sort_values(ascending=False).head(10) if not materials.empty else pd.Series(dtype=float)
    option = _base_option()
    option["xAxis"] = {"type": "category", "data": top.index.tolist()}
    option["yAxis"] = {"type": "value"}
    option["series"] = [{"type": "bar", "data": top.round(2).tolist(), "itemStyle": {"color": PURPLE}}]
    _chart("Ranking de materiais", option, 360)
    render_responsive_table(materials[["Material", "Lote", "Quantidade", "Data de Vencimento", "Status"]].head(15) if not materials.empty else materials)

with tabs[3]:
    _kpi("Aplicações filtradas", len(records), CYAN)
    if records.empty:
        st.info("Nenhuma aplicação encontrada para os filtros selecionados.")
    else:
        ranking = records.groupby("Paciente").size().sort_values(ascending=False).head(10)
        option = _base_option()
        option["xAxis"] = {"type": "category", "data": ranking.index.tolist()}
        option["yAxis"] = {"type": "value"}
        option["series"] = [{"type": "bar", "data": ranking.tolist(), "itemStyle": {"color": PURPLE}}]
        _chart("Aplicações por paciente", option, 320)
        render_responsive_table(records[["Data Hora", "Paciente", "Medicamento", "Material", "Aplicador"]].head(20))
