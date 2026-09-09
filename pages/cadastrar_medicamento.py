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
from utils.helpers import (
    calcular_dias_para_vencer,
    calcular_status,
    formatar_data_hora,
    normalizar_texto,
    render_responsive_table,
)
from utils.constants import UNIDADES_FRACIONADAS


def mostrar_toast_pendente():
    mensagem = st.session_state.pop("toast_mensagem", None)
    if mensagem:
        texto, icone = mensagem
        st.toast(texto, icon=icone)


st.markdown('<h1 class="page-title">➕  Medicamentos</h1>', unsafe_allow_html=True)

mostrar_toast_pendente()

tab_cad, tab_edit, tab_del, tab_cons = st.tabs(["📝 Cadastrar", "✏️ Editar", "🗑️ Excluir", "🔎 Consultar"])

# ── CADASTRAR ──────────────────────────────────────────────────────────────────
with tab_cad:
    st.markdown(
        '<div class="section-header">Novo(s) Medicamento(s)</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "ID: próximo número automático | Usuário: Stephanny | "
        "Inserção/Revisão: data e hora atual"
    )

    if "med_ids" not in st.session_state:
        st.session_state.med_ids = [0]
        st.session_state.med_counter = 0

    unidades = get_unidades_from_sheet()
    unidades += st.session_state.get("custom_units", [])
    unidades = sorted(list(dict.fromkeys(unidades)))
    unidades += [
        "✏️ Inserir Manualmente",
        "➕ Inserir Nova Unidade",
    ]

    for row_id in list(st.session_state.med_ids):
        with st.container(border=True):
            col1, col2 = st.columns(2)

            with col1:
                st.text_input(
                    "Nome do Medicamento *",
                    key=f"m_nome_{row_id}",
                )

                st.number_input(
                    "Quantidade Fechada *",
                    min_value=0,
                    step=1,
                    value=1,
                    key=f"m_qtd_{row_id}",
                    help="Quantidade de unidades fechadas disponíveis.",
                )

                st.selectbox(
                    "Unidade de estoque (fechada) *",
                    options=unidades,
                    key=f"m_unid_{row_id}",
                    help="Exemplo: Ampola(s), Frasco(s) ou Comprimido(s).",
                )

                unidade_selecionada = st.session_state.get(
                    f"m_unid_{row_id}",
                    "",
                )

                if unidade_selecionada == "✏️ Inserir Manualmente":
                    st.text_input(
                        "Digite a unidade",
                        placeholder="Ex.: Sachê(s), Bisnaga(s)",
                        key=f"m_unid_manual_{row_id}",
                    )

                elif unidade_selecionada == "➕ Inserir Nova Unidade":
                    nova_unidade = st.text_input(
                        "Nova Unidade",
                        placeholder="Ex.: Sachê(s)",
                        key=f"m_new_unid_{row_id}",
                    )

                    if st.button(
                        "Adicionar Unidade",
                        key=f"m_add_unid_{row_id}",
                    ):
                        nova_unidade = nova_unidade.strip()

                        if not nova_unidade:
                            st.error("Digite a unidade antes de adicionar.")
                        else:
                            unidades_customizadas = st.session_state.get(
                                "custom_units",
                                [],
                            )

                            if nova_unidade not in unidades_customizadas:
                                unidades_customizadas.append(nova_unidade)
                                st.session_state.custom_units = (
                                    unidades_customizadas
                                )

                            st.success(
                                f"Unidade '{nova_unidade}' adicionada."
                            )
                            st.rerun()

                unidade_fracionada = st.selectbox(
                    "Pode ser usado parcialmente? *",
                    options=["Não", "Sim"],
                    key=f"m_fracionada_{row_id}",
                    help="Escolha Sim para ampolas ou frascos que podem ser abertos e consumidos em partes.",
                )

                if unidade_fracionada == "Sim":
                    unidade_consumo = st.selectbox(
                        "Unidade usada no consumo *",
                        options=UNIDADES_FRACIONADAS,
                        key=f"m_unidade_consumo_{row_id}",
                        help="Exemplo: escolha ml para uma ampola de 25 ml.",
                    )

                    volume_por_unidade = st.number_input(
                        f"Volume total de 1 {unidade_selecionada or 'unidade'} ({unidade_consumo}) *",
                        min_value=0.01,
                        step=0.01,
                        value=1.0,
                        key=f"m_volume_{row_id}",
                        help="Exemplo: uma ampola com 25 ml deve ser cadastrada como 25.",
                    )

                    saldo_aberto = st.number_input(
                        f"Saldo já aberto ({unidade_consumo}) - opcional",
                        min_value=0.0,
                        step=0.01,
                        value=0.0,
                        key=f"m_saldo_{row_id}",
                        help="Preencha somente se já houver uma ampola ou frasco aberto. Se tudo estiver fechado, use 0.",
                    )
                else:
                    unidade_consumo = ""
                    volume_por_unidade = 0.0
                    saldo_aberto = 0.0

            with col2:
                st.text_input(
                    "Lote *",
                    key=f"m_lote_{row_id}",
                )

                st.date_input(
                    "Data de Vencimento *",
                    value=date.today(),
                    format="DD/MM/YYYY",
                    key=f"m_val_{row_id}",
                )

                st.text_area(
                    "Observações",
                    height=100,
                    key=f"m_obs_{row_id}",
                )

            if len(st.session_state.med_ids) > 1:
                if st.button(
                    "🗑️ Remover",
                    key=f"m_rem_{row_id}",
                ):
                    st.session_state.med_ids.remove(row_id)
                    st.rerun()

    col_add_1, col_add_2 = st.columns([8, 2])

    with col_add_2:
        if st.button(
            "➕ Adicionar Medicamento",
            width="stretch",
        ):
            st.session_state.med_counter += 1
            st.session_state.med_ids.append(
                st.session_state.med_counter
            )
            st.rerun()

    if st.button(
        "✅ Cadastrar Medicamento(s)",
        width="stretch",
        type="primary",
    ):
        erros: list[str] = []
        registros: list[dict] = []

        for indice, row_id in enumerate(
            st.session_state.med_ids,
            start=1,
        ):
            nome = st.session_state.get(
                f"m_nome_{row_id}",
                "",
            ).strip()

            quantidade_fechada = st.session_state.get(
                f"m_qtd_{row_id}",
                0,
            )

            unidade_selecionada = st.session_state.get(
                f"m_unid_{row_id}",
                "",
            )

            unidade_manual = st.session_state.get(
                f"m_unid_manual_{row_id}",
                "",
            ).strip()

            unidade = (
                unidade_manual
                if unidade_selecionada == "✏️ Inserir Manualmente"
                else unidade_selecionada
            )

            unidade_fracionada = st.session_state.get(
                f"m_fracionada_{row_id}",
                "Não",
            )

            unidade_consumo = st.session_state.get(
                f"m_unidade_consumo_{row_id}",
                "",
            )

            volume_por_unidade = st.session_state.get(
                f"m_volume_{row_id}",
                0,
            )

            saldo_aberto = st.session_state.get(
                f"m_saldo_{row_id}",
                0,
            )

            lote = st.session_state.get(
                f"m_lote_{row_id}",
                "",
            ).strip()

            validade = st.session_state.get(
                f"m_val_{row_id}",
                date.today(),
            )

            observacoes = st.session_state.get(
                f"m_obs_{row_id}",
                "",
            ).strip()

            if not nome:
                erros.append(
                    f"Medicamento {indice}: nome é obrigatório."
                )

            if not unidade:
                erros.append(
                    f"Medicamento {indice}: unidade de medida é obrigatória."
                )

            if not lote:
                erros.append(
                    f"Medicamento {indice}: lote é obrigatório."
                )

            if (
                unidade_fracionada == "Sim"
                and volume_por_unidade <= 0
            ):
                erros.append(
                    f"Medicamento {indice}: informe um volume válido."
                )

            validade_formatada = (
                validade.strftime("%d/%m/%Y")
                if isinstance(validade, date)
                else str(validade)
            )

            registros.append(
                {
                    "Medicamento": nome,
                    "Usuário que Registrou": "Stephanny",
                    "Data de Inserção": formatar_data_hora(),
                    "Quantidade": int(quantidade_fechada),
                    "Quantidade Fechada": int(quantidade_fechada),
                    "Saldo Aberto": (
                        float(saldo_aberto)
                        if unidade_fracionada == "Sim"
                        else 0
                    ),
                    "Volume por Unidade": (
                        float(volume_por_unidade)
                        if unidade_fracionada == "Sim"
                        else ""
                    ),
                    "Unidade Fracionada": unidade_fracionada,
                    "Unidade de Consumo": (
                        unidade_consumo
                        if unidade_fracionada == "Sim"
                        else ""
                    ),
                    "Fracionamento JSON": "",
                    "Unidade de Medida": unidade,
                    "Lote": lote,
                    "Data de Vencimento": validade_formatada,
                    "Observações": observacoes,
                }
            )

        if erros:
            for erro in erros:
                st.error(erro)

        elif registros:
            sucessos = sum(
                1
                for registro in registros
                if adicionar_medicamento(registro)
            )

            get_estoque.clear()

            if sucessos == len(registros):
                st.session_state.toast_mensagem = (
                    f"{sucessos} medicamento(s) cadastrado(s) com sucesso!",
                    "✅",
                )

                st.session_state.med_ids = [0]
                st.session_state.med_counter = 0

                for chave in list(st.session_state.keys()):
                    if chave.startswith("m_"):
                        del st.session_state[chave]

                st.rerun()
            else:
                st.session_state.toast_mensagem = (
                    f"{len(registros) - sucessos} medicamento(s) "
                    "não puderam ser cadastrados.",
                    "❌",
                )
                st.rerun()

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
                e_qtd = st.number_input("Quantidade fechada", min_value=0, step=1, value=int(float(str(row["Quantidade"] or 0))))
                e_unidade_sel = st.selectbox("Unidade", options=all_units_edit, index=unid_idx)
                if e_unidade_sel == "✏️ Inserir Manualmente":
                    e_unidade_manual = st.text_input("Unidade (manual)", placeholder="ex: Sachê(s)...")
                else:
                    e_unidade_manual = ""
                e_fracionada = st.selectbox(
                    "Pode ser usado parcialmente?",
                    options=["Não", "Sim"],
                    index=1 if str(row.get("Unidade Fracionada", "Não")).strip().lower() == "sim" else 0,
                )
                if e_fracionada == "Sim":
                    e_unidade_consumo = st.selectbox(
                        "Unidade usada no consumo",
                        options=UNIDADES_FRACIONADAS,
                        index=(UNIDADES_FRACIONADAS.index(str(row.get("Unidade de Consumo", "")))
                               if str(row.get("Unidade de Consumo", "")) in UNIDADES_FRACIONADAS else 0),
                    )
                    e_volume = st.number_input(
                        "Volume total de uma unidade fechada",
                        min_value=0.01,
                        step=0.01,
                        value=float(row.get("Volume por Unidade", 0) or 0) or 1.0,
                    )
                    e_saldo = st.number_input(
                        "Saldo já aberto",
                        min_value=0.0,
                        step=0.01,
                        value=float(row.get("Saldo Aberto", 0) or 0),
                    )
                else:
                    e_unidade_consumo, e_volume, e_saldo = "", 0.0, 0.0
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
                    "Quantidade Fechada": int(e_qtd),
                    "Unidade de Medida": e_unidade,
                    "Unidade Fracionada": e_fracionada,
                    "Unidade de Consumo": e_unidade_consumo,
                    "Volume por Unidade": e_volume if e_fracionada == "Sim" else "",
                    "Saldo Aberto": e_saldo if e_fracionada == "Sim" else 0,
                    "Lote": e_lote.strip(),
                    "Data de Vencimento": e_val.strftime("%d/%m/%Y"),
                    "Observações": e_obs.strip(),
                }
                if atualizar_medicamento(sheet_row, dados):
                    for campo, valor_novo in dados.items():
                        valor_anterior = str(row.get(campo, ""))
                        if valor_anterior != str(valor_novo):
                            auditar_alteracao(
                                "Medicamentos",
                                f"{selecionado_nome} - Lote {selecionado_lote}",
                                campo,
                                valor_anterior,
                                valor_novo,
                                justificativa.strip(),
                                usuario.strip(),
                            )

                    get_estoque.clear()
                    st.session_state["toast_mensagem"] = (
                        "Medicamento atualizado com sucesso!",
                        "✅",
                    )
                    st.rerun()
                else:
                    st.session_state["toast_mensagem"] = (
                        "Não foi possível atualizar o medicamento.",
                        "❌",
                    )
                    st.rerun()

