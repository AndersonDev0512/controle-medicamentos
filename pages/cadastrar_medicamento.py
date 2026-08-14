import streamlit as st
import pandas as pd
from datetime import date, datetime
from services.estoque_service import (
    get_estoque,
    get_unidades_from_sheet,
    get_medicamentos_list,
    get_lotes_por_medicamento,
)
from services.sheets_service import (
    adicionar_medicamento,
    atualizar_medicamento,
    auditar_alteracao,
    excluir_medicamento,
)
from utils.helpers import calcular_dias_para_vencer, calcular_status

st.markdown('<h1 class="page-title">➕ Cadastrar Medicamento</h1>', unsafe_allow_html=True)

tab_cad, tab_edit, tab_del, tab_cons = st.tabs(["📝 Cadastrar", "✏️ Editar", "🗑️ Excluir", "🔎 Consultar"])

# ── CADASTRAR ──────────────────────────────────────────────────────────────────
with tab_cad:
    st.markdown('<div class="section-header">Novo(s) Medicamento(s)</div>', unsafe_allow_html=True)
    st.caption("ID: próximo número automático | Usuário: Stephanny | Inserção/Revisão: data e hora atual")

    if 'med_ids' not in st.session_state:
        st.session_state.med_ids = [0]
        st.session_state.med_counter = 0

    # combine sheet units with session-added custom units
    session_custom_units = st.session_state.get('custom_units', [])
    all_units = get_unidades_from_sheet()
    all_units = sorted(list(dict.fromkeys(all_units + session_custom_units)))
    all_units += ["✏️ Inserir Manualmente", "➕ Inserir Nova Unidade"]

    for row_id in list(st.session_state.med_ids):
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Nome do Medicamento *", key=f"m_nome_{row_id}")
                st.number_input("Quantidade *", min_value=1, step=1, value=st.session_state.get(f"m_qtd_{row_id}", 1), key=f"m_qtd_{row_id}")
                st.selectbox("Unidade de Medida *", options=all_units, key=f"m_unid_{row_id}")
                sel = st.session_state.get(f"m_unid_{row_id}")
                if sel == "✏️ Inserir Manualmente":
                    st.text_input("Digite a unidade", placeholder="ex: Sachê(s), Bisnaga(s)...",
                                  key=f"m_unid_manual_{row_id}", label_visibility="collapsed")
                elif sel == "➕ Inserir Nova Unidade":
                    new_u = st.text_input("Nova Unidade", placeholder="ex: Sachê(s)", key=f"m_new_unid_{row_id}")
                    if st.button("Adicionar Unidade", key=f"m_add_unid_{row_id}"):
                        nu = (new_u or '').strip()
                        if nu:
                            lst = st.session_state.get('custom_units', [])
                            if nu not in lst:
                                lst.append(nu)
                                st.session_state['custom_units'] = lst
                                st.success(f"Unidade '{nu}' adicionada (sessão).")
                                st.experimental_rerun()
                        else:
                            st.error('Digite a unidade antes de adicionar.')
            with c2:
                st.text_input("Lote *", key=f"m_lote_{row_id}")
                st.date_input("Data de Vencimento *", value=date.today(), format="DD/MM/YYYY", key=f"m_val_{row_id}")
                st.text_area("Observações", height=68, key=f"m_obs_{row_id}")
            if len(st.session_state.med_ids) > 1:
                if st.button("🗑️ Remover", key=f"m_rem_{row_id}"):
                    st.session_state.med_ids.remove(row_id)
                    st.rerun()

    # place the add button to the right
    _, col_add = st.columns([8, 2])
    with col_add:
        if st.button("➕ Adicionar Medicamento", width='stretch'):
            st.session_state.med_counter += 1
            st.session_state.med_ids.append(st.session_state.med_counter)
            st.rerun()

    if st.button("✅ Cadastrar Medicamento(s)", width='stretch', type="primary"):
        erros: list[str] = []
        registros: list[dict] = []
        for i, row_id in enumerate(st.session_state.med_ids):
            nome = st.session_state.get(f"m_nome_{row_id}", "").strip()
            qtd = st.session_state.get(f"m_qtd_{row_id}", 1)
            unid_sel = st.session_state.get(f"m_unid_{row_id}", "")
            unid_manual = st.session_state.get(f"m_unid_manual_{row_id}", "").strip()
            unidade = unid_manual if unid_sel == "✏️ Inserir Manualmente" else unid_sel
            lote = st.session_state.get(f"m_lote_{row_id}", "").strip()
            validade = st.session_state.get(f"m_val_{row_id}", date.today())
            obs = st.session_state.get(f"m_obs_{row_id}", "").strip()

            if not nome:
                erros.append(f"Medicamento {i+1}: Nome é obrigatório.")
            if not lote:
                erros.append(f"Medicamento {i+1}: Lote é obrigatório.")
            if not unidade:
                erros.append(f"Medicamento {i+1}: Unidade de medida é obrigatória.")
            if not erros or (nome and lote and unidade):
                val_str = validade.strftime("%d/%m/%Y") if isinstance(validade, date) else str(validade)
                registros.append({
                    "Medicamento": nome,
                    "Usuário que Registrou": "Stephanny",
                    "Data de Inserção": "=NOW()",
                    "Quantidade": int(qtd),
                    "Unidade de Medida": unidade,
                    "Lote": lote,
                    "Data de Vencimento": val_str,
                    "Observações": obs,
                })

        if erros:
            for e in erros:
                st.error(e)
        elif registros:
            sucesso = sum(1 for d in registros if adicionar_medicamento(d))
            get_estoque.clear()
            if sucesso == len(registros):
                st.success(f"✅ {sucesso} medicamento(s) cadastrado(s) com sucesso!")
                st.session_state.med_ids = [0]
                st.session_state.med_counter = 0
                for k in [k for k in list(st.session_state.keys()) if k.startswith("m_")]:
                    del st.session_state[k]
                st.rerun()
            else:
                st.error(f"{len(registros) - sucesso} medicamento(s) não puderam ser cadastrados.")

