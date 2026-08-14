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
STATUS_CRITICO: Final = "Crítico"

# Updated thresholds to match requested buckets:
# dias < 0 -> Vencido
# dias <= DIAS_CRITICO (15) -> Crítico
# dias <= DIAS_ATENCAO (89) -> Atenção
# dias <= DIAS_PROXIMO (120) -> Próximo
# else -> OK
CORES_STATUS: Final = {
    STATUS_VENCIDO: "#0f172a",
    STATUS_CRITICO: "#ef4444",
    STATUS_ATENCAO: "#f97316",
    STATUS_PROXIMO: "#f59e0b",
    STATUS_OK: "#22c55e",
}

DIAS_CRITICO: Final = 15
DIAS_ATENCAO: Final = 89
DIAS_PROXIMO: Final = 120
