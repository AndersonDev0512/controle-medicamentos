import streamlit as st
import pandas as pd
import json
import html
from datetime import date, timedelta
from io import BytesIO

HAS_REPORTLAB = True
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:
    HAS_REPORTLAB = False

from services.estoque_service import get_estoque, get_materiais
from services.sheets_service import ler_historico, ler_registro_diario
from utils.constants import TIPOS_MOVIMENTACAO
from utils.helpers import render_responsive_table


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
    styles = _estilos_relatorio()
    documento.build(
        _elementos_relatorio(dataframe, data_referencia, styles),
        onFirstPage=_rodape_relatorio,
        onLaterPages=_rodape_relatorio,
    )
    return buffer.getvalue()


def _itens_json(valor: object, nome: str) -> list[dict]:
    try:
        itens = json.loads(str(valor)) if str(valor).strip() else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if isinstance(itens, dict):
        itens = itens.get("itens", [itens])
    if not isinstance(itens, list):
        return []
    return [item for item in itens if isinstance(item, dict) and item.get(nome)]


def _texto_itens(valor: object, nome: str) -> str:
    itens = _itens_json(valor, nome)
    textos = []
    for item in itens:
        quantidade = item.get("quantidade", "")
        lote = item.get("lote", "")
        unidade = item.get("unidade", "")
        detalhe = f" - {quantidade} {unidade}" if quantidade != "" else ""
        detalhe += f" - lote {lote}" if lote else ""
        textos.append(f"{item[nome]}{detalhe}")
    return "<br/>".join(textos)


def _estilos_relatorio() -> dict:
    styles = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "RelatorioTitulo", parent=styles["Title"], fontName="Helvetica-Bold",
            fontSize=16, leading=19, textColor=colors.HexColor("#12304A"),
            alignment=1, spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "RelatorioSubtitulo", parent=styles["Normal"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=colors.HexColor("#547086"), alignment=1,
            spaceAfter=12,
        ),
        "dia": ParagraphStyle(
            "RelatorioDia", parent=styles["Heading2"], fontName="Helvetica-Bold",
            fontSize=10, leading=12, textColor=colors.white, spaceBefore=8, spaceAfter=0,
        ),
        "celula": ParagraphStyle(
            "RelatorioCelula", parent=styles["BodyText"], fontName="Helvetica",
            fontSize=7.2, leading=9, textColor=colors.HexColor("#253746"), spaceAfter=0,
        ),
        "celula_cabecalho": ParagraphStyle(
            "RelatorioCabecalho", parent=styles["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.4, leading=9, textColor=colors.white, spaceAfter=0,
        ),
    }


def _estilo_tabela_relatorio() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#167D9A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7CAD4")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF7F9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])


