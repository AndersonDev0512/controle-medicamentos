import streamlit as st
import pandas as pd
from services.estoque_service import (
    get_estoque,
    get_medicamentos_list,
    get_lotes_por_medicamento,
    get_quantidade_disponivel,
    get_materiales_list,
    get_lotes_por_material,
    get_quantidade_disponivel_material,
)
from services.aplicacao_service import registrar_aplicacao, proximo_id_registro
from services.sheets_service import ler_registro_diario
from utils.helpers import formatar_data_hora

st.markdown('<h1 class="page-title">💉 Registrar Aplicação</h1>', unsafe_allow_html=True)

medicamentos = get_medicamentos_list()
materiales = get_materiales_list()

if not medicamentos:
    st.warning("Nenhum medicamento em estoque. Cadastre medicamentos primeiro.")
    if st.button("➕ Ir para Cadastro"):
        st.switch_page("pages/cadastrar_medicamento.py")
    st.stop()

st.markdown('<div class="section-header">Dados da Aplicação</div>', unsafe_allow_html=True)

c0, c1, c2 = st.columns([1, 2, 2])
with c0:
    st.text_input("ID", value=str(proximo_id_registro()), disabled=True, key="aplicacao_id")
with c1:
    med_sel = st.selectbox("Medicamento *", options=medicamentos, key="aplicacao_medicamento")
with c2:
    lotes = get_lotes_por_medicamento(med_sel)
    lote_atual = st.session_state.get("aplicacao_lote")
    if lote_atual not in lotes:
        st.session_state["aplicacao_lote"] = lotes[0] if lotes else "—"
    lote_sel = st.selectbox("Lote do Medicamento *", options=lotes if lotes else ["—"], key="aplicacao_lote")

c3, c4 = st.columns(2)
with c3:
    material_sel = st.selectbox("Material", options=["Nenhum"] + materiales, key="aplicacao_material")
with c4:
    data_hora_atual = st.text_input("Data/Hora *", value=formatar_data_hora(), disabled=True, key="aplicacao_data_hora")

lote_material_sel = "—"
qtd_material_disponivel = 0
if material_sel != "Nenhum":
    lotes_material = get_lotes_por_material(material_sel)
    lote_material_atual = st.session_state.get("aplicacao_lote_material")
    if lote_material_atual not in lotes_material:
        st.session_state["aplicacao_lote_material"] = lotes_material[0] if lotes_material else "—"
    lote_material_sel = st.selectbox("Lote do Material *", options=lotes_material if lotes_material else ["—"], key="aplicacao_lote_material")
    qtd_material_disponivel = get_quantidade_disponivel_material(material_sel, lote_material_sel) if lote_material_sel != "—" else 0
    tipo_material = st.text_input("Tipo do Material", placeholder="Tipo ou categoria do material")
else:
    tipo_material = ""

qtd_disponivel = get_quantidade_disponivel(med_sel, lote_sel) if lote_sel != "—" else 0
st.markdown(
    f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:0.75rem 1rem;margin:0.5rem 0;">'
    f'📦 Quantidade disponível do medicamento: <b style="color:#22c55e;font-size:1.1rem;">{qtd_disponivel}</b></div>',
    unsafe_allow_html=True,
)
if material_sel != "Nenhum":
    st.markdown(
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:0.75rem 1rem;margin:0.5rem 0;">'
        f'🧴 Quantidade disponível do material: <b style="color:#22c55e;font-size:1.1rem;">{qtd_material_disponivel}</b></div>',
        unsafe_allow_html=True,
    )

with st.form("form_aplicacao"):
    qtd_medicamento = st.number_input(
        "Quantidade de Medicamento *",
        min_value=1,
        max_value=max(qtd_disponivel, 1),
        step=1,
        value=min(1, max(qtd_disponivel, 1)),
    )
    if material_sel != "Nenhum":
        qtd_material = st.number_input(
            "Quantidade de Material *",
            min_value=1,
            max_value=max(qtd_material_disponivel, 1),
            step=1,
            value=min(1, max(qtd_material_disponivel, 1)),
        )
    else:
        qtd_material = 0
    aplicador = st.text_input("Aplicador *", value="Stephanny", placeholder="Nome do responsável")
    paciente = st.text_input("Paciente *", placeholder="Nome do paciente")
    observacao = st.text_area("Observação")
    justificativa = st.text_area("Justificativa obrigatória *", placeholder="Descreva o motivo da aplicação/ajuste.")

    btn_registrar = st.form_submit_button("💉 Registrar Aplicação", width='stretch')

if btn_registrar:
    if lote_sel == "—":
        st.error("Selecione um lote válido do medicamento.")
    elif qtd_medicamento > qtd_disponivel:
        st.error(f"Quantidade insuficiente do medicamento. Disponível: {qtd_disponivel}")
    elif not aplicador.strip():
        st.error("Informe o Aplicador.")
    elif not paciente.strip():
        st.error("Nome do paciente é obrigatório.")
    elif not justificativa.strip():
        st.error("Justificativa é obrigatória.")
    elif material_sel != "Nenhum" and lote_material_sel == "—":
        st.error("Selecione um lote válido do material.")
    elif material_sel != "Nenhum" and qtd_material > qtd_material_disponivel:
        st.error(f"Quantidade insuficiente do material. Disponível: {qtd_material_disponivel}")
    else:
        with st.spinner("Registrando aplicação..."):
            ok, msg = registrar_aplicacao(
                med_sel,
                lote_sel,
                int(qtd_medicamento),
                material=material_sel if material_sel != "Nenhum" else None,
                lote_material=lote_material_sel if material_sel != "Nenhum" else None,
                quantidade_material=int(qtd_material),
                tipo_material=tipo_material.strip(),
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

st.markdown('<div class="section-header">Últimas aplicações</div>', unsafe_allow_html=True)
recentes = ler_registro_diario()
if recentes.empty:
    st.info("Nenhuma aplicação registrada ainda.")
else:
    recentes = recentes.sort_values("Data Hora", ascending=False, na_position="last")
    exibir = recentes[[
        "ID", "Data Hora", "Medicamento", "Lote", "Quantidade Medicamento",
        "Quantidade Material", "Material", "Lote Material", "Tipo Material",
        "Aplicador", "Paciente", "Observação",
    ]].head(10).copy()
    st.dataframe(exibir, use_container_width=True, hide_index=True)
