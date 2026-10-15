# pyright: reportMissingModuleSource=false
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from utils.helpers import render_responsive_table

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

from services.estoque_service import get_materiais
from utils.constants import STATUS_ATENCAO, STATUS_CRITICO, STATUS_OK, STATUS_PROXIMO, STATUS_VENCIDO
from utils.helpers import normalizar_texto, status_label
from utils.constants import CARRINHO_SIM
from utils.components import stock_summary


def gerar_pdf_materiais(dataframe: pd.DataFrame) -> bytes:
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab não está instalado no ambiente atual.")

    dataframe = dataframe.copy()
    dataframe["_dias_ordem"] = pd.to_numeric(dataframe.get("Dias para Vencer"), errors="coerce")
    dataframe["_nome_ordem"] = dataframe.get("Material", "").astype(str).str.casefold()
    dataframe = dataframe.sort_values(["_dias_ordem", "_nome_ordem"], ascending=[True, True], na_position="last").drop(columns=["_dias_ordem", "_nome_ordem"])
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.35 * inch,
        rightMargin=0.35 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )
    colunas = ["Material", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Dias para Vencer", "Status"]
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
    estilos = getSampleStyleSheet()
    documento.build([Paragraph("Estoque de Materiais", estilos["Title"]), Paragraph(f"Relatório emitido dia {datetime.now():%d/%m/%Y %H:%M:%S}", estilos["Normal"]), Spacer(1, 0.15 * inch), tabela])
    return buffer.getvalue()


st.markdown('<h1 class="page-title">🧴 Estoque de Materiais</h1>', unsafe_allow_html=True)

df = get_materiais()
if df.empty:
    st.info("Nenhum material cadastrado. Acesse **Cadastrar Material** para começar.")
    if st.button("➕ Cadastrar agora"):
        st.switch_page("pages/cadastrar_material.py")
    st.stop()

st.markdown('<div class="section-header">Filtros avançados</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    # ?busca=<lote> (vindo da Central de alertas) preenche a pesquisa uma vez
    if st.query_params.get("busca"):
        st.session_state["pesquisa_material_pagina"] = st.query_params["busca"]
        del st.query_params["busca"]
    pesquisa = st.text_input("🔍 Pesquisar por material ou lote", placeholder="Ex.: Seringa, seringa, 05143 ou CX", key="pesquisa_material_pagina")
with c2:
    filtro_status = st.selectbox("Filtrar por status", ["Todos", STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK])
with c3:
    ordenar = st.selectbox("Ordenar por", ["Material", "Dias para Vencer", "Quantidade", "Data de Vencimento", "Status"])

c4, c5, c6, c7 = st.columns(4)
with c4:
    quantidade_minima = st.number_input("Quantidade mínima", min_value=0, value=0, step=1)
with c5:
    quantidade_maxima = st.number_input("Quantidade máxima", min_value=0, value=0, step=1, help="Use 0 para não limitar.")
with c6:
    apenas_vencendo = st.checkbox("Vencimento nos próximos 120 dias")
with c7:
    apenas_carrinho = st.checkbox("Somente Carrinho de Parada", key="apenas_carrinho_material_pagina")

df_filt = df.copy()
if pesquisa:
    termo = normalizar_texto(pesquisa)
    mascara = df_filt["Material"].map(normalizar_texto).str.contains(termo, regex=False)
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
if apenas_carrinho:
    df_filt = df_filt[df_filt["Carrinho de Parada"] == CARRINHO_SIM]

ascending = ordenar not in {"Dias para Vencer", "Quantidade"}
df_filt = df_filt.sort_values(ordenar, ascending=ascending, na_position="last")
display_df = df_filt.copy()
display_df["Status"] = display_df["Status"].map(lambda status: status_label(str(status)))
display_df["Carrinho de Parada"] = display_df["Carrinho de Parada"].map({"S": "Sim", "N": "Não"})

st.caption(f"Exibindo {len(df_filt)} de {len(df)} registro(s)")
colunas = ["Material", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Dias para Vencer", "Status", "Carrinho de Parada"]
render_responsive_table(display_df[colunas])

st.html(stock_summary(df_filt, len(df), "materiais"))

st.markdown('<div class="section-header">Exportar resultado</div>', unsafe_allow_html=True)
col_e1, col_e2, col_e3, _ = st.columns([1, 1, 1, 3])
with col_e1:
    csv = df_filt.drop(columns=["_sheet_row"], errors="ignore").to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("CSV", icon=":material/description:", data=csv, file_name="estoque_materiais.csv", mime="text/csv", width="stretch")
with col_e2:
    excel = BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        df_filt.drop(columns=["_sheet_row"], errors="ignore").to_excel(writer, index=False, sheet_name="Materiais")
    st.download_button("Excel", icon=":material/table_view:", data=excel.getvalue(), file_name="estoque_materiais.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
with col_e3:
    if HAS_REPORTLAB:
        pdf = gerar_pdf_materiais(display_df)
        st.download_button("PDF", icon=":material/picture_as_pdf:", data=pdf, file_name="estoque_materiais.pdf", mime="application/pdf", width="stretch")
    else:
        st.info("PDF indisponível: reportlab não está instalado neste ambiente.")
