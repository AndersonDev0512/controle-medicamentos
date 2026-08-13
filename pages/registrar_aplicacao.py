import streamlit as st
from services.estoque_service import (
    get_estoque,
    get_medicamentos_list,
    get_lotes_por_medicamento,
    get_quantidade_disponivel,
)
from services.aplicacao_service import registrar_aplicacao

st.markdown('<h1 class="page-title">💉 Registrar Aplicação</h1>', unsafe_allow_html=True)

medicamentos = get_medicamentos_list()

if not medicamentos:
    st.warning("Nenhum medicamento em estoque. Cadastre medicamentos primeiro.")
    if st.button("➕ Ir para Cadastro"):
        st.switch_page("pages/cadastrar_medicamento.py")
    st.stop()

st.markdown('<div class="section-header">Dados da Aplicação</div>', unsafe_allow_html=True)

with st.form("form_aplicacao"):
    c1, c2 = st.columns(2)
    with c1:
        med_sel = st.selectbox("Medicamento *", options=medicamentos)
    with c2:
        lotes = get_lotes_por_medicamento(med_sel)
        lote_sel = st.selectbox("Lote *", options=lotes if lotes else ["—"])

    qtd_disponivel = get_quantidade_disponivel(med_sel, lote_sel) if lote_sel != "—" else 0

    st.markdown(
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;'
        f'padding:0.75rem 1rem;margin:0.5rem 0;">'
        f'📦 Quantidade disponível: <b style="color:#22c55e;font-size:1.1rem;">{qtd_disponivel}</b></div>',
        unsafe_allow_html=True,
    )

    qtd_aplicar = st.number_input(
        "Quantidade a Aplicar *",
        min_value=1,
        max_value=max(qtd_disponivel, 1),
        step=1,
        value=1,
    )

    btn_registrar = st.form_submit_button("💉 Registrar Aplicação", use_container_width=True)

if btn_registrar:
    if lote_sel == "—":
        st.error("Selecione um lote válido.")
    elif qtd_aplicar > qtd_disponivel:
        st.error(f"Quantidade insuficiente. Disponível: {qtd_disponivel}")
    else:
        with st.spinner("Registrando aplicação..."):
            ok, msg = registrar_aplicacao(med_sel, lote_sel, int(qtd_aplicar))
        if ok:
            st.success(msg)
            # Show updated stock quantity
            novo_disponivel = get_quantidade_disponivel(med_sel, lote_sel)
            st.info(f"Estoque atual de **{med_sel}** (Lote {lote_sel}): **{novo_disponivel}** unidade(s)")
        else:
            st.error(msg)
