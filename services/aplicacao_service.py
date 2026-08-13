from __future__ import annotations
from services.sheets_service import (
    ler_estoque,
    atualizar_medicamento,
    adicionar_registro_diario,
    adicionar_historico,
)
from services.estoque_service import get_estoque
from utils.helpers import formatar_data_hora, safe_int
from utils.constants import COLUNAS_ESTOQUE


def registrar_aplicacao(
    medicamento: str, lote: str, quantidade: int
) -> tuple[bool, str]:
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

    nova_qtd = qtd_atual - quantidade
    dados = {c: df.at[df_idx, c] for c in COLUNAS_ESTOQUE}
    dados["Quantidade"] = nova_qtd

    if not atualizar_medicamento(df_idx, dados):
        return False, "Erro ao atualizar estoque."

    # Invalidate derived cache
    get_estoque.clear()

    data_hora = formatar_data_hora()
    adicionar_registro_diario(
        {"Data Hora": data_hora, "Medicamento": medicamento, "Lote": lote, "Quantidade": quantidade}
    )
    adicionar_historico(
        {
            "Data Hora": data_hora,
            "Tipo": "Saída",
            "Medicamento": medicamento,
            "Quantidade": quantidade,
            "Observação": f"Aplicação — Lote: {lote}",
        }
    )

    return True, f"Aplicação de **{quantidade}** unidade(s) de **{medicamento}** registrada com sucesso!"
