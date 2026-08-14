import streamlit as st
from services.estoque_service import (
    get_estoque,
    get_medicamentos_list,
    get_lotes_por_medicamento,
    get_quantidade_disponivel,
    get_materiales_list,
    get_lotes_por_material,
    get_quantidade_disponivel_material,
)
from services.aplicacao_service import registrar_aplicacao

st.markdown('<h1 class="page-title">💉 Registrar Aplicação</h1>', unsafe_allow_html=True)

medicamentos = get_medicamentos_list()
materiales = get_materiales_list()

if not medicamentos:
    st.warning("Nenhum medicamento em estoque. Cadastre medicamentos primeiro.")
    if st.button("➕ Ir para Cadastro"):
        st.switch_page("pages/cadastrar_medicamento.py")
    st.stop()

st.markdown('<div class="section-header">Dados da Aplicação</div>', unsafe_allow_html=True)

with st.form("form_aplicacao"):
    c1, c2, c3 = st.columns(3)
    with c1:
        med_sel = st.selectbox("Medicamento *", options=medicamentos)
    with c2:
        lotes = get_lotes_por_medicamento(med_sel)
        lote_sel = st.selectbox("Lote do Medicamento *", options=lotes if lotes else ["—"])
    with c3:
        material_sel = st.selectbox("Material", options=["Nenhum"] + materiales)

    lote_material_sel = "—"
    qtd_material_disponivel = 0
    if material_sel != "Nenhum":
        lotes_material = get_lotes_por_material(material_sel)
        lote_material_sel = st.selectbox("Lote do Material", options=lotes_material if lotes_material else ["—"])
        qtd_material_disponivel = get_quantidade_disponivel_material(material_sel, lote_material_sel) if lote_material_sel != "—" else 0

    qtd_disponivel = get_quantidade_disponivel(med_sel, lote_sel) if lote_sel != "—" else 0
    st.markdown(
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;'
        f'padding:0.75rem 1rem;margin:0.5rem 0;">'
        f'📦 Quantidade disponível do medicamento: <b style="color:#22c55e;font-size:1.1rem;">{qtd_disponivel}</b></div>',
        unsafe_allow_html=True,
    )
    if material_sel != "Nenhum":
        st.markdown(
            f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;'
            f'padding:0.75rem 1rem;margin:0.5rem 0;">'
            f'🧴 Quantidade disponível do material: <b style="color:#22c55e;font-size:1.1rem;">{qtd_material_disponivel}</b></div>',
            unsafe_allow_html=True,
        )

    qtd_aplicar = st.number_input(
        "Quantidade a Aplicar *",
        min_value=1,
        max_value=max(qtd_disponivel, 1),
        step=1,
        value=1,
    )
    aplicador = st.text_input("Aplicador *", placeholder="Nome do responsável")
    paciente = st.text_input("Paciente")
    observacao = st.text_area("Observação")
    justificativa = st.text_area("Justificativa obrigatória *", placeholder="Descreva o motivo da aplicação/ajuste.")

    btn_registrar = st.form_submit_button("💉 Registrar Aplicação", width='stretch')

if btn_registrar:
    if lote_sel == "—":
        st.error("Selecione um lote válido do medicamento.")
    elif qtd_aplicar > qtd_disponivel:
        st.error(f"Quantidade insuficiente do medicamento. Disponível: {qtd_disponivel}")
    elif not aplicador.strip():
        st.error("Informe o Aplicador.")
    elif not justificativa.strip():
        st.error("Justificativa é obrigatória.")
    elif material_sel != "Nenhum" and lote_material_sel == "—":
        st.error("Selecione um lote válido do material.")
    elif material_sel != "Nenhum" and qtd_aplicar > qtd_material_disponivel:
        st.error(f"Quantidade insuficiente do material. Disponível: {qtd_material_disponivel}")
    else:
        with st.spinner("Registrando aplicação..."):
            ok, msg = registrar_aplicacao(
                med_sel,
                lote_sel,
                int(qtd_aplicar),
                material=material_sel if material_sel != "Nenhum" else None,
                lote_material=lote_material_sel if material_sel != "Nenhum" else None,
                aplicador=aplicador.strip(),
                paciente=paciente.strip(),
                observacao=observacao.strip(),
                justificativa=justificativa.strip(),
            )
        if ok:
            st.success(msg)
            novo_disponivel = get_quantidade_disponivel(med_sel, lote_sel)
            st.info(f"Estoque atual de **{med_sel}** (Lote {lote_sel}): **{novo_disponivel}** unidade(s)")
            if material_sel != "Nenhum":
                novo_material = get_quantidade_disponivel_material(material_sel, lote_material_sel)
                st.info(f"Estoque atual de **{material_sel}** (Lote {lote_material_sel}): **{novo_material}** unidade(s)")
        else:
            st.error(msg)
