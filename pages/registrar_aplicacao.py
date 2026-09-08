import json
import html
import pandas as pd
import streamlit as st

from services.aplicacao_service import (
    registrar_aplicacao,
    registrar_aplicacao_multiplos,
)
from services.estoque_service import (
    get_estoque,
    get_materiais,
    get_materiales_list,
    get_quantidade_disponivel,
    get_quantidade_disponivel_material,
)
from services.sheets_service import ler_registro_diario
from utils.helpers import formatar_data_hora


st.markdown(
    """
    <style>
    .grupo-medicamentos {
        border-left: 5px solid #3b82f6;
        padding-left: 14px;
        margin: 25px 0 15px;
    }

    .grupo-materiais {
        border-left: 5px solid #e11d48;
        padding-left: 14px;
        margin: 35px 0 15px;
    }

    .titulo-medicamentos {
        color: #93c5fd !important;
    }

    .titulo-materiais {
        color: #fda4af !important;
    }

    .resumo-estoque {
        color: #94a3b8 !important;
        font-size: 0.85rem;
        margin-top: -8px;
        margin-bottom: 12px;
    }

    .tabela-aplicacoes-wrapper {
        width: 100%;
        overflow-x: auto;
        border: 1px solid #334155;
        border-radius: 10px;
        background: #ffffff;
    }

    .tabela-aplicacoes {
        width: max-content;
        min-width: 100%;
        border-collapse: collapse;
        table-layout: auto;
        color: #111827;
        font-size: 0.86rem;
    }

    .tabela-aplicacoes th,
    .tabela-aplicacoes td {
        padding: 10px 12px;
        border-right: 1px solid #dbe3ef;
        border-bottom: 1px solid #dbe3ef;
        text-align: left;
        vertical-align: top;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
        line-height: 1.35;
    }

    .tabela-aplicacoes th {
        position: sticky;
        top: 0;
        z-index: 1;
        background: #2563eb;
        color: #ffffff;
        font-weight: 700;
    }

    .tabela-aplicacoes tbody tr:nth-child(even) {
        background: #f1f5f9;
    }

    .tabela-aplicacoes tbody tr:hover {
        background: #dbeafe;
    }

    .tabela-aplicacoes th:first-child,
    .tabela-aplicacoes td:first-child {
        font-weight: 700;
        white-space: nowrap;
    }

    .tabela-vazia {
        padding: 1rem;
        color: #94a3b8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 class="page-title">💉 Registrar Aplicação</h1>',
    unsafe_allow_html=True,
)

estoque_medicamentos = get_estoque()
medicamentos = sorted(
    estoque_medicamentos["Medicamento"].dropna().astype(str).str.strip().unique().tolist()
) if not estoque_medicamentos.empty else []
df_materiais = get_materiais()
materiais = sorted(
    df_materiais["Material"].dropna().astype(str).str.strip().unique().tolist()
) if not df_materiais.empty else get_materiales_list()

if not medicamentos:
    st.warning("Nenhum medicamento em estoque.")
    st.stop()


def novo_medicamento():
    medicamento = medicamentos[0]
    lotes = sorted(
        estoque_medicamentos.loc[
            estoque_medicamentos["Medicamento"] == medicamento, "Lote"
        ].dropna().astype(str).str.strip().unique().tolist()
    )

    return {
        "medicamento": medicamento,
        "lote": lotes[0] if lotes else "—",
        "quantidade": 1,
    }


def novo_material():
    material = materiais[0]
    lotes = sorted(
        df_materiais.loc[
            df_materiais["Material"] == material, "Lote"
        ].dropna().astype(str).str.strip().unique().tolist()
    )

    return {
        "material": material,
        "lote": lotes[0] if lotes else "—",
        "quantidade": 1,
    }


if "medicamentos_aplicacao" not in st.session_state:
    st.session_state.medicamentos_aplicacao = [novo_medicamento()]

if "materiais_aplicacao" not in st.session_state:
    st.session_state.materiais_aplicacao = []


def remover_medicamento(index):
    if len(st.session_state.medicamentos_aplicacao) > 1:
        st.session_state.medicamentos_aplicacao.pop(index)
        st.rerun()


def remover_material(index):
    st.session_state.materiais_aplicacao.pop(index)
    st.rerun()


def obter_unidade_consumo(linha: pd.Series, fracionado: bool) -> str:
    unidade = str(linha.get("Unidade de Consumo", "")).strip()
    if unidade:
        return unidade

    try:
        fracionamento = json.loads(str(linha.get("Fracionamento JSON", "")))
        if isinstance(fracionamento, dict):
            for chave in ("Unidade de Consumo", "unidade_consumo", "unidade"):
                valor = str(fracionamento.get(chave, "")).strip()
                if valor:
                    return valor
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    return "ml" if fracionado else ""


def resumo_estoque_fracionado(linha: pd.Series, disponivel: float) -> str:
    quantidade_fechada = float(str(linha.get("Quantidade Fechada", "") or 0).replace(",", "."))
    if quantidade_fechada == 0 and str(linha.get("Quantidade Fechada", "")).strip() == "":
        quantidade_fechada = float(str(linha.get("Quantidade", 0) or 0).replace(",", "."))
    saldo_aberto = float(str(linha.get("Saldo Aberto", 0) or 0).replace(",", "."))
    unidade_estoque = str(linha.get("Unidade de Medida", "unidade(s)")).strip() or "unidade(s)"
    unidade_consumo = obter_unidade_consumo(linha, True)
    return (
        f"Disponível: {quantidade_fechada:g} {unidade_estoque} fechada(s)"
        f" + {saldo_aberto:g} {unidade_consumo} aberta"
        f" ({disponivel:g} {unidade_consumo} no total)"
    )


def resumir_json_registro(
    linha: pd.Series,
    coluna_direta: str,
    coluna_json: str,
    unidade_padrao: str = "unidade(s)",
) -> str:
    bruto = str(linha.get(coluna_json, "")).strip()
    if not bruto:
        return str(linha.get(coluna_direta, "")).strip()

    try:
        valores = json.loads(bruto)
    except (TypeError, ValueError, json.JSONDecodeError):
        return bruto

    if isinstance(valores, dict):
        valores = valores.get("itens", valores.get("items", [valores]))
    if not isinstance(valores, list):
        return str(valores)

    nomes = []
    for valor in valores:
        if isinstance(valor, dict):
            nome = valor.get(coluna_direta) or valor.get("nome") or valor.get("medicamento") or valor.get("material")
            quantidade = valor.get("quantidade") or valor.get("Quantidade")
            unidade = str(valor.get("unidade") or unidade_padrao).strip()
            detalhes = f"{quantidade:g} {unidade}" if isinstance(quantidade, (int, float)) else f"{quantidade} {unidade}"
            lote = f" | lote {valor.get('lote')}" if valor.get("lote") else ""
            nomes.append(f"{nome} - {detalhes}{lote}" if nome and quantidade != "" else str(nome or valor))
        else:
            nomes.append(str(valor))
    return "<br>".join(nomes)


def renderizar_tabela_aplicacoes(dados: pd.DataFrame) -> str:
    """Renderiza todas as aplicações com largura baseada no conteúdo."""
    if dados.empty:
        return '<div class="tabela-vazia">Nenhuma aplicação registrada ainda.</div>'

    colunas = list(dados.columns)
    larguras = {}
    for coluna in colunas:
        maior_linha = max(
            [len(str(coluna))]
            + [
                max(
                    (
                        len(parte)
                        for parte in str(valor).replace("<br>", "\n").split("\n")
                    ),
                    default=0,
                )
                for valor in dados[coluna].fillna("")
            ]
        )
        larguras[coluna] = min(max(maior_linha + 2, 8), 42)

    cabecalho = "".join(
        f'<th style="width:{larguras[coluna]}ch">{html.escape(str(coluna))}</th>'
        for coluna in colunas
    )
    linhas = []
    for _, linha in dados.iterrows():
        celulas = []
        for coluna in colunas:
            valor = html.escape(
                str(linha.get(coluna, "")).replace("<br>", "\n")
            ).replace("\n", "<br>")
            celulas.append(f"<td>{valor}</td>")
        linhas.append(f"<tr>{''.join(celulas)}</tr>")

    return (
        '<div class="tabela-aplicacoes-wrapper">'
        '<table class="tabela-aplicacoes">'
        f"<thead><tr>{cabecalho}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody>"
        "</table></div>"
    )


st.markdown(
    '<div class="section-header">Dados da aplicação</div>',
    unsafe_allow_html=True,
)

coluna1, coluna2 = st.columns(2)

with coluna1:
    aplicador = st.text_input(
        "Aplicador *",
        value="Stephanny",
        key="aplicador",
    )

with coluna2:
    st.text_input(
        "Data/Hora",
        value=formatar_data_hora(),
        disabled=True,
        key="data_hora",
    )

paciente = st.text_input(
    "Paciente *",
    key="paciente",
)

observacao = st.text_area(
    "Observação",
    placeholder="Digite uma observação opcional.",
    key="observacao",
)


st.markdown(
    '<div class="grupo-medicamentos">'
    '<h2 class="titulo-medicamentos">Medicamentos</h2>'
    "</div>",
    unsafe_allow_html=True,
)

for index, item in enumerate(st.session_state.medicamentos_aplicacao):
    st.markdown(f"### Medicamento {index + 1}")

    chave_medicamento = f"medicamento_{index}"
    chave_lote = f"lote_medicamento_{index}"
    chave_quantidade = f"quantidade_medicamento_{index}"

    medicamento_atual = item["medicamento"]

    col_med, col_lote, col_qtd, col_remover = st.columns(
        [3, 2, 1.3, 0.7]
    )

    with col_med:
        medicamento = st.selectbox(
            "Medicamento *",
            options=medicamentos,
            index=(
                medicamentos.index(medicamento_atual)
                if medicamento_atual in medicamentos
                else 0
            ),
            key=chave_medicamento,
        )

    lotes = sorted(
        estoque_medicamentos.loc[
            estoque_medicamentos["Medicamento"] == medicamento, "Lote"
        ].dropna().astype(str).str.strip().unique().tolist()
    )

    if st.session_state.get(chave_lote) not in lotes:
        st.session_state[chave_lote] = lotes[0] if lotes else "—"

    with col_lote:
        lote = st.selectbox(
            "Lote *",
            options=lotes if lotes else ["—"],
            key=chave_lote,
        )

    disponivel = (
        get_quantidade_disponivel(medicamento, lote)
        if lote != "—"
        else 0
    )

    linha_medicamento = estoque_medicamentos[
        (estoque_medicamentos["Medicamento"] == medicamento)
        & (estoque_medicamentos["Lote"] == lote)
    ]
    unidade_consumo = ""
    fracionado = False
    if not linha_medicamento.empty:
        dados_medicamento = linha_medicamento.iloc[0]
        fracionado = (
            str(dados_medicamento.get("Unidade Fracionada", "Não"))
            .strip()
            .lower()
            == "sim"
        )
        unidade_consumo = obter_unidade_consumo(dados_medicamento, fracionado)

    with col_qtd:
        quantidade = st.number_input(
            (
                f"Consumo ({unidade_consumo}) *"
                if fracionado and unidade_consumo
                else "Quantidade *"
            ),
            min_value=0.01,
            max_value=max(float(disponivel), 0.01),
            value=min(
                float(item.get("quantidade", 1)),
                max(float(disponivel), 0.01),
            ),
            step=0.01,
            key=chave_quantidade,
        )

    with col_remover:
        st.write("")
        st.write("")
        st.button(
            "🗑️",
            key=f"remover_medicamento_{index}",
            on_click=remover_medicamento,
            args=(index,),
        )

    resumo = (
        resumo_estoque_fracionado(dados_medicamento, disponivel)
        if fracionado and not linha_medicamento.empty
        else f"Disponível: {disponivel:g} unidade(s)"
    )
    st.markdown(f'<div class="resumo-estoque">{resumo}</div>', unsafe_allow_html=True)


st.button(
    "➕ Adicionar medicamento",
    width="stretch",
    on_click=lambda: (
        st.session_state.medicamentos_aplicacao.append(
            novo_medicamento()
        )
    ),
)


st.markdown(
    '<div class="grupo-materiais">'
    '<h2 class="titulo-materiais">Materiais</h2>'
    "</div>",
    unsafe_allow_html=True,
)

if not materiais:
    st.info("Nenhum material cadastrado.")
else:
    for index, item in enumerate(st.session_state.materiais_aplicacao):
        st.markdown(f"### Material {index + 1}")

        chave_material = f"material_{index}"
        chave_lote = f"lote_material_{index}"
        chave_quantidade = f"quantidade_material_{index}"

        col_mat, col_lote, col_qtd, col_remover = st.columns(
            [3, 2, 1.3, 0.7]
        )

        with col_mat:
            material = st.selectbox(
                "Material *",
                options=materiais,
                index=(
                    materiais.index(item["material"])
                    if item["material"] in materiais
                    else 0
                ),
                key=chave_material,
            )

            lotes_material = sorted(
                df_materiais.loc[
                    df_materiais["Material"] == material, "Lote"
                ].dropna().astype(str).str.strip().unique().tolist()
            )

        if st.session_state.get(chave_lote) not in lotes_material:
            st.session_state[chave_lote] = (
                lotes_material[0] if lotes_material else "—"
            )

        with col_lote:
            lote_material = st.selectbox(
                "Lote *",
                options=lotes_material if lotes_material else ["—"],
                key=chave_lote,
            )

        disponivel_material = (
            get_quantidade_disponivel_material(
                material,
                lote_material,
            )
            if lote_material != "—"
            else 0
        )

        with col_qtd:
            quantidade_material = st.number_input(
                "Quantidade *",
                min_value=1,
                max_value=max(int(disponivel_material), 1),
                value=min(
                    int(item.get("quantidade", 1)),
                    max(int(disponivel_material), 1),
                ),
                step=1,
                key=chave_quantidade,
            )

        with col_remover:
            st.write("")
            st.write("")
            st.button(
                "🗑️",
                key=f"remover_material_{index}",
                on_click=remover_material,
                args=(index,),
            )

        st.markdown(
            f'<div class="resumo-estoque">'
            f"Disponível: {disponivel_material} unidade(s)"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.button(
        "➕ Adicionar material",
        width="stretch",
        on_click=lambda: (
            st.session_state.materiais_aplicacao.append(
                novo_material()
            )
        ),
    )


st.divider()

registrar = st.button(
    "✅ Registrar aplicação",
    type="primary",
    width="stretch",
)


if registrar:
    erros: list[str] = []
    registros_medicamentos: list[dict] = []
    registros_materiais: list[dict] = []

    if not aplicador.strip():
        erros.append("Informe o aplicador.")

    if not paciente.strip():
        erros.append("Informe o paciente.")

    for index in range(len(st.session_state.medicamentos_aplicacao)):
        medicamento = st.session_state.get(
            f"medicamento_{index}",
            "",
        )

        lote = st.session_state.get(
            f"lote_medicamento_{index}",
            "",
        )

        quantidade = float(
            st.session_state.get(
                f"quantidade_medicamento_{index}",
                0,
            )
        )

        if lote == "—":
            erros.append(
                f"Medicamento {index + 1}: selecione um lote."
            )
            continue

        if quantidade <= 0:
            erros.append(
                f"Medicamento {index + 1}: "
                "a quantidade deve ser maior que zero."
            )
            continue

        registros_medicamentos.append(
            {
                "medicamento": medicamento,
                "lote": lote,
                "quantidade": quantidade,
            }
        )

    for index in range(len(st.session_state.materiais_aplicacao)):
        material = st.session_state.get(
            f"material_{index}",
            "",
        )

        lote_material = st.session_state.get(
            f"lote_material_{index}",
            "",
        )

        quantidade = float(
            st.session_state.get(
                f"quantidade_material_{index}",
                0,
            )
        )

        if lote_material == "—":
            erros.append(
                f"Material {index + 1}: selecione um lote."
            )
            continue

        if quantidade <= 0:
            erros.append(
                f"Material {index + 1}: "
                "a quantidade deve ser maior que zero."
            )
            continue

        registros_materiais.append(
            {
                "material": material,
                "lote": lote_material,
                "quantidade": quantidade,
            }
        )

    if not registros_medicamentos:
        erros.append(
            "Adicione pelo menos um medicamento."
        )

    if erros:
        for erro in erros:
            st.error(erro)
    else:
        sucesso, mensagem = registrar_aplicacao_multiplos(
            medicamentos=registros_medicamentos,
            materiais=registros_materiais,
            aplicador=aplicador.strip(),
            paciente=paciente.strip(),
            observacao=observacao.strip(),
        )

        if sucesso:
            st.success(mensagem)

            st.session_state.medicamentos_aplicacao = [
                novo_medicamento()
            ]
            st.session_state.materiais_aplicacao = []

            for chave in list(st.session_state.keys()):
                if (
                    chave.startswith("medicamento_")
                    or chave.startswith("lote_medicamento_")
                    or chave.startswith("quantidade_medicamento_")
                    or chave.startswith("material_")
                    or chave.startswith("lote_material_")
                    or chave.startswith("quantidade_material_")
                ):
                    del st.session_state[chave]

            st.rerun()
        else:
            st.error(mensagem)


st.markdown(
    '<div class="section-header">Últimas aplicações</div>',
    unsafe_allow_html=True,
)

recentes = ler_registro_diario()

if recentes.empty:
    st.info("Nenhuma aplicação registrada ainda.")
else:
    recentes["_ordem_data"] = pd.to_datetime(
        recentes["Data Hora"].astype(str),
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )

    recentes = recentes.sort_values(
        "_ordem_data",
        ascending=False,
        na_position="last",
    )

    recentes["Medicamento"] = recentes.apply(
        lambda linha: resumir_json_registro(linha, "Medicamento", "Medicamentos JSON"),
        axis=1,
    )
    recentes["Lote"] = recentes.apply(
        lambda linha: resumir_json_registro(linha, "Lote", "Lote Medicamentos"),
        axis=1,
    )
    recentes["Material"] = recentes.apply(
        lambda linha: resumir_json_registro(linha, "Material", "Materiais JSON"),
        axis=1,
    )
    recentes["Lote Material"] = recentes.apply(
        lambda linha: resumir_json_registro(linha, "Lote Material", "Lote Materiais"),
        axis=1,
    )

    colunas = [
        "ID",
        "Data Hora",
        "Medicamento",
        "Lote",
        "Quantidade Medicamento",
        "Quantidade Material",
        "Material",
        "Lote Material",
        "Aplicador",
        "Paciente",
        "Observação",
    ]

    colunas_existentes = [
        coluna
        for coluna in colunas
        if coluna in recentes.columns
    ]

    dados = recentes[colunas_existentes].fillna("")
    st.markdown(renderizar_tabela_aplicacoes(dados), unsafe_allow_html=True)
