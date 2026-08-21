import streamlit as st
from datetime import date, datetime
from services.estoque_service import (
    get_materiais,
    get_materiales_list,
    get_lotes_por_material,
    get_unidades_materiais_from_sheet,
)
from services.sheets_service import adicionar_material, atualizar_material, auditar_alteracao, excluir_material
from utils.helpers import formatar_data_hora

st.markdown('<h1 class="page-title">🧴 Cadastrar Material</h1>', unsafe_allow_html=True)

tab_cad, tab_edit, tab_del, tab_cons = st.tabs(["📝 Cadastrar", "✏️ Editar", "🗑️ Excluir", "🔎 Consultar"])

with tab_cad:
    st.markdown('<div class="section-header">Novo(s) Material(is)</div>', unsafe_allow_html=True)
    st.caption("Usuário: Stephanny | Inserção/Revisão: data e hora atual")
    if 'mat_ids' not in st.session_state:
        st.session_state.mat_ids = [0]
        st.session_state.mat_counter = 0

    session_custom_units = st.session_state.get('custom_material_units', [])
    all_units = get_unidades_materiais_from_sheet()
    all_units = sorted(list(dict.fromkeys(all_units + session_custom_units)))
    all_units += ["✏️ Inserir Manualmente", "➕ Inserir Nova Unidade"]

    for row_id in list(st.session_state.mat_ids):
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Material *", key=f"mat_nome_{row_id}")
                st.number_input("Quantidade *", min_value=1, step=1, value=st.session_state.get(f"mat_qtd_{row_id}", 1), key=f"mat_qtd_{row_id}")
                st.selectbox("Unidade de Medida *", options=all_units, key=f"mat_unid_{row_id}")
                sel = st.session_state.get(f"mat_unid_{row_id}")
                if sel == "✏️ Inserir Manualmente":
                    st.text_input("Digite a unidade", placeholder="ex: Caixa(s), Kit(s)...", key=f"mat_unid_manual_{row_id}", label_visibility="collapsed")
                elif sel == "➕ Inserir Nova Unidade":
                    new_u = st.text_input("Nova Unidade", placeholder="ex: Kit(s)", key=f"mat_new_unid_{row_id}")
                    if st.button("Adicionar Unidade", key=f"mat_add_unid_{row_id}"):
                        nu = (new_u or '').strip()
                        if nu:
                            lst = st.session_state.get('custom_material_units', [])
                            if nu not in lst:
                                lst.append(nu)
                                st.session_state['custom_material_units'] = lst
                                st.success(f"Unidade '{nu}' adicionada (sessão).")
                                st.rerun()
                        else:
                            st.error('Digite a unidade antes de adicionar.')
            with c2:
                st.text_input("Lote *", key=f"mat_lote_{row_id}")
                st.date_input("Data de Vencimento *", value=date.today(), format="DD/MM/YYYY", key=f"mat_val_{row_id}")
                st.text_area("Observação", height=68, key=f"mat_obs_{row_id}")
            if len(st.session_state.mat_ids) > 1:
                if st.button("🗑️ Remover", key=f"mat_rem_{row_id}"):
                    st.session_state.mat_ids.remove(row_id)
                    st.rerun()

    _, col_add = st.columns([8, 2])
    with col_add:
        if st.button("➕ Adicionar Material", width='stretch'):
            st.session_state.mat_counter += 1
            st.session_state.mat_ids.append(st.session_state.mat_counter)
            st.rerun()

    if st.button("✅ Cadastrar Material(is)", width='stretch', type="primary"):
        erros = []
        registros = []
        for i, row_id in enumerate(st.session_state.mat_ids):
            nome = st.session_state.get(f"mat_nome_{row_id}", "").strip()
            qtd = st.session_state.get(f"mat_qtd_{row_id}", 1)
            unid_sel = st.session_state.get(f"mat_unid_{row_id}", "")
            unid_manual = st.session_state.get(f"mat_unid_manual_{row_id}", "").strip()
            unidade = unid_manual if unid_sel == "✏️ Inserir Manualmente" else unid_sel
            lote = st.session_state.get(f"mat_lote_{row_id}", "").strip()
            validade = st.session_state.get(f"mat_val_{row_id}", date.today())
            obs = st.session_state.get(f"mat_obs_{row_id}", "").strip()

            if not nome:
                erros.append(f"Material {i+1}: Nome é obrigatório.")
            if not lote:
                erros.append(f"Material {i+1}: Lote é obrigatório.")
            if not unidade:
                erros.append(f"Material {i+1}: Unidade é obrigatória.")
            if nome and lote and unidade:
                registros.append({
                    "Material": nome,
                    "Quantidade": int(qtd),
                    "Unidade de Medida": unidade,
                    "Lote": lote,
                    "Data de Inserção": formatar_data_hora(),
                    "Data de Vencimento": validade.strftime("%d/%m/%Y") if isinstance(validade, date) else str(validade),
                    "Observação": obs,
                })

        if erros:
            for e in erros:
                st.error(e)
        elif registros:
            sucesso = sum(1 for d in registros if adicionar_material(d))
            get_materiais.clear()
            if sucesso == len(registros):
                st.success(f"✅ {sucesso} material(is) cadastrado(s) com sucesso!")
                st.toast(f"{sucesso} material(is) cadastrado(s).", icon="✅")
                st.session_state.mat_ids = [0]
                st.session_state.mat_counter = 0
                for k in [k for k in list(st.session_state.keys()) if k.startswith("mat_")]:
                    del st.session_state[k]
                st.rerun()
            else:
                st.error(f"{len(registros) - sucesso} material(is) não puderam ser cadastrados.")

