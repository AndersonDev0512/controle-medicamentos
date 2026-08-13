import streamlit as st
from services.estoque_service import get_estoque

st.markdown('<h1 class="page-title">🏠 Página Inicial</h1>', unsafe_allow_html=True)

col_main, col_side = st.columns([3, 1])

with col_main:
    st.markdown('<div class="section-header">Últimos Medicamentos Cadastrados</div>', unsafe_allow_html=True)
    df = get_estoque()
    if not df.empty:
        colunas = ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Status"]
        st.dataframe(df[colunas].tail(10).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum medicamento cadastrado. Clique em **Cadastrar Medicamento** para começar.")

with col_side:
    st.markdown('<div class="section-header">Ações Rápidas</div>', unsafe_allow_html=True)
    if st.button("➕ Cadastrar Medicamento", use_container_width=True):
        st.switch_page("pages/cadastrar_medicamento.py")
    if st.button("💉 Registrar Aplicação", use_container_width=True):
        st.switch_page("pages/registrar_aplicacao.py")
    if st.button("⚠️ Ver Alertas", use_container_width=True):
        st.switch_page("pages/alertas.py")
