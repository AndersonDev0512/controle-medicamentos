from typing import Final

COLUNAS_ESTOQUE: Final = [
    "Medicamento", "Quantidade", "Unidade de Medida", "Lote",
    "Data de Vencimento", "Dias para Vencer", "Status", "Observações",
]
COLUNAS_REGISTRO: Final = ["Data Hora", "Medicamento", "Lote", "Quantidade"]
COLUNAS_HISTORICO: Final = ["Data Hora", "Tipo", "Medicamento", "Quantidade", "Observação"]

UNIDADES_MEDIDA: Final = [
    "Comprimido(s)", "Ampola(s)", "Frasco(s)", "ml", "mg", "g",
    "Cápsula(s)", "Sache(s)", "Unidade(s)",
]

TIPOS_MOVIMENTACAO: Final = ["Entrada", "Saída", "Ajuste"]

STATUS_VENCIDO: Final = "Vencido"
STATUS_ATENCAO: Final = "Atenção"
STATUS_PROXIMO: Final = "Próximo"
STATUS_OK: Final = "OK"

CORES_STATUS: Final = {
    STATUS_VENCIDO: "#ef4444",
    STATUS_ATENCAO: "#f97316",
    STATUS_PROXIMO: "#f59e0b",
    STATUS_OK: "#22c55e",
}

DIAS_ATENCAO: Final = 30
DIAS_PROXIMO: Final = 90