with tab_edit:
    st.markdown('<div class="section-header">Editar Material</div>', unsafe_allow_html=True)
    df = get_materiais()
    if df.empty:
        st.info("Nenhum material cadastrado.")
    else:
        nomes = get_materiales_list()
        sel_nome = st.selectbox("Selecione o material", options=nomes, key="sel_edit_mat_nome")
        lotes = get_lotes_por_material(sel_nome) if sel_nome else []
        sel_lote = st.selectbox("Selecione o lote", options=lotes, key="sel_edit_mat_lote")
        mask = (df["Material"] == sel_nome) & (df["Lote"] == sel_lote)
        if not mask.any():
            st.info("Selecione um material e lote válidos.")
            st.stop()
        row = df[mask].iloc[0]
        sheet_row = int(row.get('_sheet_row', 2))
        try:
            val_atual = datetime.strptime(str(row["Data de Vencimento"]), "%d/%m/%Y").date()
        except Exception:
            val_atual = date.today()

        all_units_edit = get_unidades_materiais_from_sheet() + ["✏️ Inserir Manualmente"]
        unid_val = str(row["Unidade de Medida"])
        unid_idx = all_units_edit.index(unid_val) if unid_val in all_units_edit else 0

        with st.form("form_editar_material"):
            c1, c2 = st.columns(2)
            with c1:
                e_nome = st.text_input("Material", value=str(row["Material"]))
                e_qtd = st.number_input("Quantidade", min_value=0, step=1, value=int(float(str(row["Quantidade"] or 0))))
                e_unidade_sel = st.selectbox("Unidade", options=all_units_edit, index=unid_idx)
                if e_unidade_sel == "✏️ Inserir Manualmente":
                    e_unidade_manual = st.text_input("Unidade (manual)", placeholder="ex: Kit(s)...")
                else:
                    e_unidade_manual = ""
            with c2:
                e_lote = st.text_input("Lote", value=str(row["Lote"]))
                e_val = st.date_input("Vencimento", value=val_atual, format="DD/MM/YYYY")
                e_obs = st.text_area("Observação", value=str(row.get("Observação", "")), height=100)
                e_user = st.text_input("Usuário que Registrou", value=str(row.get("Usuário que Registrou", "")))
            usuario_auditoria = st.text_input("Usuário responsável pela alteração *")
            justificativa = st.text_area("Justificativa obrigatória *", placeholder="Descreva a razão da alteração.")
            btn_edit = st.form_submit_button("✅ Salvar Alterações", width='stretch')

        if btn_edit:
            if not usuario_auditoria.strip() or not justificativa.strip():
                st.error("Usuário responsável e justificativa são obrigatórios.")
            else:
                e_unidade = e_unidade_manual.strip() if e_unidade_sel == "✏️ Inserir Manualmente" else e_unidade_sel
                dados = {
                    "Material": e_nome.strip(),
                    "Quantidade": int(e_qtd),
                    "Unidade de Medida": e_unidade,
                    "Lote": e_lote.strip(),
                    "Data de Vencimento": e_val.strftime("%d/%m/%Y"),
                    "Observação": e_obs.strip(),
                    "Usuário que Registrou": e_user.strip(),
                    "Data de Inserção": str(row.get("Data de Inserção", "")),
                }
                if atualizar_material(sheet_row, dados):
                    for campo, valor_novo in dados.items():
                        valor_anterior = str(row.get(campo, ""))
                        if valor_anterior != str(valor_novo):
                            auditar_alteracao("Materiais", f"{sel_nome} - Lote {sel_lote}", campo, valor_anterior, valor_novo, justificativa.strip(), usuario_auditoria.strip())
                    get_materiais.clear()
                    st.success("✅ Material atualizado com sucesso!")
                    st.rerun()

