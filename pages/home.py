from __future__ import annotations

import html
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from services.alerta_service import get_alertas, get_alertas_materiais, ordenar_alertas
from services.dashboard_service import get_chart_aplicacoes_diarias, get_kpis, get_kpis_materiais
from services.estoque_service import get_estoque
from services.estoque_service import get_materiais
from services.sheets_service import ler_materiais
from utils.assets import static_url
from utils.components import (
    ORDEM_ALERTA,
    alerts_table,
    empty_state,
    kpi_card,
    page_link,
    prazo_texto,
    quick_action,
    recent_alert,
    report_shortcut,
    section_header,
    sev,
    sparkbars,
    status_badge,
    validity_panel,
)
from utils.config import get_config
from utils.constants import CARRINHO_SIM, STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK
from utils.helpers import formatar_data_hora, normalize_status, safe_int
from utils.ui import icon

e = html.escape

_ALERTAS_RECENTES = 5
_DIAS_SPARK = 14


def contagens_validade(k: dict) -> dict[str, int]:
    return {
        STATUS_VENCIDO: k.get("vencidos", 0),
        STATUS_CRITICO: k.get("critico", 0),
        STATUS_ATENCAO: k.get("atencao", 0),
        STATUS_PROXIMO: k.get("proximos", 0),
        STATUS_OK: k.get("ok", 0),
    }


def serie_aplicacoes(dias: int) -> tuple[list[int], list[str]]:
    """Aplicações por dia nos últimos ``dias`` dias (zeros onde não houve registro)."""
    df = get_chart_aplicacoes_diarias()
    por_dia = {}
    if not df.empty:
        datas = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
        por_dia = {d.date(): int(q) for d, q in zip(datas, df["Aplicações"]) if pd.notna(d)}
    hoje = date.today()
    janela = [hoje - timedelta(days=i) for i in range(dias - 1, -1, -1)]
    return [por_dia.get(d, 0) for d in janela], [d.strftime("%d/%m") for d in janela]


def tabela_ultimos(df: pd.DataFrame) -> str:
    linhas = []
    for _, row in df.iterrows():
        status = normalize_status(row.get("Status"))
        s = sev(status)
        dias = row.get("Dias para Vencer")
        dias = None if dias is None or pd.isna(dias) else int(dias)
        unidade = e(str(row.get("Unidade de Medida", "") or ""))
        linhas.append(
            "<tr>"
            f'<td data-label="Medicamento"><div class="hm-cell-med"><span class="hm-cell-dot" style="--c:{s["cor"]}">{icon("pill", 15)}</span>'
            f'<b>{e(str(row.get("Medicamento", "")))}</b></div></td>'
            f'<td data-label="Quantidade" class="hm-num"><b>{safe_int(row.get("Quantidade", 0))}</b> <small>{unidade}</small></td>'
            f'<td data-label="Lote"><code class="hm-lote">{e(str(row.get("Lote", "") or "—"))}</code></td>'
            f'<td data-label="Vencimento">{e(str(row.get("Data de Vencimento", "") or "—"))}</td>'
            f'<td data-label="Prazo" class="hm-prazo-cell" style="--c:{s["cor"]}">{prazo_texto(dias)}</td>'
            f'<td data-label="Status">{status_badge(status)}</td>'
            "</tr>"
        )
    return (
        '<div class="hm-table-wrap"><table class="hm-table"><thead><tr>'
        "<th>Medicamento</th><th>Quantidade</th><th>Lote</th><th>Vencimento</th><th>Prazo</th><th>Status</th>"
        f'</tr></thead><tbody>{"".join(linhas)}</tbody></table></div>'
    )


# ── Dados ─────────────────────────────────────────────────────────────────────
kpis = get_kpis()
kpis_m = get_kpis_materiais()
alertas = ordenar_alertas(get_alertas() + get_alertas_materiais())
df = get_estoque()
config = get_config()
agora = formatar_data_hora()  # America/Cuiaba (utils/helpers.py)
data_hoje, hora_agora = agora.split(" ")

total_med = kpis.get("total_medicamentos", 0)
total_mat = kpis_m.get("total", 0)
por_status = {s: sum(1 for a in alertas if a.status == s) for s in ORDEM_ALERTA}

# Situação operacional e estado da leitura da planilha
if por_status[STATUS_VENCIDO] or por_status[STATUS_CRITICO]:
    situacao = ("#EF4444", "Requer ação imediata")
elif alertas:
    situacao = ("#F59E0B", "Itens em observação")
else:
    situacao = ("#22C55E", "Estoque em conformidade")

try:
    tem_dados = not df.empty or not ler_materiais().empty
    sync = ("#22C55E", "Google Sheets conectado") if tem_dados else ("#F59E0B", "Planilha sem registros")
except Exception:
    sync = ("#94A3B8", "Status da planilha desconhecido")

