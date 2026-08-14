import streamlit as st
from services.estoque_service import get_estoque
from services.dashboard_service import get_kpis
from utils.helpers import metric_card

st.markdown('<h1 class="page-title">🏠 Página Inicial</h1>', unsafe_allow_html=True)

# KPIs
kpis = get_kpis()
kc1, kc2, kc3, kc4, kc5 = st.columns(5)
with kc1:
    st.markdown(metric_card("Medicamentos", kpis.get('total_medicamentos', 0), "💊", "#2563eb"), unsafe_allow_html=True)
with kc2:
    st.markdown(metric_card("Vencidos", kpis.get('vencidos', 0), "❌", "#ef4444"), unsafe_allow_html=True)
with kc3:
    st.markdown(metric_card("Atenção (<30d)", kpis.get('atencao', 0), "🔶", "#f97316"), unsafe_allow_html=True)
with kc4:
    st.markdown(metric_card("Próximos (<90d)", kpis.get('proximos', 0), "⚠️", "#f59e0b"), unsafe_allow_html=True)
with kc5:
    st.markdown(metric_card("Estoque OK", kpis.get('ok', 0), "✅", "#22c55e"), unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

col_main, col_side = st.columns([3, 1])

with col_main:
    st.markdown('<div class="section-header">Últimos Medicamentos Cadastrados</div>', unsafe_allow_html=True)
    df = get_estoque()
    if not df.empty:
        colunas = ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Status"]
        st.dataframe(df[colunas].tail(10).iloc[::-1], width='stretch', hide_index=True)
    else:
        st.info("Nenhum medicamento cadastrado. Clique em **Cadastrar Medicamento** para começar.")

with col_side:
    st.markdown('<div class="section-header">Ações Rápidas</div>', unsafe_allow_html=True)
    if st.button("➕ Cadastrar Medicamento", width='stretch'):
        st.switch_page("pages/cadastrar_medicamento.py")
    if st.button("💉 Registrar Aplicação", width='stretch'):
        st.switch_page("pages/registrar_aplicacao.py")
    if st.button("⚠️ Ver Alertas", width='stretch'):
        st.switch_page("pages/alertas.py")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📊 Ir para Dashboard", width='stretch'):
        st.switch_page("pages/dashboard.py")
    # Removed external link to Looker to keep UX in single screen; use Dashboard page to view report.
