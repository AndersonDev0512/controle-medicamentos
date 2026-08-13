import streamlit as st
from services.alerta_service import get_alertas
from utils.constants import STATUS_VENCIDO, STATUS_ATENCAO, STATUS_PROXIMO

st.markdown('<h1 class="page-title">⚠️ Alertas de Validade</h1>', unsafe_allow_html=True)

alertas = get_alertas()

# ── Summary counters ───────────────────────────────────────────────────────────
total_v = sum(1 for a in alertas if a.status == STATUS_VENCIDO)
total_a = sum(1 for a in alertas if a.status == STATUS_ATENCAO)
total_p = sum(1 for a in alertas if a.status == STATUS_PROXIMO)

sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.markdown(f"""
    <div style="background:#ef444415;border:1px solid #ef4444;border-radius:10px;padding:1rem;text-align:center;">
        <div style="font-size:2.2rem;font-weight:800;color:#ef4444;">{total_v}</div>
        <div style="color:#94a3b8;font-size:0.8rem;text-transform:uppercase;letter-spacing:.05em;">Vencidos</div>
    </div>""", unsafe_allow_html=True)
with sc2:
    st.markdown(f"""
    <div style="background:#f9731615;border:1px solid #f97316;border-radius:10px;padding:1rem;text-align:center;">
        <div style="font-size:2.2rem;font-weight:800;color:#f97316;">{total_a}</div>
        <div style="color:#94a3b8;font-size:0.8rem;text-transform:uppercase;letter-spacing:.05em;">Atenção (&lt;30 dias)</div>
    </div>""", unsafe_allow_html=True)
with sc3:
    st.markdown(f"""
    <div style="background:#f59e0b15;border:1px solid #f59e0b;border-radius:10px;padding:1rem;text-align:center;">
        <div style="font-size:2.2rem;font-weight:800;color:#f59e0b;">{total_p}</div>
        <div style="color:#94a3b8;font-size:0.8rem;text-transform:uppercase;letter-spacing:.05em;">Próximos (&lt;90 dias)</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Filters ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    pesq = st.text_input("🔍 Pesquisar", placeholder="Nome do medicamento...")
with c2:
    filtro = st.selectbox("Status", ["Todos", STATUS_VENCIDO, STATUS_ATENCAO, STATUS_PROXIMO])

alertas_filt = alertas
if pesq:
    alertas_filt = [a for a in alertas_filt if pesq.lower() in a.medicamento.lower()]
if filtro != "Todos":
    alertas_filt = [a for a in alertas_filt if a.status == filtro]

# ── Alert list ─────────────────────────────────────────────────────────────────
if not alertas_filt:
    st.success("✅ Nenhum alerta para os filtros selecionados.")
else:
    st.markdown(
        f'<p style="color:#94a3b8;font-size:0.85rem;margin-bottom:0.75rem;">'
        f'{len(alertas_filt)} alerta(s) encontrado(s)</p>',
        unsafe_allow_html=True,
    )

    for a in alertas_filt:
        if a.dias_para_vencer is not None and a.dias_para_vencer < 0:
            dias_txt = f"<b style='color:{a.cor};'>Vencido há {abs(a.dias_para_vencer)} dia(s)</b>"
        elif a.dias_para_vencer is not None:
            dias_txt = f"<b style='color:{a.cor};'>{a.dias_para_vencer} dia(s) restantes</b>"
        else:
            dias_txt = "—"

        st.markdown(f"""
        <div class="alert-card" style="border-left-color:{a.cor};">
            <div>
                <div style="font-weight:700;font-size:1rem;color:#f8fafc;">{a.medicamento}</div>
                <div style="color:#94a3b8;font-size:0.83rem;margin-top:3px;">
                    Lote: <b>{a.lote}</b> &nbsp;|&nbsp; Validade: <b>{a.data_vencimento}</b>
                    &nbsp;|&nbsp; {dias_txt}
                </div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
                <span class="status-badge"
                    style="background:{a.cor}20;color:{a.cor};border:1px solid {a.cor};">
                    {a.status}
                </span>
                <div style="color:#94a3b8;font-size:0.78rem;margin-top:5px;">Qtd: {a.quantidade}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