# ── EDITAR ─────────────────────────────────────────────────────────────────────
with tab_edit:
    st.markdown('<div class="section-header">Editar Medicamento</div>', unsafe_allow_html=True)
    df = get_estoque()

    if df.empty:
        st.info("Nenhum medicamento cadastrado.")
    else:
        nomes = get_medicamentos_list()
        selecionado_nome = st.selectbox("Selecione o nome do medicamento", options=nomes, key="sel_edit_nome")
        lotes = get_lotes_por_medicamento(selecionado_nome) if selecionado_nome else []
        selecionado_lote = st.selectbox("Selecione o lote", options=lotes, key="sel_edit_lote")

        # find matching row
        mask = (df["Medicamento"] == selecionado_nome) & (df["Lote"] == selecionado_lote)
        if not mask.any():
            st.info("Selecione um medicamento e lote válidos.")
            st.stop()
        row = df[mask].iloc[0]
        sheet_row = int(row['_sheet_row'])

        try:
            val_atual = datetime.strptime(str(row["Data de Vencimento"]), "%d/%m/%Y").date()
        except Exception:
            val_atual = date.today()

        all_units_edit = get_unidades_from_sheet() + ["✏️ Inserir Manualmente"]
        unid_val = str(row["Unidade de Medida"])
        unid_idx = all_units_edit.index(unid_val) if unid_val in all_units_edit else 0

        with st.form("form_editar"):
            c1, c2 = st.columns(2)
            with c1:
                e_nome = st.text_input("Nome", value=str(row["Medicamento"]))
                e_qtd = st.number_input("Quantidade", min_value=0, step=1, value=int(float(str(row["Quantidade"] or 0))))
                e_unidade_sel = st.selectbox("Unidade", options=all_units_edit, index=unid_idx)
                if e_unidade_sel == "✏️ Inserir Manualmente":
                    e_unidade_manual = st.text_input("Unidade (manual)", placeholder="ex: Sachê(s)...")
                else:
                    e_unidade_manual = ""
            with c2:
                e_lote = st.text_input("Lote", value=str(row["Lote"]))
                e_val = st.date_input("Validade", value=val_atual, format="DD/MM/YYYY")
                e_obs = st.text_area("Observações", value=str(row.get("Observações", "")), height=100)
            usuario = st.text_input("Usuário responsável *")
            justificativa = st.text_area("Justificativa obrigatória *", placeholder="Descreva a razão da alteração.")
            btn_edit = st.form_submit_button("✅ Salvar Alterações", width='stretch')

        if btn_edit:
            if not usuario.strip() or not justificativa.strip():
                st.error("Usuário responsável e justificativa são obrigatórios.")
            else:
                e_unidade = e_unidade_manual.strip() if e_unidade_sel == "✏️ Inserir Manualmente" else e_unidade_sel
                dados = {
                    "Medicamento": e_nome.strip(),
                    "Quantidade": int(e_qtd),
                    "Unidade de Medida": e_unidade,
                    "Lote": e_lote.strip(),
                    "Data de Vencimento": e_val.strftime("%d/%m/%Y"),
                    "Observações": e_obs.strip(),
                }
                if atualizar_medicamento(sheet_row, dados):
                    for campo, valor_novo in dados.items():
                        valor_anterior = str(row.get(campo, ""))
                        if valor_anterior != str(valor_novo):
                            auditar_alteracao("Medicamentos", f"{selecionado_nome} - Lote {selecionado_lote}", campo, valor_anterior, valor_novo, justificativa.strip(), usuario.strip())
                    get_estoque.clear()
                    st.success("✅ Medicamento atualizado com sucesso!")
                    st.rerun()