# ── EXCLUIR ────────────────────────────────────────────────────────────────────
with tab_del:
    st.markdown(
        '<div class="section-header">Excluir Medicamentos</div>',
        unsafe_allow_html=True,
    )

    df2 = get_estoque()

    if df2.empty:
        st.info("Nenhum medicamento cadastrado.")
    else:
        busca_exclusao = st.text_input(
            "🔍 Buscar medicamento para a Exclusão:",
            placeholder="Digite o nome do medicamento...",
            key="busca_exclusao_medicamento",
        )

        termo = normalizar_texto(busca_exclusao)

        filtro = df2["Medicamento"].map(normalizar_texto).str.contains(
            termo,
            regex=False,
            na=False,
        )
        df2 = df2[filtro].copy()

        if df2.empty:
            st.info("Nenhum medicamento encontrado.")
            st.stop()

        tabela_exclusao = df2.drop(
            columns=["_sheet_row"],
            errors="ignore",
        ).copy()

        tabela_exclusao.insert(0, "Selecionar", False)

        tabela_editada = st.data_editor(
            tabela_exclusao,
            hide_index=True,
            width="stretch",
            disabled=[
                coluna for coluna in tabela_exclusao.columns
                if coluna != "Selecionar"
            ],
            column_config={
                "Selecionar": st.column_config.CheckboxColumn(
                    "Excluir",
                    help="Marque os medicamentos que deseja excluir",
                    default=False,
                ),
            },
            key="tabela_selecao_medicamentos",
        )

        selecionados = tabela_editada[tabela_editada["Selecionar"]]

        st.write(f"{len(selecionados)} medicamento(s) selecionado(s).")

        usuario_del = st.text_input(
            "Usuário responsável *",
            value="Stephanny",
            key="del_med_usuario",
        )

        justificativa_del = st.text_area(
            "Justificativa obrigatória *",
            placeholder="Descreva a razão da exclusão.",
            key="del_med_justificativa",
        )

        if st.button(
            "🗑️ Excluir selecionados",
            type="primary",
            key="btn_del_selecionados",
        ):
            if selecionados.empty:
                st.error("Selecione pelo menos um medicamento na tabela.")
            elif not usuario_del.strip():
                st.error("Informe o usuário responsável.")
            elif not justificativa_del.strip():
                st.error("A justificativa é obrigatória.")
            else:
                excluidos = 0
                falhas = 0

                linhas_para_excluir = []

                for indice in selecionados.index:
                    linha_original = df2.loc[indice]
                    linhas_para_excluir.append(linha_original)

                # Exclui de baixo para cima para preservar os números das linhas
                linhas_para_excluir.sort(
                    key=lambda linha: int(linha["_sheet_row"]),
                    reverse=True,
                )

                for linha in linhas_para_excluir:
                    sheet_row = int(linha["_sheet_row"])
                    nome = str(linha.get("Medicamento", ""))
                    lote = str(linha.get("Lote", ""))

                    if excluir_medicamento(sheet_row):
                        auditar_alteracao(
                            "Medicamentos",
                            f"{nome} - Lote {lote}",
                            "Registro",
                            str(
                                linha.drop(
                                    labels=["_sheet_row"],
                                    errors="ignore",
                                ).to_dict()
                            ),
                            "Excluído",
                            justificativa_del.strip(),
                            usuario_del.strip(),
                        )
                        excluidos += 1
                    else:
                        falhas += 1

                get_estoque.clear()

                if falhas == 0:
                    st.session_state["toast_mensagem"] = (
                        f"{excluidos} medicamento(s) excluído(s) com sucesso!",
                        "✅",
                    )
                else:
                    st.session_state["toast_mensagem"] = (
                        f"{excluidos} excluído(s) e {falhas} não puderam ser excluído(s).",
                        "⚠️",
                    )

                st.rerun()

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
        pesq = st.text_input(
            "🔍 Termo de pesquisa",
            placeholder="Ex.: Lidocaína, 000513, AMP...",
            key="pesq_cons",
        )

        filtro1, filtro2 = st.columns(2)

        with filtro1:
            qtd_min = st.number_input(
                "Quantidade mínima",
                min_value=0,
                value=0,
                step=1,
                key="qtd_min_cons",
            )

        with filtro2:
            qtd_max = st.number_input(
                "Quantidade máxima",
                min_value=0,
                value=0,
                step=1,
                key="qtd_max_cons",
                help="Use 0 para não limitar.",
            )

        if pesq.strip() and campos_pesquisa:
            termo = normalizar_texto(pesq)
            mask = pd.Series(False, index=df_cons.index)

            for campo in campos_pesquisa:
                mask |= df_cons[campo].map(
                    normalizar_texto
                ).str.contains(
                    termo,
                    regex=False,
                    na=False,
                )

            df_cons = df_cons[mask]

        if "Quantidade" in df_cons.columns:
            quantidades = pd.to_numeric(
                df_cons["Quantidade"]
                .astype(str)
                .str.replace(",", ".", regex=False),
                errors="coerce",
            ).fillna(0)

            df_cons = df_cons[quantidades >= qtd_min]

            if qtd_max > 0:
                df_cons = df_cons[quantidades <= qtd_max]

        st.caption(f"{len(df_cons)} registro(s) encontrado(s)")
        render_responsive_table(df_cons)
