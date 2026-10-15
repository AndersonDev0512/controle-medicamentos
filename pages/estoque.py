import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
# pyright: reportMissingModuleSource=false
from io import BytesIO
from services.estoque_service import get_estoque
from services.estoque_service import get_materiais
from utils.config import get_config
from utils.constants import STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK
from utils.helpers import normalizar_texto, render_responsive_table, status_label
from utils.constants import CARRINHO_SIM
from utils.components import stock_summary


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

    dataframe = dataframe.copy()
    dataframe["_dias_ordem"] = pd.to_numeric(dataframe.get("Dias para Vencer"), errors="coerce")
    dataframe["_nome_ordem"] = dataframe.get("Medicamento", "").astype(str).str.casefold()
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
    estilos = getSampleStyleSheet()
    colunas = ["Medicamento", "Quantidade", "Unidade de Medida", "Quantidade Fechada", "Saldo Aberto", "Volume por Unidade", "Unidade Fracionada", "Lote", "Data de Vencimento", "Dias para Vencer", "Status"]
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
    documento.build([Paragraph(titulo, estilos["Title"]), Paragraph(f"Relatório emitido dia {datetime.now():%d/%m/%Y %H:%M:%S}", estilos["Normal"]), Spacer(1, 0.15 * inch), tabela])
    return buffer.getvalue()

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

st.markdown('<h1 class="page-title">📦 Estoque Geral</h1>', unsafe_allow_html=True)

tab_estoque_medicamentos, tab_estoque_materiais, tab_planilha_medicamentos = st.tabs([
    "💊 Estoque de Medicamentos",
    "🧴 Estoque de Materiais",
    "📋 Planilha de Medicamentos",
])

with tab_planilha_medicamentos:
    st.markdown(
        '<div class="section-header">Planilha de Medicamentos</div>',
        unsafe_allow_html=True,
    )
    st.caption("Visualização direta da planilha usada pelo estoque de medicamentos.")

    config = get_config()
    spreadsheet_id = config.spreadsheet_id

    if "/spreadsheets/d/" in spreadsheet_id:
        spreadsheet_id = (
            spreadsheet_id
            .split("/spreadsheets/d/", 1)[1]
            .split("/", 1)[0]
        )

    if spreadsheet_id:
        components.iframe(
            (
                "https://docs.google.com/spreadsheets/d/"
                f"{spreadsheet_id}/edit?gid=0&rm=minimal#gid=0"
            ),
            height=860,
            scrolling=True,
        )
    else:
        st.warning("Configure o SPREADSHEET_ID para visualizar a planilha de medicamentos.")