# ── EXCLUIR ────────────────────────────────────────────────────────────────────
with tab_del:
    st.markdown('<div class="section-header">Excluir Medicamento</div>', unsafe_allow_html=True)
    df2 = get_estoque()

    if df2.empty:
        st.info("Nenhum medicamento cadastrado.")
    else:
        nomes = get_medicamentos_list()
        sel_nome = st.selectbox("Selecione o nome do medicamento", options=nomes, key="sel_del_nome")
        lotes = get_lotes_por_medicamento(sel_nome) if sel_nome else []
        sel_lote = st.selectbox("Selecione o lote", options=lotes, key="sel_del_lote")

        mask = (df2["Medicamento"] == sel_nome) & (df2["Lote"] == sel_lote)
        if not mask.any():
            st.info("Selecione um medicamento e lote válidos para exclusão.")
            st.stop()

        row_del = df2[mask].iloc[0]
        sheet_row_del = int(row_del['_sheet_row'])

        st.warning(f"⚠️ Tem certeza que deseja excluir **{sel_nome} — Lote: {sel_lote}**? Esta ação não pode ser desfeita.")
        st.markdown("**Registro selecionado para exclusão**")
        st.dataframe(row_del.drop(labels=['_sheet_row'], errors='ignore').to_frame().T, width='stretch', hide_index=True)
        usuario_del = st.text_input("Usuário responsável *", key="del_med_usuario")
        justificativa_del = st.text_area("Justificativa obrigatória *", key="del_med_justificativa", placeholder="Descreva a razão da exclusão.")

        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("🗑️ Confirmar Exclusão", key="btn_del"):
                if not usuario_del.strip() or not justificativa_del.strip():
                    st.error("Usuário responsável e justificativa são obrigatórios.")
                elif excluir_medicamento(sheet_row_del):
                    auditar_alteracao("Medicamentos", f"{sel_nome} - Lote {sel_lote}", "Registro", str(row_del.drop(labels=['_sheet_row'], errors='ignore').to_dict()), "Excluído", justificativa_del.strip(), usuario_del.strip())
                    get_estoque.clear()
                    st.session_state["ultimo_medicamento_excluido"] = f"{sel_nome} - Lote {sel_lote}"
                    st.success("✅ Medicamento excluído com sucesso!")
                    st.rerun()

        if st.session_state.get("ultimo_medicamento_excluido"):
            st.success(f"Tabela atualizada após a exclusão de {st.session_state['ultimo_medicamento_excluido']}.")
            tabela_atual = get_estoque().drop(columns=['_sheet_row'], errors='ignore')
            st.dataframe(tabela_atual, width='stretch', hide_index=True)
            del st.session_state["ultimo_medicamento_excluido"]

# ── CONSULTAR ──────────────────────────────────────────────────────────────────
with tab_cons:
    st.markdown('<div class="section-header">Consultar Medicamento</div>', unsafe_allow_html=True)
    df3 = get_estoque()

    if df3.empty:
        st.info("Nenhum medicamento cadastrado.")
    else:
        st.caption("Alterações ficam disponíveis na aba Editar e são registradas automaticamente na auditoria.")
        df_cons = df3.drop(columns=['_sheet_row'], errors='ignore').copy()
        campos_disponiveis = [
            campo for campo in ["ID", "Medicamento", "Lote", "Quantidade", "Unidade de Medida", "Data de Vencimento", "Status", "Usuário que Registrou"]
            if campo in df_cons.columns
        ]
        campos_pesquisa = st.multiselect(
            "Campos para pesquisar",
            options=campos_disponiveis,
            default=[campo for campo in ["Medicamento", "Lote"] if campo in campos_disponiveis],
            key="campos_cons",
        )
        pesq = st.text_input("🔍 Termo de pesquisa", placeholder="Ex.: Lidocaína, 000513, AMP...", key="pesq_cons")
        filtro1, filtro2 = st.columns(2)
        with filtro1:
            qtd_min = st.number_input("Quantidade mínima", min_value=0, value=0, step=1, key="qtd_min_cons")
        with filtro2:
            qtd_max = st.number_input("Quantidade máxima", min_value=0, value=0, step=1, key="qtd_max_cons", help="Use 0 para não limitar.")
        if pesq and campos_pesquisa:
            mask = pd.Series(False, index=df_cons.index)
            for campo in campos_pesquisa:
                mask |= df_cons[campo].astype(str).str.contains(pesq, case=False, na=False)
            df_cons = df_cons[mask]
        if "Quantidade" in df_cons.columns:
            quantidades = pd.to_numeric(df_cons["Quantidade"].astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0)
            df_cons = df_cons[quantidades >= qtd_min]
            if qtd_max > 0:
                df_cons = df_cons[quantidades <= qtd_max]
        st.caption(f"{len(df_cons)} registro(s) encontrado(s)")
        st.dataframe(df_cons, width='stretch', hide_index=True)
