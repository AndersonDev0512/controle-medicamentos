import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

HAS_REPORTLAB = True
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
except Exception:
    HAS_REPORTLAB = False
from services.sheets_service import ler_historico
from utils.constants import TIPOS_MOVIMENTACAO


def gerar_pdf_aplicacoes(dataframe: pd.DataFrame, data_referencia: str) -> bytes:
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab não está instalado no ambiente atual.")
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.3 * inch,
        rightMargin=0.3 * inch,
        topMargin=0.3 * inch,
        bottomMargin=0.3 * inch,
    )
    colunas = ["Data Hora", "Medicamento", "Quantidade", "Material", "Lote Material", "Aplicador", "Paciente", "Observação"]
    dados = [colunas]
    for _, linha in dataframe.reindex(columns=colunas, fill_value="").iterrows():
        dados.append([str(linha[coluna]) for coluna in colunas])
    tabela = Table(dados, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    styles = getSampleStyleSheet()
    documento.build([Paragraph("Aplicações do dia " + data_referencia, styles["Title"]), tabela])
    return buffer.getvalue()

st.markdown('<h1 class="page-title">📜 Histórico de Movimentações</h1>', unsafe_allow_html=True)

df = ler_historico()

if df.empty:
    st.info("Nenhuma movimentação registrada ainda.")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Filtros</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    dt_ini = st.date_input("Data Inicial", value=date.today() - timedelta(days=30), format="DD/MM/YYYY")
with c2:
    dt_fim = st.date_input("Data Final", value=date.today(), format="DD/MM/YYYY")
with c3:
    meds = ["Todos"] + sorted(df["Medicamento"].dropna().unique().tolist())
    filtro_med = st.selectbox("Medicamento", options=meds)
with c4:
    filtro_tipo = st.selectbox("Tipo", options=["Todos"] + TIPOS_MOVIMENTACAO)

# ── Apply filters ──────────────────────────────────────────────────────────────
df_filt = df.copy()
df_filt["_dt"] = pd.to_datetime(
    df_filt["Data Hora"].astype(str), format="%d/%m/%Y %H:%M:%S", errors="coerce"
)
dt_ini_ts = pd.Timestamp(dt_ini)
dt_fim_ts = pd.Timestamp(dt_fim) + pd.Timedelta(days=1)
df_filt = df_filt[(df_filt["_dt"] >= dt_ini_ts) & (df_filt["_dt"] < dt_fim_ts)]

if filtro_med != "Todos":
    df_filt = df_filt[df_filt["Medicamento"] == filtro_med]
if filtro_tipo != "Todos":
    df_filt = df_filt[df_filt["Tipo"] == filtro_tipo]

df_filt = df_filt.drop(columns=["_dt"]).sort_values("Data Hora", ascending=False)

st.markdown(
    f'<p style="color:#94a3b8;font-size:0.85rem;">{len(df_filt)} registro(s) encontrado(s)</p>',
    unsafe_allow_html=True,
)

st.dataframe(df_filt, width='stretch', hide_index=True)

# ── Export ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Exportar</div>', unsafe_allow_html=True)
col1, col2, _ = st.columns([1, 1, 4])
with col1:
    csv = df_filt.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📄 CSV", data=csv, file_name="historico.csv", mime="text/csv", width='stretch')
with col2:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_filt.to_excel(w, index=False, sheet_name="Histórico")
    st.download_button(
        "📊 Excel",
        data=buf.getvalue(),
        file_name="historico.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width='stretch',
    )
with col1:
    if HAS_REPORTLAB:
        hoje = date.today().strftime("%d/%m/%Y")
        aplicacoes_hoje = df[df["Data Hora"].astype(str).str.startswith(hoje)].copy()
        pdf = gerar_pdf_aplicacoes(aplicacoes_hoje, hoje)
        st.download_button("📑 PDF do dia", data=pdf, file_name="aplicacoes_do_dia.pdf", mime="application/pdf", width="stretch")
    else:
        st.info("PDF indisponível: reportlab não está instalado neste ambiente.")
