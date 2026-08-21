from __future__ import annotations
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
from utils.helpers import formatar_data_hora, safe_int
from utils.constants import COLUNAS_ESTOQUE, COLUNAS_MATERIAIS, COLUNAS_REGISTRO


def proximo_id_registro() -> int:
    df = ler_registro_diario()
    if df.empty or "ID" not in df.columns:
        return 1
    ids = pd.to_numeric(df["ID"], errors="coerce").dropna()
    return int(ids.max()) + 1 if not ids.empty else 1


def registrar_aplicacao(
    medicamento: str,
    lote: str,
    quantidade: int,
    material: str | None = None,
    lote_material: str | None = None,
    quantidade_material: int = 0,
    aplicador: str = "Sistema Streamlit",
    paciente: str = "",
    observacao: str = "",
    justificativa: str = "",
) -> tuple[bool, str]:
    if not paciente.strip():
        return False, "Nome do paciente é obrigatório."
    if not justificativa.strip():
        return False, "Justificativa é obrigatória para registrar uma aplicação."

    df = ler_estoque()
    mask = (df["Medicamento"] == medicamento) & (df["Lote"] == lote)
    indices = df[mask].index.tolist()

    if not indices:
        return False, "Medicamento/Lote não encontrado no estoque."

    df_idx = indices[0]
    qtd_atual = safe_int(df.at[df_idx, "Quantidade"])

    if quantidade <= 0:
        return False, "A quantidade deve ser maior que zero."
    if quantidade > qtd_atual:
        return False, f"Estoque insuficiente. Disponível: {qtd_atual}"

    material_atual = None
    material_nova_qtd = None
    material_sheet_row = None
    dados_mat = None
    if material and lote_material:
        df_mat = ler_materiais()
        mask_mat = (df_mat["Material"] == material) & (df_mat["Lote"] == lote_material)
        if not mask_mat.any():
            return False, "Material/Lote não encontrado no estoque."
        idx_mat = df_mat[mask_mat].index.tolist()[0]
        qtd_mat_atual = safe_int(df_mat.at[idx_mat, "Quantidade"])
        if quantidade_material <= 0:
            return False, "Informe a quantidade de material utilizada."
        if quantidade_material > qtd_mat_atual:
            return False, f"Estoque de material insuficiente. Disponível: {qtd_mat_atual}"
        material_atual = qtd_mat_atual
        material_nova_qtd = qtd_mat_atual - quantidade_material
        material_sheet_row = int(df_mat.at[idx_mat, "_sheet_row"])
        dados_mat = {c: df_mat.at[idx_mat, c] for c in COLUNAS_MATERIAIS}
        dados_mat["Quantidade"] = material_nova_qtd

    nova_qtd = qtd_atual - quantidade
    dados = {c: df.at[df_idx, c] for c in COLUNAS_ESTOQUE}
    dados["Quantidade"] = nova_qtd
    sheet_row = int(df.at[df_idx, "_sheet_row"])

    # Garante a aba antes de baixar o estoque, evitando uma baixa sem registro.
    if not adicionar_registro_diario({}):
        return False, "Não foi possível preparar a aba de registro diário."

    if not atualizar_medicamento(sheet_row, dados):
        return False, "Erro ao atualizar estoque do medicamento."
    if dados_mat is not None and not atualizar_material(material_sheet_row, dados_mat):
        return False, "Erro ao atualizar estoque de materiais."

    get_estoque.clear()
    get_materiais.clear()

    data_hora = formatar_data_hora()
    registro = {
        "ID": proximo_id_registro(),
        "Data Hora": data_hora,
        "Medicamento": medicamento,
        "Lote": lote,
        "Quantidade": quantidade,
        "Quantidade Medicamento": quantidade,
        "Quantidade Material": quantidade_material if material else 0,
        "Material": material or "",
        "Lote Material": lote_material or "",
        "Aplicador": aplicador,
        "Paciente": paciente,
        "Observação": observacao or justificativa or "",
    }
    if not adicionar_registro_diario(registro):
        atualizar_medicamento(sheet_row, {**dados, "Quantidade": qtd_atual})
        if dados_mat is not None:
            atualizar_material(material_sheet_row, {**dados_mat, "Quantidade": material_atual})
        return False, "Aplicação registrada no estoque, mas houve erro ao salvar o registro diário."
    if not adicionar_historico(
        {
            "Data Hora": data_hora,
            "Tipo": "Saída",
            "Medicamento": medicamento,
            "Quantidade": quantidade,
            "Observação": observacao or justificativa or f"Aplicação — Lote: {lote}",
            "Aplicador": aplicador,
            "Paciente": paciente,
            "Material": material or "",
            "Lote Material": lote_material or "",
        }
    ):
        atualizar_medicamento(sheet_row, {**dados, "Quantidade": qtd_atual})
        if dados_mat is not None:
            atualizar_material(material_sheet_row, {**dados_mat, "Quantidade": material_atual})
        return False, "Aplicação registrada no estoque, mas houve erro ao salvar o histórico."

    auditar_alteracao(
        modulo="Aplicação",
        registro=f"{medicamento} - Lote {lote}",
        campo_alterado="Quantidade",
        valor_anterior=qtd_atual,
        valor_novo=nova_qtd,
        justificativa=justificativa,
        usuario=aplicador,
    )
    if material_atual is not None and material_nova_qtd is not None:
        auditar_alteracao(
            modulo="Aplicação",
            registro=f"{material} - Lote {lote_material}",
            campo_alterado="Quantidade",
            valor_anterior=material_atual,
            valor_novo=material_nova_qtd,
            justificativa=justificativa,
            usuario=aplicador,
        )

    return True, f"Aplicação de **{quantidade}** unidade(s) de **{medicamento}** registrada com sucesso!"
