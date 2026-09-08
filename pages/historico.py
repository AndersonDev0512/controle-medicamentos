import streamlit as st
import pandas as pd
import json
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
from services.sheets_service import ler_historico, ler_registro_diario
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
    colunas = ["ID", "Data/Hora", "Paciente", "Medicamentos Usados", "Materiais Usados", "Observação"]
    dados = [colunas]
    for _, linha in dataframe.iterrows():
        dados.append([
            Paragraph(str(linha.get("ID", "")), getSampleStyleSheet()["BodyText"]),
            Paragraph(str(linha.get("Data Hora", "")), getSampleStyleSheet()["BodyText"]),
            Paragraph(str(linha.get("Paciente", "")), getSampleStyleSheet()["BodyText"]),
            Paragraph(_texto_itens(linha.get("Medicamentos JSON", ""), "medicamento") or str(linha.get("Medicamento", "")), getSampleStyleSheet()["BodyText"]),
            Paragraph(_texto_itens(linha.get("Materiais JSON", ""), "material") or str(linha.get("Material", "")), getSampleStyleSheet()["BodyText"]),
            Paragraph(str(linha.get("Observação", "")), getSampleStyleSheet()["BodyText"]),
        ])

    tabela = Table(dados, repeatRows=1, colWidths=[0.45 * inch, 1.2 * inch, 1.4 * inch, 3 * inch, 3 * inch, 2.5 * inch])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    styles = getSampleStyleSheet()
    titulo = f"Relatório de aplicações: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    documento.build([Paragraph(titulo, styles["Title"]), tabela])
    return buffer.getvalue()

st.markdown('<h1 class="page-title">📊 Relatórios</h1>', unsafe_allow_html=True)
st.caption("Gere relatórios prontos ou personalizados a partir das movimentações registradas.")

df = ler_historico()
df_registros = ler_registro_diario()

st.markdown('<div class="section-header">Relatório personalizado</div>', unsafe_allow_html=True)
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
    with rel_col1:
        rel_inicio = st.date_input("Data inicial da aplicação", value=data_inicial_padrao, format="DD/MM/YYYY")
    with rel_col2:
        rel_fim = st.date_input("Data final da aplicação", value=data_final_padrao, format="DD/MM/YYYY")
    gerar_relatorio = st.form_submit_button("📑 Gerar relatório personalizado", width="stretch")

if gerar_relatorio:
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
        ].sort_values("_dt", ascending=False)

        if relatorio_personalizado.empty:
            st.warning("Nenhuma aplicação registrada no período selecionado.")
        else:
            exibicao = relatorio_personalizado.copy()
            exibicao["Medicamentos"] = exibicao.apply(
                lambda linha: _texto_itens(linha.get("Medicamentos JSON", ""), "medicamento")
                or str(linha.get("Medicamento", "")),
                axis=1,
            )
            exibicao["Materiais"] = exibicao.apply(
                lambda linha: _texto_itens(linha.get("Materiais JSON", ""), "material")
                or str(linha.get("Material", "")),
                axis=1,
            )
            exibicao["Medicamentos"] = exibicao["Medicamentos"].str.replace("<br/>", "\n", regex=False)
            exibicao["Materiais"] = exibicao["Materiais"].str.replace("<br/>", "\n", regex=False)
            exibicao = exibicao.rename(columns={"Data Hora": "Data/Hora"})
            colunas_exibicao = ["ID", "Data/Hora", "Paciente", "Medicamentos", "Materiais", "Aplicador", "Observação"]
            st.dataframe(exibicao.reindex(columns=colunas_exibicao, fill_value=""), width="stretch", hide_index=True)

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

if df.empty and df_registros.empty:
    st.info("Nenhuma movimentação registrada ainda.")
    st.stop()

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

st.dataframe(df_filt, width='stretch', hide_index=True)

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
