from __future__ import annotations

import json
import math
import pandas as pd

from services.sheets_service import (
    ler_estoque,
    ler_materiais,
    ler_registro_diario,
    atualizar_medicamento,
    atualizar_material,
    adicionar_registro_diario,
    adicionar_historico,
    auditar_alteracao,
)
from services.estoque_service import get_estoque, get_materiais
from utils.helpers import formatar_data_hora
from utils.constants import COLUNAS_ESTOQUE, COLUNAS_MATERIAIS


def _numero(valor: object, padrao: float = 0.0) -> float:
    try:
        if valor is None or str(valor).strip() == "":
            return padrao

        texto = str(valor).strip().replace(",", ".")

        return float(texto)
    except (TypeError, ValueError):
        return padrao


def _formatar_quantidade(valor: float) -> int | float:
    valor = float(valor)
    if valor.is_integer():
        return int(valor)

    return round(valor, 4)


def proximo_id_registro() -> int:
    df = ler_registro_diario()

    if df.empty or "ID" not in df.columns:
        return 1

    ids = pd.to_numeric(df["ID"], errors="coerce").dropna()

    return int(ids.max()) + 1 if not ids.empty else 1


def _calcular_estoque_medicamento(
    linha: pd.Series,
    quantidade_utilizada: float,
) -> tuple[bool, str, dict]:
    quantidade_fechada_raw = linha.get("Quantidade Fechada", "")
    if str(quantidade_fechada_raw).strip() == "":
        quantidade_fechada_raw = linha.get("Quantidade", 0)
    quantidade_fechada = _numero(quantidade_fechada_raw)

    saldo_aberto = _numero(linha.get("Saldo Aberto", 0))
    volume_por_unidade = _numero(linha.get("Volume por Unidade", 0))
    unidade_fracionada = (
        str(linha.get("Unidade Fracionada", "Não")).strip().lower()
    )

    fracionavel = unidade_fracionada in {"sim", "s", "yes", "true"}

    if not fracionavel:
        quantidade_atual = _numero(
            linha.get("Quantidade", quantidade_fechada)
        )

        if quantidade_utilizada > quantidade_atual:
            return (
                False,
                f"Estoque insuficiente. Disponível: "
                f"{_formatar_quantidade(quantidade_atual)}",
                {},
            )

        nova_quantidade = quantidade_atual - quantidade_utilizada

        return (
            True,
            "",
            {
                "Quantidade": _formatar_quantidade(nova_quantidade),
                "Quantidade Fechada": _formatar_quantidade(nova_quantidade),
                "Saldo Aberto": 0,
                "Volume por Unidade": "",
                "Unidade Fracionada": "Não",
            },
        )

    if volume_por_unidade <= 0:
        return (
            False,
            "O medicamento fracionável não possui volume por unidade válido.",
            {},
        )

    volume_total_disponivel = (
        quantidade_fechada * volume_por_unidade
    ) + saldo_aberto

    volume_utilizado = quantidade_utilizada

    if volume_utilizado > volume_total_disponivel:
        quantidade_disponivel = (
            volume_total_disponivel / volume_por_unidade
        )

        return (
            False,
            f"Estoque insuficiente. Disponível: "
            f"{_formatar_quantidade(volume_total_disponivel)} "
            f"{str(linha.get('Unidade de Consumo', '')).strip() or 'unidade(s)'}.",
            {},
        )

    volume_restante = volume_total_disponivel - volume_utilizado

    nova_quantidade_fechada = math.floor(
        volume_restante / volume_por_unidade
    )

    novo_saldo_aberto = round(
        volume_restante
        - (nova_quantidade_fechada * volume_por_unidade),
        4,
    )

    return (
        True,
        "",
        {
            "Quantidade": _formatar_quantidade(nova_quantidade_fechada),
            "Quantidade Fechada": _formatar_quantidade(
                nova_quantidade_fechada
            ),
            "Saldo Aberto": _formatar_quantidade(novo_saldo_aberto),
            "Volume por Unidade": _formatar_quantidade(
                volume_por_unidade
            ),
            "Unidade Fracionada": "Sim",
        },
    )


