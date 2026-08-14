import streamlit as st
import plotly.graph_objects as go
from services.dashboard_service import (
    get_kpis,
    get_chart_status,
    get_chart_quantidade_por_medicamento,
    get_chart_aplicacoes_diarias,
    get_chart_mais_utilizados,
)
from utils.helpers import metric_card
from utils.constants import CORES_STATUS

_BG = "#1e293b"
_FONT = "#f8fafc"
_GRID = "#334155"


def _layout(title: str = "") -> dict:
    return dict(
        plot_bgcolor=_BG,
        paper_bgcolor=_BG,
        font=dict(color=_FONT, size=12),
        title=dict(text=title, font=dict(color=_FONT, size=14), x=0),
        margin=dict(l=20, r=20, t=45, b=20),
        xaxis=dict(gridcolor=_GRID, zerolinecolor=_GRID),
        yaxis=dict(gridcolor=_GRID, zerolinecolor=_GRID),
        legend=dict(font=dict(color=_FONT)),
    )


st.markdown('<h1 class="page-title">📊 Dashboard</h1>', unsafe_allow_html=True)

kpis = get_kpis()

# ── KPI Cards ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(metric_card("Medicamentos", kpis["total_medicamentos"], "💊", "#2563eb"), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("Vencidos", kpis["vencidos"], "❌", "#ef4444"), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("Atenção (<30d)", kpis["atencao"], "🔶", "#f97316"), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card("Próximos (<90d)", kpis["proximos"], "⚠️", "#f59e0b"), unsafe_allow_html=True)
with c5:
    st.markdown(metric_card("Estoque OK", kpis["ok"], "✅", "#22c55e"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Status donut + Stock bar ───────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    df_status = get_chart_status()
    if not df_status.empty:
        cores = [CORES_STATUS.get(s, "#6b7280") for s in df_status["Status"]]
        fig = go.Figure(go.Pie(
            labels=df_status["Status"],
            values=df_status["Quantidade"],
            marker=dict(colors=cores, line=dict(color=_BG, width=2)),
            hole=0.48,
            textinfo="label+percent",
            textfont=dict(color=_FONT),
        ))
        fig.update_layout(**_layout("Status dos Medicamentos"))
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Sem dados de status.")

with col2:
    df_qtd = get_chart_quantidade_por_medicamento()
    if not df_qtd.empty:
        top = df_qtd.head(10)
        fig = go.Figure(go.Bar(
            x=top["Quantidade"],
            y=top["Medicamento"],
            orientation="h",
            marker=dict(color="#2563eb"),
            text=top["Quantidade"],
            textposition="outside",
            textfont=dict(color=_FONT),
        ))
        fig.update_layout(**_layout("Quantidade em Estoque (Top 10)"))
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Sem dados de estoque.")

# ── Row 2: Daily applications + Most used ─────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    df_ap = get_chart_aplicacoes_diarias()
    if not df_ap.empty:
        fig = go.Figure(go.Scatter(
            x=df_ap["Data"],
            y=df_ap["Aplicações"],
            mode="lines+markers",
            line=dict(color="#22c55e", width=2),
            marker=dict(color="#22c55e", size=6),
            fill="tozeroy",
            fillcolor="rgba(34,197,94,0.1)",
        ))
        fig.update_layout(**_layout("Aplicações por Dia"))
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Sem dados de aplicações registradas.")

with col4:
    df_mais = get_chart_mais_utilizados()
    if not df_mais.empty:
        fig = go.Figure(go.Bar(
            x=df_mais["Total"],
            y=df_mais["Medicamento"],
            orientation="h",
            marker=dict(color="#8b5cf6"),
            text=df_mais["Total"],
            textposition="outside",
            textfont=dict(color=_FONT),
        ))
        fig.update_layout(**_layout("Top 10 Mais Utilizados"))
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Sem dados de utilização registrados.")

# Embedded Looker report (centralized in the dashboard page)
import streamlit.components.v1 as components
looker_url = "https://lookerstudio.google.com/embed/reporting/31bc0f2d-27e1-466f-8759-8d73ff05c5cf/page/aoNyF"

st.markdown('<hr/>', unsafe_allow_html=True)
st.markdown('<div class="section-header">Relatório</div>', unsafe_allow_html=True)
# Provide tabs so user can switch between native charts and embedded report if desired
tab1, tab2 = st.tabs(["Visualizações Nativas", "Relatório Looker"])

with tab1:
    st.write('Visualizações do Dashboard estão acima.')

with tab2:
    components.html(f"""
        <iframe src="{looker_url}" style="width:100%;height:800px;border:none;" allowfullscreen></iframe>
    """, height=820)