# ── Hero ──────────────────────────────────────────────────────────────────────
hero_img = static_url("clinical-hero.webp")
hero_style = f' style="--hero-img:url(\'{hero_img}\')"' if hero_img else ""
pilares = "".join(
    f'<span class="hm-pilar">{icon(i, 20)}<small>{t}</small></span>'
    for i, t in (
        ("shield-check", "Segurança<br>no cuidado"),
        ("package", "Controle<br>de estoque"),
        ("heart-pulse", "Qualidade<br>na assistência"),
    )
)
st.html(
    f'<section class="hm-hero"{hero_style}>'
    '<div class="hm-hero-brand">'
    f'<div class="hm-hero-logo">{icon("pill", 34)}</div>'
    f'<div class="hm-hero-text"><span class="hm-eyebrow">{e(config.clinic_name)}</span>'
    "<h1>Controle de Enfermagem</h1>"
    "<p>Medicamentos, materiais e aplicações monitorados em um só lugar.</p>"
    f'<div class="hm-pilares">{pilares}</div></div></div>'
    '<blockquote class="hm-quote">“Cuidar é administrar com responsabilidade.”'
    "<small>Enfermagem · base para um futuro mais seguro</small></blockquote>"
    '<div class="hm-status">'
    f'<div class="hm-status-head">{icon("calendar-clock", 20)}<div><span>Cuiabá · {e(data_hoje)}</span><b>{e(hora_agora)}</b></div></div>'
    f'<div class="hm-status-row" style="--c:{sync[0]}"><i></i>{e(sync[1])}</div>'
    f'<div class="hm-status-row" style="--c:{situacao[0]}"><i></i>{e(situacao[1])}</div>'
    "</div></section>"
)

# ── KPIs ──────────────────────────────────────────────────────────────────────
serie, rotulos = serie_aplicacoes(_DIAS_SPARK)

# Carrinho de Parada: lotes marcados "S" em medicamentos e materiais
df_mat = get_materiais()
car_med = df[df["Carrinho de Parada"] == CARRINHO_SIM] if not df.empty else df
car_mat = df_mat[df_mat["Carrinho de Parada"] == CARRINHO_SIM] if not df_mat.empty else df_mat
car_urgentes = sum(int(c["Status"].isin([STATUS_VENCIDO, STATUS_CRITICO]).sum()) for c in (car_med, car_mat) if not c.empty)
car_total = len(car_med) + len(car_mat)
car_validade = {
    st_: sum(int((c["Status"] == st_).sum()) for c in (car_med, car_mat) if not c.empty)
    for st_ in (STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK)
}
if not car_total:
    car_detalhe = "Nenhum lote marcado no carrinho"
elif car_urgentes:
    car_detalhe = (f'{len(car_med)} medicamento(s) · {len(car_mat)} material(is) · '
                   f'<b class="hm-red">{car_urgentes} vencido(s)/crítico(s)</b>')
else:
    car_detalhe = f"{len(car_med)} medicamento(s) · {len(car_mat)} material(is) · nenhum vencido/crítico"
st.html(
    '<div class="hm-kpis">'
    + kpi_card("pill", "#3B82F6", "Medicamentos", total_med,
               f'{kpis.get("quantidade_total", 0)} unidade(s) em estoque',
               href=page_link("pages/estoque.py"), rotulo_link="Abrir estoque de medicamentos")
    + kpi_card("package", "#10B981", "Materiais", total_mat,
               f'{kpis_m.get("ok", 0)} lote(s) com validade segura',
               href=page_link("pages/estoque_materiais.py"), rotulo_link="Abrir estoque de materiais")
    + kpi_card("syringe", "#8B5CF6", "Aplicações hoje", kpis.get("aplicacoes_hoje", 0),
               f"Registradas no dia · {sum(serie)} nos últimos {_DIAS_SPARK} dias",
               href=page_link("pages/registrar_aplicacao.py"), rotulo_link="Registrar aplicação",
               grafico=sparkbars(serie, rotulos) if any(serie) else "")
    + kpi_card("bell", "#EF4444", "Alertas ativos", len(alertas),
               f'<b class="hm-red">{por_status[STATUS_CRITICO]} crítico(s)</b> · '
               f'<b class="hm-red">{por_status[STATUS_VENCIDO]} vencido(s)</b>',
               href="#central-alertas", rotulo_link="Ir para a Central de alertas")
    + kpi_card("heart-pulse", "#F43F5E", "Carrinho de Parada", car_total, car_detalhe,
               href=page_link("pages/estoque.py", carrinho="1"), rotulo_link="Ver itens do Carrinho de Parada no estoque")
    + "</div>"
)

# ── Situação de validade + Alertas recentes ──────────────────────────────────
if alertas:
    recentes = "".join(recent_alert(a) for a in alertas[:_ALERTAS_RECENTES])
else:
    recentes = empty_state("check", "#22C55E", "Nenhum alerta de validade",
                           "Nenhum alerta de validade encontrado no momento.")
