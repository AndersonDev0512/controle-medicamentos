import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO
from services.sheets_service import ler_historico
from utils.constants import TIPOS_MOVIMENTACAO

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

st.dataframe(df_filt, use_container_width=True, hide_index=True)

# ── Export ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Exportar</div>', unsafe_allow_html=True)
col1, col2, _ = st.columns([1, 1, 4])
with col1:
    csv = df_filt.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📄 CSV", data=csv, file_name="historico.csv", mime="text/csv", use_container_width=True)
with col2:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_filt.to_excel(w, index=False, sheet_name="Histórico")
    st.download_button(
        "📊 Excel",
        data=buf.getvalue(),
        file_name="historico.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