with tab_estoque_medicamentos:
    df = get_estoque()

    if df.empty:
        st.info(
            "Nenhum medicamento cadastrado. "
            "Acesse **Cadastrar Medicamento** para começar."
        )

        if st.button("➕ Cadastrar agora"):
            st.switch_page("pages/cadastrar_medicamento.py")

        st.stop()

    st.markdown(
        '<div class="section-header">Filtros avançados</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([3, 2, 1])

    # ?carrinho=1 (KPI da Página Inicial) liga o filtro do Carrinho de Parada uma vez
    if st.query_params.get("carrinho"):
        st.session_state["apenas_carrinho_medicamento"] = True
        del st.query_params["carrinho"]

    # ?busca=<lote> (vindo da Central de alertas) preenche a pesquisa uma vez
    if st.query_params.get("busca"):
        st.session_state["pesquisa_medicamento"] = st.query_params["busca"]
        del st.query_params["busca"]

    with col1:
        pesquisa = st.text_input(
            "🔍 Pesquisar por medicamento ou lote",
            placeholder="Ex.: Ácido, 05143 ou AMP",
            key="pesquisa_medicamento",
        )

    with col2:
        filtro_status = st.selectbox(
            "Filtrar por status",
            [
                "Todos",
                STATUS_VENCIDO,
                STATUS_CRITICO,
                STATUS_ATENCAO,
                STATUS_PROXIMO,
                STATUS_OK,
            ],
            key="filtro_status_medicamento",
        )

    with col3:
        ordenar = st.selectbox(
            "Ordenar por",
            [
                "Medicamento",
                "Dias para Vencer",
                "Quantidade",
                "Data de Vencimento",
                "Status",
            ],
            key="ordenar_medicamento",
        )

    col4, col5, col6, col7 = st.columns(4)

    with col4:
        quantidade_minima = st.number_input(
            "Quantidade mínima",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="quantidade_minima_medicamento",
        )

    with col5:
        quantidade_maxima = st.number_input(
            "Quantidade máxima",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Use 0 para não limitar.",
            key="quantidade_maxima_medicamento",
        )

    with col6:
        apenas_vencendo = st.checkbox(
            "Vencimento nos próximos 120 dias",
            key="apenas_vencendo_medicamento",
        )

    with col7:
        apenas_carrinho = st.checkbox(
            "Somente Carrinho de Parada",
            key="apenas_carrinho_medicamento",
        )

    df_filt = df.copy()

    if pesquisa.strip():
        termo = normalizar_texto(pesquisa)

        mascara = (
            df_filt["Medicamento"]
            .map(normalizar_texto)
            .str.contains(termo, regex=False, na=False)
        )

        mascara |= (
            df_filt["Lote"]
            .map(normalizar_texto)
            .str.contains(termo, regex=False, na=False)
        )

        df_filt = df_filt[mascara]

    if filtro_status != "Todos":
        df_filt = df_filt[
            df_filt["Status"] == filtro_status
        ]

    quantidades = pd.to_numeric(
        df_filt["Quantidade"],
        errors="coerce",
    ).fillna(0)

    df_filt = df_filt[
        quantidades >= quantidade_minima
    ]

    if quantidade_maxima > 0:
        quantidades = pd.to_numeric(
            df_filt["Quantidade"],
            errors="coerce",
        ).fillna(0)

        df_filt = df_filt[
            quantidades <= quantidade_maxima
        ]

    if apenas_vencendo:
        dias = pd.to_numeric(
            df_filt["Dias para Vencer"],
            errors="coerce",
        )

        df_filt = df_filt[
            dias.between(0, 120)
        ]

    if apenas_carrinho:
        df_filt = df_filt[df_filt["Carrinho de Parada"] == CARRINHO_SIM]

    ascending = ordenar not in {
        "Dias para Vencer",
        "Quantidade",
    }

    df_filt = df_filt.sort_values(
        ordenar,
        ascending=ascending,
        na_position="last",
    )

    display_df = df_filt.copy()

    display_df["Status"] = display_df["Status"].map(
        lambda status: status_label(str(status))
    )
    display_df["Carrinho de Parada"] = display_df["Carrinho de Parada"].map({"S": "Sim", "N": "Não"})

    st.caption(
        f"Exibindo {len(df_filt)} de {len(df)} registro(s)"
    )

    colunas_estoque = [
        "Medicamento",
        "Quantidade",
        "Unidade de Medida",
        "Quantidade Fechada",
        "Saldo Aberto",
        "Volume por Unidade",
        "Unidade Fracionada",
        "Lote",
        "Data de Vencimento",
        "Dias para Vencer",
        "Status",
        "Carrinho de Parada",
    ]

    colunas_existentes = [
        coluna
        for coluna in colunas_estoque
        if coluna in display_df.columns
    ]

    render_responsive_table(display_df[colunas_existentes])

    st.html(stock_summary(df_filt, len(df), "medicamentos"))

    st.markdown(
        '<div class="section-header">'
        "Exportar resultado"
        "</div>",
        unsafe_allow_html=True,
    )

    col_e1, col_e2, col_e3, _ = st.columns(
        [1, 1, 1, 3]
    )

    exportacao = df_filt.drop(
        columns=["_sheet_row"],
        errors="ignore",
    )

    with col_e1:
        csv = exportacao.to_csv(
            index=False,
            encoding="utf-8-sig",
        ).encode("utf-8-sig")

        st.download_button(
            "CSV",
            icon=":material/description:",
            data=csv,
            file_name="estoque_medicamentos.csv",
            mime="text/csv",
            width="stretch",
        )

    with col_e2:
        excel = BytesIO()

        with pd.ExcelWriter(
            excel,
            engine="openpyxl",
        ) as writer:
            exportacao.to_excel(
                writer,
                index=False,
                sheet_name="Estoque",
            )

        st.download_button(
            "Excel",
            icon=":material/table_view:",
            data=excel.getvalue(),
            file_name="estoque_medicamentos.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            width="stretch",
        )

    with col_e3:
        if HAS_REPORTLAB:
            pdf = gerar_pdf_estoque(
                display_df,
                "Estoque de Medicamentos",
            )

            st.download_button(
                "PDF",
                icon=":material/picture_as_pdf:",
                data=pdf,
                file_name="estoque_medicamentos.pdf",
                mime="application/pdf",
                width="stretch",
            )
        else:
            st.info(
                "PDF indisponível: reportlab não está instalado."
            )

with tab_estoque_materiais:
    df = get_materiais()

    if df.empty:
        st.info("Nenhum material cadastrado. Acesse **Cadastrar Material** para começar.")
        if st.button("➕ Cadastrar agora"):
            st.switch_page("pages/cadastrar_material.py")
        st.stop()

    st.markdown('<div class="section-header">Filtros avançados</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        pesquisa = st.text_input("🔍 Pesquisar por material ou lote", placeholder="Ex.: Seringa, seringa, 05143 ou CX", key="pesquisa_material")
    with c2:
        filtro_status = st.selectbox("Filtrar por status", ["Todos", STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK], key="filtro_status_material")
    with c3:
        ordenar = st.selectbox("Ordenar por", ["Material", "Dias para Vencer", "Quantidade", "Data de Vencimento", "Status"], key="ordenar_material")

    c4, c5, c6, c7 = st.columns(4)
    with c4:
        quantidade_minima = st.number_input("Quantidade mínima", min_value=0, value=0, step=1, key="quantidade_minima_material")
    with c5:
        quantidade_maxima = st.number_input("Quantidade máxima", min_value=0, value=0, step=1, help="Use 0 para não limitar.", key="quantidade_maxima_material")
    with c6:
        apenas_vencendo = st.checkbox("Vencimento nos próximos 120 dias", key="apenas_vencendo_material")
    with c7:
        apenas_carrinho = st.checkbox("Somente Carrinho de Parada", key="apenas_carrinho_material")

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