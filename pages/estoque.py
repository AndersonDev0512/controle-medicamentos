import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
# pyright: reportMissingModuleSource=false
from io import BytesIO
from services.estoque_service import get_estoque
from utils.config import get_config
from utils.constants import STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK
from utils.helpers import normalizar_texto, status_label

import plotly.express as px

HAS_REPORTLAB = True
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:
    HAS_REPORTLAB = False
    colors = None
    landscape = letter = None
    getSampleStyleSheet = None
    inch = None
    Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None


def gerar_pdf_estoque(dataframe: pd.DataFrame, titulo: str) -> bytes:
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab não está instalado no ambiente atual.")

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.35 * inch,
        rightMargin=0.35 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )
    estilos = getSampleStyleSheet()
    colunas = ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Dias para Vencer", "Status"]
    dados = [colunas]
    for _, linha in dataframe.reindex(columns=colunas, fill_value="").iterrows():
        dados.append([str(linha[coluna]) for coluna in colunas])

    tabela = Table(dados, repeatRows=1, colWidths=[2.25 * inch, 0.75 * inch, 1.15 * inch, 1.0 * inch, 1.15 * inch, 0.95 * inch, 1.35 * inch])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    documento.build([Paragraph(titulo, estilos["Title"]), Spacer(1, 0.15 * inch), tabela])
    return buffer.getvalue()

st.markdown('<h1 class="page-title">📦 Estoque de Medicamento</h1>', unsafe_allow_html=True)

st.page_link(
    "pages/estoque_materiais.py",
    label="🧴 Abrir Estoque de Materiais",
    icon="🧴",
)

df = get_estoque()
if df.empty:
    st.info("Nenhum medicamento cadastrado. Acesse **Cadastrar Medicamento** para começar.")
    if st.button("➕ Cadastrar agora"):
        st.switch_page("pages/cadastrar_medicamento.py")
    st.stop()

st.markdown('<div class="section-header">Filtros avançados</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    pesquisa = st.text_input("🔍 Pesquisar por medicamento ou lote", placeholder="Ex.: Acido, Ácido, 05143 ou AMP")
with c2:
    filtro_status = st.selectbox("Filtrar por status", ["Todos", STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK])
with c3:
    ordenar = st.selectbox("Ordenar por", ["Medicamento", "Dias para Vencer", "Quantidade", "Data de Vencimento", "Status"])

c4, c5, c6 = st.columns(3)
with c4:
    quantidade_minima = st.number_input("Quantidade mínima", min_value=0, value=0, step=1)
with c5:
    quantidade_maxima = st.number_input("Quantidade máxima", min_value=0, value=0, step=1, help="Use 0 para não limitar.")
with c6:
    apenas_vencendo = st.checkbox("Vencimento nos próximos 120 dias")

df_filt = df.copy()
if pesquisa:
    termo = normalizar_texto(pesquisa)
    mascara = df_filt["Medicamento"].map(normalizar_texto).str.contains(termo, regex=False)
    mascara |= df_filt["Lote"].map(normalizar_texto).str.contains(termo, regex=False)
    df_filt = df_filt[mascara]
if filtro_status != "Todos":
    df_filt = df_filt[df_filt["Status"] == filtro_status]

quantidades = pd.to_numeric(df_filt["Quantidade"], errors="coerce").fillna(0)
df_filt = df_filt[quantidades >= quantidade_minima]
if quantidade_maxima > 0:
    df_filt = df_filt[quantidades <= quantidade_maxima]
if apenas_vencendo:
    dias = pd.to_numeric(df_filt["Dias para Vencer"], errors="coerce")
    df_filt = df_filt[dias.between(0, 120)]

ascending = ordenar not in {"Dias para Vencer", "Quantidade"}
df_filt = df_filt.sort_values(ordenar, ascending=ascending, na_position="last")
display_df = df_filt.copy()
display_df["Status"] = display_df["Status"].map(lambda status: status_label(str(status)))

st.caption(f"Exibindo {len(df_filt)} de {len(df)} registro(s)")
colunas = ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Dias para Vencer", "Status"]
st.dataframe(display_df[colunas], width="stretch", hide_index=True)

grafico_coluna, resumo_coluna = st.columns([2, 1])
with grafico_coluna:
    if not df_filt.empty:
        contagem_status = df_filt.groupby("Status").size().reset_index(name="Registros")
        ordem_status = [STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK]
        contagem_status["Status"] = pd.Categorical(contagem_status["Status"], categories=ordem_status, ordered=True)
        contagem_status = contagem_status.sort_values("Status")
        figura = px.bar(
            contagem_status,
            x="Status",
            y="Registros",
            text="Registros",
            color="Status",
            color_discrete_map={
                STATUS_VENCIDO: "#525252", STATUS_CRITICO: "#a3a3a3", STATUS_ATENCAO: "#d4d4d4",
                STATUS_PROXIMO: "#737373", STATUS_OK: "#171717",
            },
            title="Distribuição do estoque por status",
        )
        figura.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=45, b=10))
        figura.update_xaxes(title=None, showgrid=False)
        figura.update_yaxes(title=None, showgrid=True, gridcolor="rgba(148,163,184,0.20)")
        st.plotly_chart(figura, use_container_width=True)
with resumo_coluna:
    st.markdown('<div class="section-header">Resumo</div>', unsafe_allow_html=True)
    st.metric("Itens filtrados", len(df_filt))
    st.metric("Unidades em estoque", int(pd.to_numeric(df_filt["Quantidade"], errors="coerce").fillna(0).sum()))

st.markdown('<div class="section-header">Exportar resultado filtrado</div>', unsafe_allow_html=True)
col_e1, col_e2, col_e3, _ = st.columns([1, 1, 1, 3])
with col_e1:
    csv = df_filt.drop(columns=["_sheet_row"], errors="ignore").to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📄 CSV", data=csv, file_name="estoque_medicamentos.csv", mime="text/csv", width="stretch")
with col_e2:
    excel = BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        df_filt.drop(columns=["_sheet_row"], errors="ignore").to_excel(writer, index=False, sheet_name="Estoque")
    st.download_button("📊 Excel", data=excel.getvalue(), file_name="estoque_medicamentos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
with col_e3:
    if HAS_REPORTLAB:
        pdf = gerar_pdf_estoque(display_df, "Estoque de Medicamento")
        st.download_button("📑 PDF", data=pdf, file_name="estoque_medicamentos.pdf", mime="application/pdf", width="stretch")
    else:
        st.info("PDF indisponível: reportlab não está instalado neste ambiente.")

config = get_config()
spreadsheet_id = config.spreadsheet_id
if "/spreadsheets/d/" in spreadsheet_id:
    spreadsheet_id = spreadsheet_id.split("/spreadsheets/d/", 1)[1].split("/", 1)[0]

if spreadsheet_id:
    st.markdown('<div class="section-header">Planilha de Estoque de Medicamentos</div>', unsafe_allow_html=True)
    components.iframe(
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?gid=0#gid=0",
        height=620,
        scrolling=True,
    )