def registrar_aplicacao(
    medicamento: str,
    lote: str,
    quantidade: float,
    material: str | None = None,
    lote_material: str | None = None,
    quantidade_material: int = 0,
    aplicador: str = "Sistema Streamlit",
    paciente: str = "",
    observacao: str = "",
    justificativa: str = "",
    id_registro: int | None = None,
    medicamentos_json: list[dict] | None = None,
    materiais_json: list[dict] | None = None,
    somente_material: bool = False,
    salvar_registro: bool = True,
    salvar_historico: bool = True,
) -> tuple[bool, str]:
    if not paciente.strip():
        return False, "Nome do paciente é obrigatório."

    quantidade = _numero(quantidade)

    if quantidade <= 0 and not somente_material:
        return False, "A quantidade deve ser maior que zero."

    df_estoque = ler_estoque()

    filtro_medicamento = (
        (df_estoque["Medicamento"] == medicamento)
        & (df_estoque["Lote"] == lote)
    )

    indices_medicamento = df_estoque[filtro_medicamento].index.tolist()

    if not indices_medicamento:
        return False, "Medicamento/Lote não encontrado no estoque."

    indice_medicamento = indices_medicamento[0]
    linha_medicamento = df_estoque.loc[indice_medicamento]

    if somente_material:
        sucesso, mensagem, alteracoes_medicamento = True, "", {}
    else:
        sucesso, mensagem, alteracoes_medicamento = _calcular_estoque_medicamento(
            linha_medicamento,
            quantidade,
        )

    if not sucesso:
        return False, mensagem

    dados_medicamento = {
        coluna: linha_medicamento.get(coluna, "")
        for coluna in COLUNAS_ESTOQUE
    }

    dados_medicamento.update(alteracoes_medicamento)

    medicamento_sheet_row = int(
        linha_medicamento["_sheet_row"]
    )

    dados_material = None
    material_sheet_row = None
    material_quantidade_anterior = None
    material_quantidade_nova = None

    if material and lote_material:
        df_materiais = ler_materiais()

        filtro_material = (
            (df_materiais["Material"] == material)
            & (df_materiais["Lote"] == lote_material)
        )

        indices_material = df_materiais[filtro_material].index.tolist()

        if not indices_material:
            return False, "Material/Lote não encontrado no estoque."

        indice_material = indices_material[0]
        linha_material = df_materiais.loc[indice_material]

        material_quantidade_anterior = _numero(
            linha_material.get("Quantidade", 0)
        )
        quantidade_material = _numero(quantidade_material)

        if quantidade_material <= 0:
            return False, "Informe a quantidade de material utilizada."

        if quantidade_material > material_quantidade_anterior:
            return (
                False,
                "Estoque de material insuficiente. "
                f"Disponível: "
                f"{_formatar_quantidade(material_quantidade_anterior)}",
            )

        material_quantidade_nova = (
            material_quantidade_anterior - quantidade_material
        )

        dados_material = {
            coluna: linha_material.get(coluna, "")
            for coluna in COLUNAS_MATERIAIS
        }

        dados_material["Quantidade"] = _formatar_quantidade(
            material_quantidade_nova
        )

        material_sheet_row = int(
            linha_material["_sheet_row"]
        )
    else:
        quantidade_material = 0

    if not somente_material and not atualizar_medicamento(
        medicamento_sheet_row,
        dados_medicamento,
    ):
        return False, "Erro ao atualizar estoque do medicamento."

    if dados_material is not None and material_sheet_row is not None:
        if not atualizar_material(
            material_sheet_row,
            dados_material,
        ):
            if not somente_material:
                atualizar_medicamento(
                    medicamento_sheet_row,
                    {
                        **dados_medicamento,
                        "Quantidade": linha_medicamento.get("Quantidade", 0),
                        "Quantidade Fechada": linha_medicamento.get(
                            "Quantidade Fechada", linha_medicamento.get("Quantidade", 0)
                        ),
                        "Saldo Aberto": linha_medicamento.get("Saldo Aberto", 0),
                    },
                )

            return False, "Erro ao atualizar estoque de materiais."

    get_estoque.clear()
    get_materiais.clear()

    data_hora = formatar_data_hora()
    id_registro = id_registro if id_registro is not None else proximo_id_registro()

    medicamentos_registro = [dict(item) for item in (medicamentos_json or [{
        "medicamento": medicamento,
        "lote": lote,
        "quantidade": _formatar_quantidade(quantidade),
    }])]
    materiais_registro = [dict(item) for item in (materiais_json or ([{
        "material": material,
        "lote": lote_material,
        "quantidade": _formatar_quantidade(quantidade_material),
    }] if material and lote_material else []))]

    for item in medicamentos_registro:
        if item.get("unidade"):
            continue
        nome = str(item.get("medicamento", "")).strip()
        lote_item = str(item.get("lote", "")).strip()
        linha_item = df_estoque[
            (df_estoque["Medicamento"] == nome)
            & (df_estoque["Lote"] == lote_item)
        ]
        if not linha_item.empty:
            dados_item = linha_item.iloc[0]
            fracionado_item = str(
                dados_item.get("Unidade Fracionada", "Não")
            ).strip().lower() == "sim"
            item["unidade"] = str(
                dados_item.get("Unidade de Consumo" if fracionado_item else "Unidade de Medida", "")
            ).strip()

    if materiais_registro:
        df_materiais_registro = ler_materiais()
        for item in materiais_registro:
            if item.get("unidade"):
                continue
            linha_item = df_materiais_registro[
                (df_materiais_registro["Material"] == str(item.get("material", "")).strip())
                & (df_materiais_registro["Lote"] == str(item.get("lote", "")).strip())
            ]
            if not linha_item.empty:
                item["unidade"] = str(
                    linha_item.iloc[0].get("Unidade de Medida", "")
                ).strip()

    registro = {
        "ID": id_registro,
        "Data Hora": data_hora,
        "Medicamento": "" if somente_material else medicamento,
        "Lote": "" if somente_material else lote,
        "Quantidade": _formatar_quantidade(quantidade),
        "Quantidade Medicamento": 0 if somente_material else _formatar_quantidade(quantidade),
        "Quantidade Material": _formatar_quantidade(
            quantidade_material
        ),
        "Material": material or "",
        "Lote Material": lote_material or "",
        "Aplicador": aplicador,
        "Paciente": paciente,
        "Observação": (
            observacao.strip()
            or f"Aplicação - Lote: {lote}"
        ),
        "Medicamentos JSON": json.dumps(
            medicamentos_registro,
            ensure_ascii=False,
        ),
        "Materiais JSON": json.dumps(
            materiais_registro,
            ensure_ascii=False,
        ),
    }

    if salvar_registro and not adicionar_registro_diario(registro):
        if not somente_material:
            atualizar_medicamento(
            medicamento_sheet_row,
            {
                **dados_medicamento,
                "Quantidade": linha_medicamento.get(
                    "Quantidade",
                    0,
                ),
                "Quantidade Fechada": linha_medicamento.get(
                    "Quantidade Fechada",
                    linha_medicamento.get("Quantidade", 0),
                ),
                "Saldo Aberto": linha_medicamento.get(
                    "Saldo Aberto",
                    0,
                ),
            },
        )

        if dados_material is not None and material_sheet_row is not None:
            atualizar_material(
                material_sheet_row,
                {
                    **dados_material,
                    "Quantidade": material_quantidade_anterior,
                },
            )

        return (
            False,
            "Estoque atualizado, mas houve erro ao salvar o registro diário.",
        )

    historico = {
        "Data Hora": data_hora,
        "Tipo": "Saída",
        "Medicamento": "" if somente_material else medicamento,
        "Quantidade": _formatar_quantidade(quantidade),
        "Observação": (
            observacao.strip()
            or f"Aplicação - Lote: {lote}"
        ),
        "Aplicador": aplicador,
        "Paciente": paciente,
        "Material": material or "",
        "Lote Material": lote_material or "",
    }

    if salvar_historico and not adicionar_historico(historico):
        if not somente_material:
            atualizar_medicamento(
            medicamento_sheet_row,
            {
                **dados_medicamento,
                "Quantidade": linha_medicamento.get(
                    "Quantidade",
                    0,
                ),
                "Quantidade Fechada": linha_medicamento.get(
                    "Quantidade Fechada",
                    linha_medicamento.get("Quantidade", 0),
                ),
                "Saldo Aberto": linha_medicamento.get(
                    "Saldo Aberto",
                    0,
                ),
            },
        )

        if dados_material is not None and material_sheet_row is not None:
            atualizar_material(
                material_sheet_row,
                {
                    **dados_material,
                    "Quantidade": material_quantidade_anterior,
                },
            )

        return (
            False,
            "Estoque atualizado, mas houve erro ao salvar o histórico.",
        )

    nova_quantidade = dados_medicamento.get(
        "Quantidade",
        0,
    )

    if not somente_material:
        auditar_alteracao(
            modulo="Aplicação",
            registro={
                "medicamentos": medicamentos_json or [{
                    "medicamento": medicamento,
                    "lote": lote,
                    "quantidade": _formatar_quantidade(quantidade),
                }],
                "materiais": materiais_json or ([{
                    "material": material,
                    "lote": lote_material,
                    "quantidade": _formatar_quantidade(quantidade_material),
                }] if material and lote_material else []),
            },
            campo_alterado="Quantidade",
            valor_anterior=linha_medicamento.get("Quantidade", 0),
            valor_novo=nova_quantidade,
            justificativa=justificativa,
            usuario=aplicador,
        )

    if (
        material
        and lote_material
        and material_quantidade_anterior is not None
        and material_quantidade_nova is not None
    ):
        auditar_alteracao(
            modulo="Aplicação",
            registro={
                "material": material,
                "lote": lote_material,
                "quantidade": _formatar_quantidade(quantidade_material),
            },
            campo_alterado="Quantidade",
            valor_anterior=material_quantidade_anterior,
            valor_novo=material_quantidade_nova,
            justificativa=justificativa,
            usuario=aplicador,
        )

    return (
        True,
        f"Aplicação de **{_formatar_quantidade(quantidade)}** "
        f"unidade(s) de **{medicamento}** registrada com sucesso!",
    )


