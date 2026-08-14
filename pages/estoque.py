import streamlit as st
import pandas as pd
from io import BytesIO
from services.estoque_service import get_estoque
from utils.constants import STATUS_VENCIDO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK
from utils.helpers import status_label

st.markdown('<h1 class="page-title">📦 Estoque de Medicamentos</h1>', unsafe_allow_html=True)

df = get_estoque()

if df.empty:
    st.info("Nenhum medicamento cadastrado. Acesse **Cadastrar Medicamento** para começar.")
    if st.button("➕ Cadastrar agora"):
        st.switch_page("pages/cadastrar_medicamento.py")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    pesquisa = st.text_input("🔍 Pesquisar", placeholder="Nome do medicamento ou lote...")
with c2:
    filtro_status = st.selectbox("Filtrar por Status", ["Todos", STATUS_VENCIDO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK])
with c3:
    ordenar = st.selectbox("Ordenar por", ["Medicamento", "Dias para Vencer", "Quantidade", "Status"])

df_filt = df.copy()
if pesquisa:
    mask = df_filt["Medicamento"].astype(str).str.contains(pesquisa, case=False, na=False)
    mask |= df_filt["Lote"].astype(str).str.contains(pesquisa, case=False, na=False)
    df_filt = df_filt[mask]
if filtro_status != "Todos":
    df_filt = df_filt[df_filt["Status"] == filtro_status]
df_filt = df_filt.sort_values(ordenar, na_position="last")

display_df = df_filt.copy()
display_df["Status"] = display_df["Status"].map(lambda s: status_label(str(s)))

st.markdown(
    f'<p style="color:#94a3b8;font-size:0.85rem;margin-bottom:0.5rem;">'
    f'Exibindo <b>{len(df_filt)}</b> de <b>{len(df)}</b> registro(s)</p>',
    unsafe_allow_html=True,
)

# ── Table ──────────────────────────────────────────────────────────────────────
colunas = ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Dias para Vencer", "Status"]
st.dataframe(display_df[colunas], width='stretch', hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Export ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Exportar</div>', unsafe_allow_html=True)
col_e1, col_e2, _ = st.columns([1, 1, 4])

with col_e1:
    csv = df_filt.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📄 Exportar CSV", data=csv, file_name="estoque.csv", mime="text/csv", width='stretch')

with col_e2:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_filt.to_excel(writer, index=False, sheet_name="Estoque")
    st.download_button(
        "📊 Exportar Excel",
        data=buf.getvalue(),
        file_name="estoque.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width='stretch',
    )