with tab_del:
    st.markdown('<div class="section-header">Excluir Material</div>', unsafe_allow_html=True)
    df2 = get_materiais()
    if df2.empty:
        st.info("Nenhum material cadastrado.")
    else:
        nomes = get_materiales_list()
        sel_nome = st.selectbox("Selecione o material", options=nomes, key="sel_del_mat_nome")
        lotes = get_lotes_por_material(sel_nome) if sel_nome else []
        sel_lote = st.selectbox("Selecione o lote", options=lotes, key="sel_del_mat_lote")
        mask = (df2["Material"] == sel_nome) & (df2["Lote"] == sel_lote)
        if not mask.any():
            st.info("Selecione um material e lote válidos para exclusão.")
            st.stop()
        row_del = df2[mask].iloc[0]
        sheet_row_del = int(row_del.get('_sheet_row', 2))
        st.warning(f"⚠️ Tem certeza que deseja excluir **{sel_nome} — Lote: {sel_lote}**?")
        usuario_del = st.text_input("Usuário responsável *", key="del_mat_usuario")
        justificativa_del = st.text_area("Justificativa obrigatória *", key="del_mat_justificativa", placeholder="Descreva a razão da exclusão.")
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("🗑️ Confirmar Exclusão", key="btn_del_mat"):
                if not usuario_del.strip() or not justificativa_del.strip():
                    st.error("Usuário responsável e justificativa são obrigatórios.")
                elif excluir_material(sheet_row_del):
                    auditar_alteracao("Materiais", f"{sel_nome} - Lote {sel_lote}", "Registro", str(row_del.drop(labels=['_sheet_row'], errors='ignore').to_dict()), "Excluído", justificativa_del.strip(), usuario_del.strip())
                    get_materiais.clear()
                    st.success("✅ Material excluído com sucesso!")
                    st.rerun()

with tab_cons:
    st.markdown('<div class="section-header">Consultar Material</div>', unsafe_allow_html=True)
    df3 = get_materiais()
    if df3.empty:
        st.info("Nenhum material cadastrado.")
    else:
        pesq = st.text_input("🔍 Pesquisar", placeholder="Material, lote...", key="pesq_cons_mat")
        df_cons = df3.drop(columns=['_sheet_row'], errors='ignore').copy()
        if pesq:
            mask = df_cons["Material"].astype(str).str.contains(pesq, case=False, na=False)
            mask |= df_cons["Lote"].astype(str).str.contains(pesq, case=False, na=False)
            df_cons = df_cons[mask]
        st.dataframe(df_cons, width='stretch', hide_index=True)