def registrar_aplicacao_multiplos(
    medicamentos: list[dict],
    materiais: list[dict],
    aplicador: str,
    paciente: str,
    observacao: str = "",
) -> tuple[bool, str]:
    """Registra os itens selecionados pela tela de aplicação.

    O serviço legado registra uma combinação de medicamento/material por
    chamada. Para preservar esse contrato, os materiais ficam associados ao
    primeiro medicamento e os demais medicamentos são processados em seguida.
    Todos os dados são validados antes da primeira baixa.
    """
    if not paciente.strip():
        return False, "Nome do paciente é obrigatório."

    if not medicamentos:
        return False, "Adicione pelo menos um medicamento."

    medicamentos_validos: list[dict] = []
    for indice, item in enumerate(medicamentos, start=1):
        medicamento = str(item.get("medicamento", "")).strip()
        lote = str(item.get("lote", "")).strip()
        quantidade = _numero(item.get("quantidade", 0))

        if not medicamento or not lote or quantidade <= 0:
            return (
                False,
                f"Medicamento {indice}: informe medicamento, lote e quantidade válida.",
            )

        medicamentos_validos.append(
            {
                "medicamento": medicamento,
                "lote": lote,
                "quantidade": quantidade,
            }
        )

    materiais_validos: list[dict] = []
    for indice, item in enumerate(materiais, start=1):
        material = str(item.get("material", "")).strip()
        lote = str(item.get("lote", "")).strip()
        quantidade = _numero(item.get("quantidade", 0))

        if not material or not lote or quantidade <= 0:
            return (
                False,
                f"Material {indice}: informe material, lote e quantidade válida.",
            )

        materiais_validos.append(
            {
                "material": material,
                "lote": lote,
                "quantidade": quantidade,
            }
        )

    resultados: list[str] = []
    proximo_id = proximo_id_registro()
    medicamentos_json = [
        {
            "medicamento": item["medicamento"],
            "lote": item["lote"],
            "quantidade": _formatar_quantidade(item["quantidade"]),
        }
        for item in medicamentos_validos
    ]
    materiais_json = [
        {
            "material": item["material"],
            "lote": item["lote"],
            "quantidade": _formatar_quantidade(item["quantidade"]),
        }
        for item in materiais_validos
    ]
    for indice, item in enumerate(medicamentos_validos):
        materiais_do_item = materiais_validos if indice == 0 else []
        material = materiais_do_item[0] if materiais_do_item else None

        sucesso, mensagem = registrar_aplicacao(
            medicamento=item["medicamento"],
            lote=item["lote"],
            quantidade=item["quantidade"],
            material=material["material"] if material else None,
            lote_material=material["lote"] if material else None,
            quantidade_material=material["quantidade"] if material else 0,
            aplicador=aplicador,
            paciente=paciente,
            observacao=observacao,
            justificativa=observacao,
            id_registro=proximo_id,
            medicamentos_json=medicamentos_json,
            materiais_json=materiais_json if indice == 0 else [],
            salvar_registro=indice == 0,
            salvar_historico=indice == 0,
        )

        if not sucesso:
            return False, mensagem

        resultados.append(mensagem)
        proximo_id += 1

        for material_extra in materiais_do_item[1:]:
            sucesso_material, mensagem_material = registrar_aplicacao(
                medicamento=item["medicamento"],
                lote=item["lote"],
                quantidade=0,
                material=material_extra["material"],
                lote_material=material_extra["lote"],
                quantidade_material=material_extra["quantidade"],
                aplicador=aplicador,
                paciente=paciente,
                observacao=observacao,
                justificativa=observacao,
                id_registro=proximo_id,
                medicamentos_json=[],
                materiais_json=[{
                    "material": material_extra["material"],
                    "lote": material_extra["lote"],
                    "quantidade": _formatar_quantidade(material_extra["quantidade"]),
                }],
                somente_material=True,
                salvar_registro=False,
                salvar_historico=False,
            )

            if not sucesso_material:
                return False, mensagem_material

            proximo_id += 1

    return (
        True,
        f"Aplicação registrada com {len(medicamentos_validos)} "
        f"medicamento(s) e {len(materiais_validos)} material(is).",
    )