def _rodape_relatorio(canvas, documento) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B7CAD4"))
    canvas.setLineWidth(0.4)
    canvas.line(documento.leftMargin, 0.32 * inch, documento.pagesize[0] - documento.rightMargin, 0.32 * inch)
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(colors.HexColor("#547086"))
    canvas.drawString(documento.leftMargin, 0.17 * inch, "Controle de Enfermagem  |  Documento assistencial")
    canvas.drawRightString(documento.pagesize[0] - documento.rightMargin, 0.17 * inch, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def _valor_linha(linha: pd.Series, coluna: str, styles: dict) -> Paragraph:
    if coluna == "Data Hora":
        valor = str(linha.get("Data Hora", "")).replace(" ", "<br/>", 1)
    elif coluna == "Medicamentos Usados":
        valor = _texto_itens(linha.get("Medicamentos JSON", ""), "medicamento") or str(linha.get("Medicamento", ""))
    elif coluna == "Materiais Usados":
        valor = _texto_itens(linha.get("Materiais JSON", ""), "material") or str(linha.get("Material", ""))
    else:
        valor = str(linha.get(coluna, ""))
    return Paragraph(html.escape(valor, quote=False).replace("&lt;br/&gt;", "<br/>"), styles["celula"])


def _elementos_relatorio(dataframe: pd.DataFrame, periodo: str, styles: dict) -> list:
    elementos = [
        Paragraph("RELATÓRIO DE APLICAÇÕES", styles["titulo"]),
        Paragraph(f"Período: {html.escape(periodo)}  |  Documento assistencial", styles["subtitulo"]),
    ]
    colunas = ["Data Hora", "Paciente", "Medicamentos Usados", "Materiais Usados", "Observação"]
    dados = dataframe.copy()
    dados["_dt"] = pd.to_datetime(dados.get("Data Hora", ""), format="%d/%m/%Y %H:%M:%S", errors="coerce")
    dados["_dia"] = dados["_dt"].dt.date
    dados = dados.sort_values("_dt", ascending=True, na_position="last")
    grupos = list(dados.groupby("_dia", dropna=False))
    for indice, (dia, grupo) in enumerate(grupos):
        dia_label = dia.strftime("%d/%m/%Y") if hasattr(dia, "strftime") else "Data não informada"
        faixa_dia = Table([[Paragraph(f"DIA {dia_label}", styles["dia"])]], colWidths=[10.4 * inch])
        faixa_dia.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#245B78")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(faixa_dia)
        corpo = [[Paragraph(coluna, styles["celula_cabecalho"]) for coluna in colunas]]
        corpo.extend([[_valor_linha(linha, coluna, styles) for coluna in colunas] for _, linha in grupo.iterrows()])
        tabela = Table(corpo, repeatRows=1, colWidths=[1.05 * inch, 1.25 * inch, 2.85 * inch, 2.85 * inch, 2.4 * inch])
        tabela.setStyle(_estilo_tabela_relatorio())
        elementos.append(tabela)
        if indice < len(grupos) - 1:
            elementos.append(Spacer(1, 0.14 * inch))
    return elementos


def gerar_pdf_relatorio_personalizado(dataframe: pd.DataFrame, inicio: date, fim: date) -> bytes:
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
    periodo = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    documento.build(
        _elementos_relatorio(dataframe, periodo, _estilos_relatorio()),
        onFirstPage=_rodape_relatorio,
        onLaterPages=_rodape_relatorio,
    )
    return buffer.getvalue()


def gerar_pdf_estoque_personalizado(dataframe: pd.DataFrame, titulo: str, colunas: list[str]) -> bytes:
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
    estilos = _estilos_relatorio()
    tabela = [[Paragraph(coluna, estilos["celula_cabecalho"]) for coluna in colunas]]
    for _, linha in dataframe.reindex(columns=colunas, fill_value="").iterrows():
        tabela.append([
            Paragraph(html.escape(str(linha.get(coluna, ""))), estilos["celula"])
            for coluna in colunas
        ])
    tabela_pdf = Table(tabela, repeatRows=1)
    tabela_pdf.setStyle(_estilo_tabela_relatorio())
    documento.build([
        Paragraph(html.escape(titulo).upper(), estilos["titulo"]),
        Paragraph("Documento de controle de estoque | Gerado pelo sistema", estilos["subtitulo"]),
        tabela_pdf,
    ], onFirstPage=_rodape_relatorio, onLaterPages=_rodape_relatorio)
    return buffer.getvalue()

st.markdown('<h1 class="page-title">📊 Relatórios</h1>', unsafe_allow_html=True)
st.caption("Gere relatórios prontos ou personalizados a partir das movimentações registradas.")

df = ler_historico()
df_registros = ler_registro_diario()

# Atalhos da Página Inicial (Ações rápidas > Relatórios) chegam por ?rel=...; valem uma vez.
_atalho = st.query_params.get("rel", "")
_auto_aplicacoes = _auto_estoque = False
if _atalho == "aplicacoes":
    _dias = {"semana": 6}.get(st.query_params.get("periodo", ""))
    _fim = date.today()
    st.session_state["rel_inicio"] = _fim - timedelta(days=_dias) if _dias else _fim.replace(day=1)
    st.session_state["rel_fim"] = _fim
    _auto_aplicacoes = True
elif _atalho == "estoque":
    st.session_state["relatorio_estoque_tipo"] = "Materiais" if st.query_params.get("inv") == "materiais" else "Medicamentos"
    st.session_state["_rel_status_atalho"] = st.query_params.get("status", "Todos")
    _auto_estoque = True
for _param in ("rel", "periodo", "inv", "status"):
    st.query_params.pop(_param, None)

st.markdown('<div class="section-header">Relatório Personalizado — Aplicações</div>', unsafe_allow_html=True)
st.caption("Relatório fechado de aplicações por intervalo de datas.")
with st.form("form_relatorio_personalizado"):
    rel_col1, rel_col2 = st.columns(2)
    datas_aplicacoes = pd.to_datetime(
        df_registros.get("Data Hora", pd.Series(dtype=str)).astype(str),
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    ).dropna()
    data_inicial_padrao = datas_aplicacoes.min().date() if not datas_aplicacoes.empty else date.today()
    data_final_padrao = datas_aplicacoes.max().date() if not datas_aplicacoes.empty else date.today()
    st.session_state.setdefault("rel_inicio", data_inicial_padrao)
    st.session_state.setdefault("rel_fim", data_final_padrao)
    with rel_col1:
        rel_inicio = st.date_input("Data inicial da aplicação", format="DD/MM/YYYY", key="rel_inicio")
    with rel_col2:
        rel_fim = st.date_input("Data final da aplicação", format="DD/MM/YYYY", key="rel_fim")
    gerar_relatorio = st.form_submit_button("📑 Gerar relatório personalizado", width="stretch")

if gerar_relatorio or _auto_aplicacoes:
    if rel_inicio > rel_fim:
        st.error("A data inicial não pode ser maior que a data final.")
    elif df_registros.empty:
        st.warning("Nenhuma aplicação registrada no período selecionado.")
    else:
        relatorio_personalizado = df_registros.copy()
        relatorio_personalizado["_dt"] = pd.to_datetime(
            relatorio_personalizado["Data Hora"].astype(str),
            format="%d/%m/%Y %H:%M:%S",
            errors="coerce",
        )
        relatorio_personalizado = relatorio_personalizado[
            (relatorio_personalizado["_dt"] >= pd.Timestamp(rel_inicio))
            & (relatorio_personalizado["_dt"] < pd.Timestamp(rel_fim) + pd.Timedelta(days=1))
        ].sort_values("_dt", ascending=True)

        if relatorio_personalizado.empty:
            st.warning("Nenhuma aplicação registrada no período selecionado.")
        else:
            exibicao = relatorio_personalizado.copy()
            exibicao["Medicamentos Usados"] = exibicao.apply(
                lambda linha: _texto_itens(linha.get("Medicamentos JSON", ""), "medicamento")
                or str(linha.get("Medicamento", "")),
                axis=1,
            )
            exibicao["Materiais Usados"] = exibicao.apply(
                lambda linha: _texto_itens(linha.get("Materiais JSON", ""), "material")
                or str(linha.get("Material", "")),
                axis=1,
            )
            exibicao["Medicamentos Usados"] = exibicao["Medicamentos Usados"].str.replace("<br/>", "\n", regex=False)
            exibicao["Materiais Usados"] = exibicao["Materiais Usados"].str.replace("<br/>", "\n", regex=False)
            exibicao = exibicao.rename(columns={"Data Hora": "Data/Hora"})
            colunas_exibicao = ["Data/Hora", "Paciente", "Medicamentos Usados", "Materiais Usados", "Observação"]
            render_responsive_table(exibicao.reindex(columns=colunas_exibicao, fill_value=""))

            if HAS_REPORTLAB:
                pdf_personalizado = gerar_pdf_relatorio_personalizado(
                    relatorio_personalizado,
                    rel_inicio,
                    rel_fim,
                )
                st.download_button(
                    "⬇️ Baixar PDF do período",
                    data=pdf_personalizado,
                    file_name=f"relatorio_aplicacoes_{rel_inicio:%Y%m%d}_{rel_fim:%Y%m%d}.pdf",
                    mime="application/pdf",
                    width="stretch",
                )
            else:
                st.info("PDF indisponível: reportlab não está instalado neste ambiente.")

estoque_medicamentos = get_estoque()
estoque_materiais = get_materiais()

if df.empty and df_registros.empty and estoque_medicamentos.empty and estoque_materiais.empty:
    st.info("Nenhuma movimentação registrada ainda.")
    st.stop()

st.markdown('<div class="section-header">Relatório Personalizado — Estoque</div>', unsafe_allow_html=True)
st.caption("Escolha o tipo de estoque e a situação para gerar um documento paisagem pronto para entrega.")
estoque_col1, estoque_col2, estoque_col3 = st.columns([2, 2, 1])
with estoque_col1:
    tipo_estoque = st.selectbox("Inventário", ["Medicamentos", "Materiais"], key="relatorio_estoque_tipo")
opcoes_status = ["Todos"] + sorted(
    (estoque_medicamentos if tipo_estoque == "Medicamentos" else estoque_materiais).get("Status", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
)
_status_atalho = st.session_state.pop("_rel_status_atalho", None)
if _status_atalho is not None:
    # Situação pedida pelo atalho; se não houver lote nela, o relatório sai vazio em vez de "Todos".
    st.session_state["relatorio_estoque_status"] = _status_atalho if _status_atalho in opcoes_status else "Todos"
    _auto_vazio = _status_atalho not in opcoes_status
else:
    _auto_vazio = False
if st.session_state.get("relatorio_estoque_status") not in opcoes_status:
    st.session_state.pop("relatorio_estoque_status", None)
with estoque_col2:
    status_estoque = st.selectbox("Situação", opcoes_status, key="relatorio_estoque_status")
with estoque_col3:
    gerar_estoque = st.button("📑 Gerar estoque", width="stretch")

if _auto_estoque and _auto_vazio:
    st.info(f"Nenhum lote de {tipo_estoque.lower()} com situação “{_status_atalho}” no momento.")
elif gerar_estoque or _auto_estoque:
    estoque_relatorio = (estoque_medicamentos if tipo_estoque == "Medicamentos" else estoque_materiais).copy()
    if status_estoque != "Todos" and "Status" in estoque_relatorio:
        estoque_relatorio = estoque_relatorio[estoque_relatorio["Status"] == status_estoque]
    colunas_estoque = (
        ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Status"]
        if tipo_estoque == "Medicamentos"
        else ["Material", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Status"]
    )
    render_responsive_table(estoque_relatorio.reindex(columns=colunas_estoque, fill_value=""))
    if HAS_REPORTLAB:
        pdf_estoque = gerar_pdf_estoque_personalizado(
            estoque_relatorio,
            f"Relatório Personalizado — Estoque de {tipo_estoque}",
            colunas_estoque,
        )
        st.download_button(
            "⬇️ Baixar relatório de estoque em PDF",
            data=pdf_estoque,
            file_name=f"relatorio_estoque_{tipo_estoque.lower()}.pdf",
            mime="application/pdf",
            width="stretch",
        )
    else:
        st.info("PDF indisponível: reportlab não está instalado neste ambiente.")

# ── Filters ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Filtros</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    datas_historico = pd.to_datetime(
        df.get("Data Hora", pd.Series(dtype=str)).astype(str),
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    ).dropna()
    dt_ini_padrao = datas_historico.min().date() if not datas_historico.empty else date.today() - timedelta(days=30)
    dt_ini = st.date_input("Data Inicial", value=dt_ini_padrao, format="DD/MM/YYYY")
with c2:
    dt_fim_padrao = datas_historico.max().date() if not datas_historico.empty else date.today()
    dt_fim = st.date_input("Data Final", value=dt_fim_padrao, format="DD/MM/YYYY")
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

render_responsive_table(df_filt)

st.markdown('<div class="section-header">Gerar relatório</div>', unsafe_allow_html=True)
tipo_relatorio = st.selectbox(
    "Tipo de relatório",
    ["Aplicações do período", "Por medicamento", "Por aplicador", "Personalizado"],
)
if tipo_relatorio == "Personalizado":
    campos = st.multiselect(
        "Campos do relatório",
        options=[coluna for coluna in df_filt.columns if coluna != "_dt"],
        default=["Data Hora", "Medicamento", "Quantidade", "Paciente"],
    )
    relatorio = df_filt[campos] if campos else df_filt
else:
    relatorio = df_filt

st.markdown('<div class="section-header">Exportar relatório selecionado</div>', unsafe_allow_html=True)
col1, col2, _ = st.columns([1, 1, 4])
with col1:
    csv = relatorio.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📄 CSV", data=csv, file_name="historico.csv", mime="text/csv", width='stretch')
with col2:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        relatorio.to_excel(w, index=False, sheet_name="Relatório")
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
        pdf = gerar_pdf_aplicacoes(relatorio, hoje)
        st.download_button("📑 Gerar PDF", data=pdf, file_name="relatorio_aplicacoes.pdf", mime="application/pdf", width="stretch")
    else:
        st.info("PDF indisponível: reportlab não está instalado neste ambiente.")