ver_todos = (
    f'<a class="hm-link-inline" href="#central-alertas">Ver todos {icon("arrow", 14)}</a>' if alertas else ""
)
st.html(
    '<div class="hm-row hm-row-validade">'
    '<div class="hm-card-section">'
    + section_header("calendar-clock", "Situação de validade", "Distribuição dos lotes por faixa de vencimento")
    + '<div class="hm-panels">'
    + validity_panel("Medicamentos", "pill", contagens_validade(kpis))
    + validity_panel("Materiais", "package", contagens_validade(kpis_m))
    + validity_panel("Carrinho de Parada", "heart-pulse", car_validade)
    + "</div></div>"
    '<div class="hm-card-section hm-recents">'
    + section_header("bell", "Alertas recentes", "", ver_todos)
    + f'<div class="hm-recent-list">{recentes}</div></div>'
    "</div>"
)

# ── Central de alertas + Ações rápidas ───────────────────────────────────────
contadores = "".join(
    f'<span class="hm-count" style="--c:{sev(s)["cor"]}">{por_status[s]} {sev(s)["rotulo"]}</span>'
    for s in ORDEM_ALERTA
)
if alertas:
    corpo_central = alerts_table(alertas)
else:
    corpo_central = empty_state("check", "#22C55E", "Nenhum alerta de validade",
                                "Todos os lotes estão com mais de 120 dias de validade.")
acoes = "".join((
    quick_action("syringe", "Registrar aplicação", page_link("pages/registrar_aplicacao.py"), "#2563EB"),
    quick_action("boxes", "Consultar estoque", page_link("pages/estoque.py"), "#06B6D4"),
    quick_action("plus", "Novo medicamento", page_link("pages/cadastrar_medicamento.py"), "#8B5CF6"),
    quick_action("plus", "Novo material", page_link("pages/cadastrar_material.py"), "#10B981"),
))
_hoje = date.today()
_rel = "pages/historico.py"
relatorios = "".join((
    report_shortcut("calendar", "Aplicações do mês", f"{_hoje.replace(day=1):%d/%m} a {_hoje:%d/%m}",
                    page_link(_rel, rel="aplicacoes", periodo="mes"), "#3B82F6"),
    report_shortcut("clock", "Aplicações da semana", "Últimos 7 dias",
                    page_link(_rel, rel="aplicacoes", periodo="semana"), "#06B6D4"),
    report_shortcut("pill", "Estoque de medicamentos", "Inventário completo em PDF",
                    page_link(_rel, rel="estoque", inv="medicamentos"), "#8B5CF6"),
    report_shortcut("package", "Estoque de materiais", "Inventário completo em PDF",
                    page_link(_rel, rel="estoque", inv="materiais"), "#10B981"),
    report_shortcut("x-circle", "Lotes vencidos", "Medicamentos para descarte",
                    page_link(_rel, rel="estoque", inv="medicamentos", status=STATUS_VENCIDO), "#EF4444"),
    report_shortcut("report", "Relatório personalizado", "Escolha período, filtros e campos",
                    page_link(_rel), "#F59E0B"),
))
st.html(
    '<div class="hm-row hm-row-central">'
    '<div class="hm-card-section" id="central-alertas">'
    + section_header("bell", "Central de alertas",
                     "Lotes vencidos ou próximos do vencimento, do mais urgente ao menos urgente",
                     f'<div class="hm-counts">{contadores}</div>')
    + corpo_central
    + "</div>"
    '<div class="hm-card-section hm-quick-section">'
    + section_header("activity", "Ações rápidas", "Acesso direto às principais funcionalidades")
    + f'<div class="hm-quick-grid">{acoes}</div>'
    + f'<div class="hm-reports"><span class="hm-reports-title">{icon("file-chart", 15)}Relatórios</span>'
    + f'<div class="hm-reports-grid">{relatorios}</div></div></div>'
    "</div>"
)

# ── Últimos medicamentos ──────────────────────────────────────────────────────
st.html(
    '<div class="hm-card-section">'
    + section_header("table", "Últimos medicamentos cadastrados", "Os 15 lotes mais recentes do estoque",
                     f'<a class="hm-link" href="{page_link("pages/estoque.py")}" target="_self">Ver estoque completo '
                     + icon("arrow", 15) + "</a>")
    + (empty_state("pill", "#3B82F6", "Nenhum medicamento cadastrado", "Cadastre o primeiro lote em Medicamentos.")
       if df.empty else tabela_ultimos(df.tail(15).iloc[::-1]))
    + "</div>"
)

# ── Rodapé ────────────────────────────────────────────────────────────────────
st.html(
    '<footer class="hm-footer">'
    '<span class="hm-footer-quote">“Tecnologia a serviço da vida.”<i></i></span>'
    f'<span class="hm-online" style="--c:{sync[0]}"><i></i>{e(sync[1])}</span>'
    f"<span>Atualizado em <b>{e(agora)}</b></span>"
    f'<span class="hm-footer-brand">{e(config.clinic_name)} | Controle de Enfermagem</span>'
    "</footer>"
)
