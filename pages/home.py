import streamlit as st
import plotly.graph_objects as go
from services.estoque_service import get_estoque
from services.dashboard_service import get_kpis, get_kpis_materiais
from utils.helpers import metric_card, status_label, normalize_status

st.markdown(
    '<h2 style="margin:0 0 12px 0;color:#f1f5f9;font-size:1.4rem;font-weight:700;">🏠 Página Inicial</h2>',
    unsafe_allow_html=True,
)

kpis   = get_kpis()
kpis_m = get_kpis_materiais()

# ── KPI Block: Medicamentos ────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;'
    'color:#64748b;margin-bottom:6px;">Estoque de Medicamentos</div>',
    unsafe_allow_html=True,
)
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.markdown(metric_card("⚫ VENCIDO",                kpis.get("vencidos", 0), "⚫", "#475569"), unsafe_allow_html=True)
mc2.markdown(metric_card("🔴 CRÍTICO (até 15 dias)",  kpis.get("critico",  0), "🔴", "#ef4444"), unsafe_allow_html=True)
mc3.markdown(metric_card("🟠 ATENÇÃO (16 a 89 dias)", kpis.get("atencao",  0), "🟠", "#f97316"), unsafe_allow_html=True)
mc4.markdown(metric_card("🟡 PRÓXIMO (90 a 120 dias)",kpis.get("proximos", 0), "🟡", "#f59e0b"), unsafe_allow_html=True)
mc5.markdown(metric_card("🟢 OK (+120 dias)",         kpis.get("ok",       0), "🟢", "#22c55e"), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

# ── KPI Block: Materiais ───────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;'
    'color:#64748b;margin-bottom:6px;">Estoque de Materiais</div>',
    unsafe_allow_html=True,
)
mm1, mm2, mm3, mm4, mm5 = st.columns(5)
mm1.markdown(metric_card("⚫ VENCIDO",                kpis_m.get("vencidos", 0), "⚫", "#475569"), unsafe_allow_html=True)
mm2.markdown(metric_card("🔴 CRÍTICO (até 15 dias)",  kpis_m.get("critico",  0), "🔴", "#ef4444"), unsafe_allow_html=True)
mm3.markdown(metric_card("🟠 ATENÇÃO (16 a 89 dias)", kpis_m.get("atencao",  0), "🟠", "#f97316"), unsafe_allow_html=True)
mm4.markdown(metric_card("🟡 PRÓXIMO (90 a 120 dias)",kpis_m.get("proximos", 0), "🟡", "#f59e0b"), unsafe_allow_html=True)
mm5.markdown(metric_card("🟢 OK (+120 dias)",         kpis_m.get("ok",       0), "🟢", "#22c55e"), unsafe_allow_html=True)

st.markdown("<hr style='border-color:#1e293b;margin:16px 0'/>", unsafe_allow_html=True)

# ── Plotly dark table: últimos medicamentos ────────────────────────────────────
st.markdown(
    '<div style="font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;'
    'color:#64748b;margin-bottom:8px;">Últimos Medicamentos Cadastrados</div>',
    unsafe_allow_html=True,
)

df = get_estoque()

_STATUS_COLOR = {
    "Vencido": "#475569",
    "Crítico": "#ef4444",
    "Atenção":  "#f97316",
    "Próximo":  "#f59e0b",
    "OK":       "#22c55e",
}
_BG   = "#0f172a"
_HEAD = "#1e293b"
_FONT = "#e2e8f0"
_GRID = "#1e293b"

if df.empty:
    st.info("Nenhum medicamento cadastrado ainda.")
else:
    cols_show = ["Medicamento", "Quantidade", "Unidade de Medida", "Lote", "Data de Vencimento", "Status"]
    dft = df[cols_show].tail(15).iloc[::-1].reset_index(drop=True)
    dft["Status"] = dft["Status"].map(lambda s: status_label(str(s)))
    status_colors = [_STATUS_COLOR.get(normalize_status(s), "#334155") for s in dft["Status"]]

    fig = go.Figure(go.Table(
        columnwidth=[240, 80, 140, 120, 150, 100],
        header=dict(
            values=[f"<b>{c}</b>" for c in cols_show],
            fill_color=_HEAD,
            font=dict(color="#64748b", size=12, family="monospace"),
            align="left",
            height=36,
            line=dict(color="#0f172a", width=1),
        ),
        cells=dict(
            values=[dft[c].tolist() for c in cols_show],
            fill_color=[
                [_BG] * len(dft),
                [_BG] * len(dft),
                [_BG] * len(dft),
                [_BG] * len(dft),
                [_BG] * len(dft),
                status_colors,
            ],
            font=dict(
                color=[
                    [_FONT] * len(dft),
                    [_FONT] * len(dft),
                    [_FONT] * len(dft),
                    [_FONT] * len(dft),
                    [_FONT] * len(dft),
                    ["#fff"] * len(dft),
                ],
                size=13,
            ),
            align="left",
            height=34,
            line=dict(color="#0f172a", width=1),
        ),
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        height=min(34 * len(dft) + 60, 600),
    )
    st.plotly_chart(fig, use_container_width=True)

