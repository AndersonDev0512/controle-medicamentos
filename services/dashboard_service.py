from __future__ import annotations
import pandas as pd
import streamlit as st
from datetime import date
from services.estoque_service import get_estoque
from services.sheets_service import ler_registro_diario
from utils.constants import STATUS_VENCIDO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK
from utils.helpers import safe_int


@st.cache_data(ttl=60)
def get_kpis() -> dict:
    df = get_estoque()
    hoje_str = date.today().strftime("%d/%m/%Y")

    if df.empty:
        return {k: 0 for k in ("total_medicamentos", "quantidade_total", "vencidos", "atencao", "proximos", "ok", "aplicacoes_hoje")}

    qtd_total = sum(safe_int(v) for v in df["Quantidade"])
    registro = ler_registro_diario()
    aplicacoes_hoje = (
        int(registro["Data Hora"].astype(str).str.startswith(hoje_str).sum())
        if not registro.empty
        else 0
    )

    return {
        "total_medicamentos": len(df),
        "quantidade_total": qtd_total,
        "vencidos": int((df["Status"] == STATUS_VENCIDO).sum()),
        "atencao": int((df["Status"] == STATUS_ATENCAO).sum()),
        "proximos": int((df["Status"] == STATUS_PROXIMO).sum()),
        "ok": int((df["Status"] == STATUS_OK).sum()),
        "aplicacoes_hoje": aplicacoes_hoje,
    }


@st.cache_data(ttl=60)
def get_chart_status() -> pd.DataFrame:
    df = get_estoque()
    if df.empty:
        return pd.DataFrame(columns=["Status", "Quantidade"])
    return df.groupby("Status").size().reset_index(name="Quantidade")


@st.cache_data(ttl=60)
def get_chart_quantidade_por_medicamento() -> pd.DataFrame:
    df = get_estoque()
    if df.empty:
        return pd.DataFrame(columns=["Medicamento", "Quantidade"])
    df2 = df.copy()
    df2["Quantidade"] = df2["Quantidade"].apply(safe_int)
    return (
        df2.groupby("Medicamento")["Quantidade"]
        .sum()
        .reset_index()
        .sort_values("Quantidade", ascending=False)
    )


@st.cache_data(ttl=60)
def get_chart_aplicacoes_diarias() -> pd.DataFrame:
    registro = ler_registro_diario()
    if registro.empty:
        return pd.DataFrame(columns=["Data", "Aplicações"])
    df = registro.copy()
    df["Data"] = df["Data Hora"].astype(str).str[:10]
    return df.groupby("Data").size().reset_index(name="Aplicações").sort_values("Data")


@st.cache_data(ttl=60)
def get_chart_mais_utilizados() -> pd.DataFrame:
    registro = ler_registro_diario()
    if registro.empty:
        return pd.DataFrame(columns=["Medicamento", "Total"])
    df = registro.copy()
    df["Quantidade"] = df["Quantidade"].apply(safe_int)
    return (
        df.groupby("Medicamento")["Quantidade"]
        .sum()
        .reset_index(name="Total")
        .sort_values("Total", ascending=False)
        .head(10)
    )
