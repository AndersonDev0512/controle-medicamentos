from __future__ import annotations
import pandas as pd
import streamlit as st
from services.sheets_service import ler_estoque, ler_materiais
from utils.helpers import calcular_dias_para_vencer, calcular_status, safe_int
from utils.constants import UNIDADES_MEDIDA


@st.cache_data(ttl=30)
def get_estoque() -> pd.DataFrame:
    """Return stock DataFrame with recalculated expiry days and status."""
    df = ler_estoque().copy()
    if df.empty:
        return df
    df["Dias para Vencer"] = df["Data de Vencimento"].apply(calcular_dias_para_vencer)
    df["Status"] = df["Dias para Vencer"].apply(calcular_status)
    return df


def get_unidades_from_sheet() -> list[str]:
    df = get_estoque()
    sheet_units: list[str] = []
    if not df.empty:
        sheet_units = df["Unidade de Medida"].dropna().astype(str).str.strip().unique().tolist()
    return sorted(set(UNIDADES_MEDIDA) | {u for u in sheet_units if u})


def get_medicamentos_list() -> list[str]:
    df = get_estoque()
    if df.empty:
        return []
    return sorted(df["Medicamento"].dropna().unique().tolist())


def get_lotes_por_medicamento(medicamento: str) -> list[str]:
    df = get_estoque()
    if df.empty:
        return []
    return df[df["Medicamento"] == medicamento]["Lote"].dropna().unique().tolist()


def get_quantidade_disponivel(medicamento: str, lote: str) -> int:
    df = get_estoque()
    if df.empty:
        return 0
    mask = (df["Medicamento"] == medicamento) & (df["Lote"] == lote)
    rows = df[mask]
    if rows.empty:
        return 0
    return safe_int(rows.iloc[0]["Quantidade"])


@st.cache_data(ttl=30)
def get_materiais() -> pd.DataFrame:
    """Return materiais DataFrame with recalculated expiry days and status."""
    df = ler_materiais().copy()
    if df.empty:
        return df
    df["Dias para Vencer"] = df["Data de Vencimento"].apply(calcular_dias_para_vencer)
    df["Status"] = df["Dias para Vencer"].apply(calcular_status)
    return df


def get_unidades_materiais_from_sheet() -> list[str]:
    df = get_materiais()
    sheet_units: list[str] = []
    if not df.empty:
        sheet_units = df["Unidade de Medida"].dropna().astype(str).str.strip().unique().tolist()
    return sorted(set(UNIDADES_MEDIDA) | {u for u in sheet_units if u})


def get_materiales_list() -> list[str]:
    df = get_materiais()
    if df.empty:
        return []
    return sorted(df["Material"].dropna().unique().tolist())


def get_lotes_por_material(material: str) -> list[str]:
    df = get_materiais()
    if df.empty:
        return []
    return df[df["Material"] == material]["Lote"].dropna().unique().tolist()


def get_quantidade_disponivel_material(material: str, lote: str) -> int:
    df = get_materiais()
    if df.empty:
        return 0
    mask = (df["Material"] == material) & (df["Lote"] == lote)
    rows = df[mask]
    if rows.empty:
        return 0
    return safe_int(rows.iloc[0]["Quantidade"])
