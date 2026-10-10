import json
import html
import pandas as pd
import streamlit as st
from datetime import date, datetime, time

from services.aplicacao_service import (
    registrar_aplicacao,
    registrar_aplicacao_multiplos,
)
from services.estoque_service import (
    get_estoque,
    get_lotes_por_medicamento,
    get_materiais,
    get_materiales_list,
    get_quantidade_disponivel,
    get_quantidade_disponivel_material,
)
from services.sheets_service import ler_registro_diario
from utils.helpers import normalizar_texto


st.markdown(
    """
    <style>
    .grupo-medicamentos {
        border-left: 5px solid #dc3545;
        padding-left: 14px;
        margin: 25px 0 15px;
    }

    .grupo-materiais {
        border-left: 5px solid #e11d48;
        padding-left: 14px;
        margin: 35px 0 15px;
    }

    .titulo-medicamentos {
        color: #fda4af !important;
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

    .lista-aplicacoes {
        display: grid;
        gap: 14px;
        margin-top: 12px;
    }

    .aplicacao-item {
        padding: 16px 18px;
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        border-radius: 10px;
        background: linear-gradient(135deg, #172033, #111827);
    }

    .aplicacao-cabecalho {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 12px;
        color: #e2e8f0 !important;
        font-size: 0.86rem;
    }

    .aplicacao-paciente {
        color: #f8fafc !important;
        font-weight: 800;
    }

    .aplicacao-data {
        color: #7dd3fc !important;
        white-space: nowrap;
    }

    .aplicacao-grupos {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 16px;
    }

    .aplicacao-grupo-titulo {
        margin-bottom: 6px;
        color: #a5b4fc !important;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .aplicacao-linha {
        margin: 5px 0;
        color: #dbeafe !important;
        font-size: 0.82rem;
        line-height: 1.45;
    }

    .aplicacao-detalhe {
        color: #94a3b8 !important;
    }

    @media (max-width: 760px) {
        .aplicacao-grupos { grid-template-columns: 1fr; }
        .aplicacao-cabecalho { display: block; }
        .aplicacao-data { display: block; margin-top: 4px; }
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
    lotes = sorted(get_lotes_por_medicamento(medicamento))

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


def rotulo_lote_medicamento(lote: str, medicamento: str) -> str:
    """Mostra o lote com a validade sem alterar o valor salvo no formulário."""
    linhas = estoque_medicamentos[
        (
            estoque_medicamentos["Medicamento"].map(normalizar_texto)
            == normalizar_texto(medicamento)
        )
        & (
            estoque_medicamentos["Lote"].fillna("").astype(str).str.strip()
            == str(lote).strip()
        )
    ]
    if linhas.empty:
        return str(lote)

    validade = str(linhas.iloc[0].get("Data de Vencimento", "")).strip()
    return f"{lote} | Vencimento: {validade or 'não informado'}"


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


def _unidade_medicamento(medicamento: str, lote: str) -> str:
    linhas = estoque_medicamentos[
        (estoque_medicamentos["Medicamento"].map(normalizar_texto) == normalizar_texto(medicamento))
        & (estoque_medicamentos["Lote"].fillna("").astype(str).str.strip() == str(lote).strip())
    ]
    if linhas.empty:
        return "unidade(s)"
    linha = linhas.iloc[0]
    return obter_unidade_consumo(linha, str(linha.get("Unidade Fracionada", "")).strip().lower() == "sim") or str(linha.get("Unidade de Medida", "unidade(s)"))


def _unidade_material(material: str, lote: str) -> str:
    linhas = df_materiais[
        (df_materiais["Material"].map(normalizar_texto) == normalizar_texto(material))
        & (df_materiais["Lote"].fillna("").astype(str).str.strip() == str(lote).strip())
    ]
    return str(linhas.iloc[0].get("Unidade de Medida", "unidade(s)")) if not linhas.empty else "unidade(s)"


def _linhas_lista_aplicacao(valor: object, tipo: str, unidade_fallback: str = "unidade(s)") -> list[str]:
    try:
        itens = json.loads(str(valor)) if str(valor).strip() else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if isinstance(itens, dict):
        itens = itens.get("itens", [itens])
    if not isinstance(itens, list):
        return []
    linhas = []
    for indice, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            continue
        nome = item.get(tipo, "")
        lote = str(item.get("lote", "")).strip()
        quantidade = item.get("quantidade", "")
        unidade = str(item.get("unidade", "")).strip() or ( _unidade_medicamento(nome, lote) if tipo == "medicamento" else _unidade_material(nome, lote) ) or unidade_fallback
        detalhe = f"{quantidade} {unidade}" if quantidade != "" else "Quantidade não informada"
        lote_texto = f"Lote: {lote or 'não informado'}"
        linhas.append(f"<div class='aplicacao-linha'><b>{indice}. {html.escape(str(nome))}</b><br><span class='aplicacao-detalhe'>{html.escape(lote_texto)} · {html.escape(detalhe)}</span></div>")
    return linhas


def renderizar_lista_aplicacoes(dados: pd.DataFrame) -> str:
    """Renderiza aplicações como cartões legíveis e espaçados."""
    if dados.empty:
        return '<div class="tabela-vazia">Nenhuma aplicação registrada ainda.</div>'
    cards = []
    for _, linha in dados.iterrows():
        medicamentos_html = "".join(_linhas_lista_aplicacao(linha.get("Medicamentos JSON", ""), "medicamento")) or "<div class='aplicacao-linha'>Nenhum medicamento detalhado</div>"
        materiais_html = "".join(_linhas_lista_aplicacao(linha.get("Materiais JSON", ""), "material")) or "<div class='aplicacao-linha'>Nenhum material utilizado</div>"
        cards.append(
            '<article class="aplicacao-item">'
            f'<div class="aplicacao-cabecalho"><span class="aplicacao-paciente">Paciente: {html.escape(str(linha.get("Paciente", "")))}</span><span class="aplicacao-data">{html.escape(str(linha.get("Data Hora", "")))}</span></div>'
            '<div class="aplicacao-grupos">'
            f'<div><div class="aplicacao-grupo-titulo">Medicamentos utilizados</div>{medicamentos_html}</div>'
            f'<div><div class="aplicacao-grupo-titulo">Materiais utilizados</div>{materiais_html}</div>'
            '</div>'
            f'<div class="aplicacao-detalhe">Observação: {html.escape(str(linha.get("Observação", "")))}</div>'
            '</article>'
        )
    return f'<div class="lista-aplicacoes">{"".join(cards)}</div>'


st.markdown(
    '<div class="section-header">Dados da aplicação</div>',
    unsafe_allow_html=True,
)

coluna1, coluna2, coluna3 = st.columns(3)

with coluna1:
    aplicador = st.text_input(
        "Aplicador *",
        value="Stephanny",
        key="aplicador",
    )

with coluna2:
    data_aplicacao = st.date_input(
        "Data da aplicação *",
        value=date.today(),
        format="DD/MM/YYYY",
        key="data_aplicacao",
    )

with coluna3:
    hora_aplicacao = st.time_input(
        "Hora da aplicação *",
        value=datetime.now().time().replace(second=0, microsecond=0),
        key="hora_aplicacao",
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

dar_baixa_estoque = st.checkbox(
    "Dar baixa no estoque nesta aplicação",
    value=True,
    help="Desmarque quando o registro for apenas histórico. Nesse caso, as quantidades não serão alteradas no estoque.",
    key="dar_baixa_estoque",
)

justificativa_retroativa = ""
if data_aplicacao < date.today():
    st.markdown(
        """
        <style>
        .st-key-justificativa-retroativa textarea {
            background-color: #ffffff !important;
            color: #111827 !important;
            -webkit-text-fill-color: #111827 !important;
            caret-color: #111827 !important;
        }
        .st-key-justificativa-retroativa textarea::placeholder {
            color: #6b7280 !important;
            -webkit-text-fill-color: #6b7280 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="justificativa-retroativa"):
        justificativa_retroativa = st.text_area(
            "Justificativa da aplicação retroativa *",
            placeholder="Obrigatória quando a data da aplicação for anterior a hoje.",
            help="Informe por que a aplicação está sendo lançada depois da data em que ocorreu.",
            key="justificativa_retroativa",
        )


titulo_medicamentos, acao_medicamentos = st.columns([8, 1])
with titulo_medicamentos:
    st.markdown(
        '<div class="grupo-medicamentos">'
        '<h2 class="titulo-medicamentos">Medicamentos</h2>'
        "</div>",
        unsafe_allow_html=True,
    )
with acao_medicamentos:
    st.button(
        "+",
        key="add-medication-header",
        on_click=lambda: st.session_state.medicamentos_aplicacao.append(
            novo_medicamento()
        ),
        help="Adicionar medicamento",
    )

colunas_medicamentos = st.columns(
    min(len(st.session_state.medicamentos_aplicacao), 3)
)

for index, item in enumerate(st.session_state.medicamentos_aplicacao):
    with colunas_medicamentos[index % 3]:
        with st.container(border=True, key=f"medication-card-{index}"):
            st.markdown(f"### {index + 1}. Medicamento")

            chave_medicamento = f"medicamento_{index}"
            chave_lote = f"lote_medicamento_{index}"
            chave_quantidade = f"quantidade_medicamento_{index}"

            medicamento_atual = item["medicamento"]

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

            lotes = sorted(get_lotes_por_medicamento(medicamento))

            if st.session_state.get(chave_lote) not in lotes:
                st.session_state[chave_lote] = lotes[0] if lotes else "—"

            lote = st.selectbox(
                "Lote *",
                options=lotes if lotes else ["—"],
                format_func=lambda valor: rotulo_lote_medicamento(valor, medicamento),
                key=chave_lote,
            )

            disponivel = (
                get_quantidade_disponivel(medicamento, lote)
                if lote != "—"
                else 0
            )

            linha_medicamento = estoque_medicamentos[
                (
                    estoque_medicamentos["Medicamento"].map(normalizar_texto)
                    == normalizar_texto(medicamento)
                )
                & (
                    estoque_medicamentos["Lote"].fillna("").astype(str).str.strip()
                    == str(lote).strip()
                )
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

            st.markdown(
                f'<div class="resumo-estoque"><b>Unidade de consumo:</b> '
                f'{html.escape(unidade_consumo or "unidade(s)")}</div>',
                unsafe_allow_html=True,
            )

            max_quantidade_medicamento = (
                max(float(disponivel), 0.01)
                if dar_baixa_estoque
                else 1_000_000.0
            )
            quantidade = st.number_input(
                (
                    f"Consumo ({unidade_consumo}) *"
                    if fracionado and unidade_consumo
                    else "Quantidade *"
                ),
                min_value=0.01,
                max_value=max_quantidade_medicamento,
                value=min(
                    float(item.get("quantidade", 1)),
                    max_quantidade_medicamento,
                ),
                step=0.01,
                key=chave_quantidade,
            )

            resumo = (
                resumo_estoque_fracionado(dados_medicamento, disponivel)
                if fracionado and not linha_medicamento.empty
                else f"Disponível: {disponivel:g} unidade(s)"
            )
            st.markdown(f'<div class="resumo-estoque">{resumo}</div>', unsafe_allow_html=True)

            st.button(
                "🗑️ Remover",
                key=f"remover_medicamento_{index}",
                on_click=remover_medicamento,
                args=(index,),
                width="stretch",
            )


st.button(
    "➕ Adicionar medicamento",
    width="stretch",
    on_click=lambda: (
        st.session_state.medicamentos_aplicacao.append(
            novo_medicamento()
        )
    ),
)


titulo_materiais, acao_materiais = st.columns([8, 1])
with titulo_materiais:
    st.markdown(
        '<div class="grupo-materiais">'
        '<h2 class="titulo-materiais">Materiais</h2>'
        "</div>",
        unsafe_allow_html=True,
    )
with acao_materiais:
    st.button(
        "+",
        key="add-material-header",
        on_click=lambda: st.session_state.materiais_aplicacao.append(
            novo_material()
        ),
        help="Adicionar material",
    )

if not materiais:
    st.info("Nenhum material cadastrado.")
else:
    colunas_materiais = st.columns(
        min(len(st.session_state.materiais_aplicacao), 3)
    ) if st.session_state.materiais_aplicacao else []

    for index, item in enumerate(st.session_state.materiais_aplicacao):
        with colunas_materiais[index % 3]:
            with st.container(border=True, key=f"material-card-{index}"):
                st.markdown(f"### {index + 1}. Material")

                chave_material = f"material_{index}"
                chave_lote = f"lote_material_{index}"
                chave_quantidade = f"quantidade_material_{index}"

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

                lote_material = st.selectbox(
                    "Lote *",
                    options=lotes_material if lotes_material else ["—"],
                    key=chave_lote,
                )

                linha_material = df_materiais[
                    (df_materiais["Material"] == material)
                    & (df_materiais["Lote"].fillna("").astype(str).str.strip() == str(lote_material).strip())
                ]
                unidade_material = (
                    str(linha_material.iloc[0].get("Unidade de Medida", "unidade(s)"))
                    if not linha_material.empty else "unidade(s)"
                )

                st.markdown(
                    f'<div class="resumo-estoque"><b>Unidade de estoque:</b> '
                    f'{html.escape(unidade_material)}</div>',
                    unsafe_allow_html=True,
                )

                disponivel_material = (
                    get_quantidade_disponivel_material(
                        material,
                        lote_material,
                    )
                    if lote_material != "—"
                    else 0
                )

                max_quantidade_material = (
                    max(int(disponivel_material), 1)
                    if dar_baixa_estoque
                    else 1_000_000
                )
                st.number_input(
                    "Quantidade *",
                    min_value=1,
                    max_value=max_quantidade_material,
                    value=min(
                        int(item.get("quantidade", 1)),
                        max_quantidade_material,
                    ),
                    step=1,
                    key=chave_quantidade,
                )

                st.markdown(
                    f'<div class="resumo-estoque">'
                    f"Disponível: {disponivel_material} unidade(s)"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                st.button(
                    "🗑️ Remover",
                    key=f"remover_material_{index}",
                    on_click=remover_material,
                    args=(index,),
                    width="stretch",
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
    data_hora_aplicacao = datetime.combine(
        data_aplicacao,
        hora_aplicacao or time(0, 0),
    ).strftime("%d/%m/%Y %H:%M:%S")
    aplicacao_retroativa = data_aplicacao < date.today()

    if not aplicador.strip():
        erros.append("Informe o aplicador.")

    if not paciente.strip():
        erros.append("Informe o paciente.")

    if data_aplicacao > date.today():
        erros.append("A data da aplicação não pode ser futura.")

    if aplicacao_retroativa and not justificativa_retroativa.strip():
        erros.append("Informe a justificativa para a aplicação retroativa.")

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
            justificativa=justificativa_retroativa.strip(),
            data_hora=data_hora_aplicacao,
            dar_baixa_estoque=dar_baixa_estoque,
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

    colunas = ["Data Hora", "Paciente", "Medicamentos JSON", "Materiais JSON", "Observação"]

    colunas_existentes = [
        coluna
        for coluna in colunas
        if coluna in recentes.columns
    ]

    dados = recentes[colunas_existentes].fillna("")
    st.markdown(renderizar_lista_aplicacoes(dados), unsafe_allow_html=True)
