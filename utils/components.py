"""Componentes visuais em HTML (estilos em assets/style.css, prefixo ``hm-``).

Cada função recebe os dados prontos e devolve uma string HTML para ``st.html``.
Todo texto vindo da planilha passa por ``html.escape``. Ícones vêm de ``utils.ui.icon``
(máscaras CSS, porque ``st.html`` remove ``<svg>``).
"""
from __future__ import annotations

import html
from urllib.parse import quote

from services.alerta_service import Alerta
from utils.constants import STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK
from utils.ui import icon

e = html.escape

# Faixas de validade conforme utils/constants.py (DIAS_CRITICO=15, DIAS_ATENCAO=89, DIAS_PROXIMO=120).
SEVERIDADE = {
    STATUS_VENCIDO: {"cor": "#CBD5E1", "badge": "#B91C1C", "icone": "x-circle", "rotulo": "Vencido", "faixa": "Prazo expirado"},
    STATUS_CRITICO: {"cor": "#EF4444", "badge": "#EF4444", "icone": "octagon", "rotulo": "Crítico", "faixa": "até 15 dias"},
    STATUS_ATENCAO: {"cor": "#F97316", "badge": "#F59E0B", "icone": "triangle", "rotulo": "Atenção", "faixa": "16 a 89 dias"},
    STATUS_PROXIMO: {"cor": "#EAB308", "badge": "#3B82F6", "icone": "hourglass", "rotulo": "Próximo", "faixa": "90 a 120 dias"},
    STATUS_OK: {"cor": "#22C55E", "badge": "#22C55E", "icone": "check", "rotulo": "OK", "faixa": "mais de 120 dias"},
}
ORDEM_ALERTA = (STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO)


def sev(status: str) -> dict:
    return SEVERIDADE.get(status, SEVERIDADE[STATUS_OK])


def prazo_texto(dias: int | None) -> str:
    if dias is None:
        return "Sem data"
    if dias < 0:
        return f"Vencido há {abs(dias)} dia(s)"
    if dias == 0:
        return "Vence hoje"
    return f"Vence em {dias} dia(s)"


def page_link(pagina: str, **params: str) -> str:
    """Link no mesmo padrão da barra do topo (?page=...), que o app.py encaminha via switch_page."""
    extra = "".join(f"&{k}={quote(str(v))}" for k, v in params.items() if v)
    return f"?page={pagina}{extra}"


def status_badge(status: str, solido: bool = False) -> str:
    s = sev(status)
    if solido:
        return f'<span class="hm-badge-solid" style="--c:{s["badge"]}">{e(s["rotulo"])}</span>'
    return f'<span class="hm-badge" style="--c:{s["cor"]}"><i></i>{e(s["rotulo"])}</span>'


def section_header(nome_icone: str, titulo: str, subtitulo: str = "", extra: str = "") -> str:
    sub = f"<p>{e(subtitulo)}</p>" if subtitulo else ""
    return (
        f'<div class="hm-section"><div class="hm-section-icon">{icon(nome_icone, 20)}</div>'
        f'<div class="hm-section-text"><h2>{e(titulo)}</h2>{sub}</div>{extra}</div>'
    )


def empty_state(nome_icone: str, cor: str, titulo: str, texto: str) -> str:
    return (
        f'<div class="hm-empty" style="--c:{cor}">{icon(nome_icone, 26)}'
        f"<div><b>{e(titulo)}</b><span>{e(texto)}</span></div></div>"
    )


def sparkbars(valores: list[int], rotulos: list[str]) -> str:
    """Mini gráfico de barras em CSS (st.html não aceita SVG). Só para séries reais."""
    maior = max(valores) if valores and max(valores) > 0 else 0
    barras = "".join(
        f'<span style="height:{(v / maior * 100) if maior else 0:.0f}%" title="{e(r)}: {v}"></span>'
        for v, r in zip(valores, rotulos)
    )
    return f'<div class="hm-spark" aria-hidden="true">{barras}</div>'


def kpi_card(nome_icone: str, cor: str, titulo: str, valor: object, detalhe: str,
             href: str = "", rotulo_link: str = "", grafico: str = "") -> str:
    """``detalhe`` já vem em HTML (pode conter <b>); os demais textos são escapados."""
    seta = (
        f'<a class="hm-kpi-go" href="{e(href)}" target="_self" title="{e(rotulo_link)}" aria-label="{e(rotulo_link)}">'
        f'{icon("arrow", 15)}</a>'
        if href else ""
    )
    return (
        f'<div class="hm-kpi" style="--c:{cor}">{seta}'
        f'<div class="hm-kpi-icon">{icon(nome_icone, 28)}</div>'
        f'<div class="hm-kpi-body"><span class="hm-kpi-title">{e(titulo)}</span>'
        f'<strong class="hm-kpi-value">{e(str(valor))}</strong>'
        f'<span class="hm-kpi-detail">{detalhe}</span></div>{grafico}</div>'
    )


def validity_panel(titulo: str, nome_icone: str, contagens: dict[str, int]) -> str:
    """``contagens``: {status: quantidade} para as cinco faixas."""
    total = sum(contagens.values())
    ordem = (STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK)
    segmentos = "".join(
        f'<span style="flex:{contagens.get(s, 0)};background:{sev(s)["cor"]}" '
        f'title="{sev(s)["rotulo"]}: {contagens.get(s, 0)}"></span>'
        for s in ordem
        if contagens.get(s, 0)
    ) or '<span style="flex:1;background:#334155" title="Sem lotes"></span>'
    linhas = "".join(
        f'<div class="hm-legend-row" style="--c:{sev(s)["cor"]}">'
        f'<span class="hm-legend-name"><i></i>{sev(s)["rotulo"]}<small>{sev(s)["faixa"]}</small></span>'
        f'<span class="hm-legend-qtd">{contagens.get(s, 0)}</span>'
        f'<span class="hm-legend-pct">{(contagens.get(s, 0) / total * 100 if total else 0):.0f}%</span></div>'
        for s in ordem
    )
    seguro = (contagens.get(STATUS_OK, 0) / total * 100) if total else 0
    return (
        '<div class="hm-panel">'
        f'<div class="hm-panel-head"><div class="hm-panel-icon">{icon(nome_icone, 20)}</div>'
        f"<div><h3>{e(titulo)}</h3><p>{total} lote(s) monitorado(s) · {seguro:.0f}% dentro da validade segura</p></div></div>"
        f'<div class="hm-stackbar" role="img" aria-label="Distribuição de {e(titulo)} por validade">{segmentos}</div>'
        f'<div class="hm-legend">{linhas}</div></div>'
    )


def recent_alert(a: Alerta) -> str:
    s = sev(a.status)
    icone = "package" if a.tipo == "Material" else "pill"
    if a.dias_para_vencer is not None and a.dias_para_vencer < 0:
        quando = f"Venceu em {e(a.data_vencimento)}"
    else:
        quando = f"Vence em {e(a.data_vencimento or '—')}"
    return (
        f'<div class="hm-recent" style="--c:{s["cor"]}">'
        f'<div class="hm-recent-icon">{icon(icone, 18)}</div>'
        f'<div class="hm-recent-main"><b>{e(a.medicamento)}</b>'
        f'<span>{e(a.tipo)} · Lote: {e(a.lote or "—")} | {quando}</span></div>'
        f"{status_badge(a.status, solido=True)}</div>"
    )


def alert_row(a: Alerta) -> str:
    s = sev(a.status)
    dias = "—" if a.dias_para_vencer is None else str(a.dias_para_vencer)
    pagina = "pages/estoque_materiais.py" if a.tipo == "Material" else "pages/estoque.py"
    busca = a.lote if a.lote and a.lote.strip() else a.medicamento
    acao = (
        f'<a class="hm-row-action" href="{e(page_link(pagina, busca=busca))}" target="_self" '
        f'title="Consultar no estoque" aria-label="Consultar {e(a.medicamento)} no estoque">{icon("eye", 16)}</a>'
    )
    return (
        "<tr>"
        f'<td data-label="Produto"><b>{e(a.medicamento)}</b></td>'
        f'<td data-label="Tipo">{e(a.tipo)}</td>'
        f'<td data-label="Lote"><code class="hm-lote">{e(a.lote or "—")}</code></td>'
        f'<td data-label="Validade">{e(a.data_vencimento or "—")}</td>'
        f'<td data-label="Dias restantes" class="hm-dias" style="--c:{s["cor"]}" title="{prazo_texto(a.dias_para_vencer)}">{dias}</td>'
        f'<td data-label="Status">{status_badge(a.status)}</td>'
        f'<td data-label="Ações" class="hm-acoes">{acao}</td>'
        "</tr>"
    )


def alerts_table(alertas: list[Alerta]) -> str:
    return (
        '<div class="hm-table-wrap hm-table-scroll"><table class="hm-table"><thead><tr>'
        "<th>Produto</th><th>Tipo</th><th>Lote</th><th>Validade</th><th>Dias restantes</th><th>Status</th><th>Ações</th>"
        f'</tr></thead><tbody>{"".join(alert_row(a) for a in alertas)}</tbody></table></div>'
    )


def quick_action(nome_icone: str, rotulo: str, href: str, cor: str) -> str:
    return (
        f'<a class="hm-quick" href="{e(href)}" target="_self" style="--c:{cor}">'
        f"{icon(nome_icone, 20)}<span>{e(rotulo)}</span></a>"
    )


def _numero(valor: float, casas: int = 0) -> str:
    """Número no formato brasileiro (1.234 / 12,5), sem zeros decimais sobrando."""
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto.rstrip("0").rstrip(",") if casas and "," in texto else texto


def stock_summary(df, total_geral: int, item: str) -> str:
    """Resumo do resultado filtrado no estoque: validade (barra + legenda) e números-chave.

    ``df`` é o DataFrame filtrado com Status canônico; ``item`` é "medicamentos" ou "materiais".
    """
    import pandas as pd
    from utils.constants import CARRINHO_SIM

    ordem = (STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK)
    contagens = {s: int((df["Status"] == s).sum()) for s in ordem} if not df.empty else dict.fromkeys(ordem, 0)
    unidades = pd.to_numeric(df.get("Quantidade"), errors="coerce").fillna(0).sum() if not df.empty else 0
    saldo = (
        pd.to_numeric(df["Saldo Aberto"], errors="coerce").fillna(0).sum()
        if "Saldo Aberto" in df.columns and not df.empty else 0
    )
    carrinho = int((df["Carrinho de Parada"] == CARRINHO_SIM).sum()) if "Carrinho de Parada" in df.columns else 0
    urgentes = contagens[STATUS_VENCIDO] + contagens[STATUS_CRITICO]

    if saldo:
        detalhe_unid = f"+ {_numero(saldo, 2)} em frações abertas"
    else:
        detalhe_unid = "unidades fechadas" if "Saldo Aberto" in df.columns else "unidades em estoque"
    tiles = [
        ("boxes", "#3B82F6", "Lotes", _numero(len(df)), f"de {_numero(total_geral)} cadastrados", ""),
        ("package", "#06B6D4", "Unidades", _numero(unidades), detalhe_unid, ""),
        ("triangle", "#EF4444" if urgentes else "#22C55E", "Ação imediata", _numero(urgentes),
         "vencidos ou críticos" if urgentes else "nenhum vencido ou crítico", " is-alert" if urgentes else ""),
        ("heart-pulse", "#F43F5E", "Carrinho de Parada", _numero(carrinho), "lotes no carrinho", ""),
    ]
    stats = "".join(
        f'<div class="st-tile{extra}" style="--c:{cor}">'
        f'<span class="st-tile-icon">{icon(ico, 18)}</span>'
        f'<div><span class="st-tile-label">{e(rotulo)}</span><strong>{e(valor)}</strong>'
        f'<small>{e(detalhe)}</small></div></div>'
        for ico, cor, rotulo, valor, detalhe, extra in tiles
    )
    return (
        '<div class="st-summary">'
        + validity_panel(f"Validade dos {item} filtrados", "shield", contagens)
        + f'<div class="st-tiles">{stats}</div></div>'
    )


NOTIF_LIMITE = 60


def notification_drawer(alertas: list[Alerta]) -> str:
    """Painel lateral de notificações aberto pelo sino da barra do topo.

    Sem JS: o sino é um ``<label for="nt-toggle">`` que marca o checkbox; os rádios
    ``nt-f-*`` filtram por status. Estilos em assets/style.css (seção NOTIFICAÇÕES).
    """
    contagem = {s: sum(1 for a in alertas if a.status == s) for s in ORDEM_ALERTA}
    radios = '<input type="radio" name="nt-f" id="nt-f-all" class="nt-radio" checked>' + "".join(
        f'<input type="radio" name="nt-f" id="nt-f-{i}" class="nt-radio">' for i in range(len(ORDEM_ALERTA))
    )
    filtros = f'<label for="nt-f-all" class="nt-chip nt-chip-all">Todos <b>{len(alertas)}</b></label>' + "".join(
        f'<label for="nt-f-{i}" class="nt-chip nt-chip-{i}" style="--c:{sev(s)["cor"]}">'
        f'{sev(s)["rotulo"]} <b>{contagem[s]}</b></label>'
        for i, s in enumerate(ORDEM_ALERTA)
        if contagem[s]
    )

    itens = []
    for n, a in enumerate(alertas[:NOTIF_LIMITE]):
        s = sev(a.status)
        idx = ORDEM_ALERTA.index(a.status) if a.status in ORDEM_ALERTA else len(ORDEM_ALERTA)
        pagina = "pages/estoque_materiais.py" if a.tipo == "Material" else "pages/estoque.py"
        busca = a.lote if a.lote and a.lote.strip() else a.medicamento
        itens.append(
            f'<a class="nt-item nt-s{idx}" href="{e(page_link(pagina, busca=busca))}" target="_self" '
            f'style="--c:{s["cor"]};--i:{min(n, 12)}">'
            f'<span class="nt-item-icon">{icon(s["icone"], 18)}</span>'
            f'<span class="nt-item-main"><b>{e(a.medicamento)}</b>'
            f'<small>{icon("package" if a.tipo == "Material" else "pill", 12)} {e(a.tipo)} · Lote {e(a.lote or "—")}</small>'
            f'<em>{e(prazo_texto(a.dias_para_vencer))} · {e(a.data_vencimento or "—")}</em></span>'
            f'<span class="nt-item-tag">{e(s["rotulo"])}</span></a>'
        )
    restante = len(alertas) - NOTIF_LIMITE
    mais = f'<p class="nt-more">+{restante} alerta(s) na central</p>' if restante > 0 else ""

    if alertas:
        corpo = f'<div class="nt-filters">{filtros}</div><div class="nt-list">{"".join(itens)}{mais}</div>'
        sub = f"{len(alertas)} lote(s) exigem atenção"
    else:
        corpo = f'<div class="nt-empty">{icon("bell", 52)}<span>Nenhuma notificação</span></div>'
        sub = "Tudo em dia com as validades"

    return (
        '<div class="nt-root">'
        '<input type="checkbox" id="nt-toggle" class="nt-toggle" aria-label="Abrir notificações">'
        f"{radios}"
        '<label for="nt-toggle" class="nt-backdrop" aria-hidden="true"></label>'
        '<aside class="nt-panel" role="dialog" aria-label="Notificações">'
        '<div class="nt-head"><div><h3>Notificações</h3>'
        f"<p>{e(sub)}</p></div>"
        f'<label for="nt-toggle" class="nt-close" title="Fechar">{icon("x", 18)}</label></div>'
        f"{corpo}"
        f'<a class="nt-foot" href="{page_link("pages/home.py")}" target="_self">'
        f'Abrir central de alertas {icon("arrow", 15)}</a>'
        "</aside></div>"
    )


def cart_kpi(df, item: str) -> str:
    """KPI do Carrinho de Parada para um DataFrame de estoque (medicamentos ou materiais).

    Conta os lotes com "Carrinho de Parada" = S, as unidades e a validade desses lotes.
    ``item`` é o nome no plural usado nos textos ("medicamentos" ou "materiais").
    """
    import pandas as pd

    from utils.constants import CARRINHO_SIM

    if df.empty or "Carrinho de Parada" not in df.columns:
        carrinho = df.iloc[0:0]
    else:
        carrinho = df[df["Carrinho de Parada"] == CARRINHO_SIM]
    lotes = len(carrinho)
    unidades = int(pd.to_numeric(carrinho.get("Quantidade", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    ordem = (STATUS_VENCIDO, STATUS_CRITICO, STATUS_ATENCAO, STATUS_PROXIMO, STATUS_OK)
    contagem = {s: int((carrinho["Status"] == s).sum()) if lotes else 0 for s in ordem}
    urgentes = contagem[STATUS_VENCIDO] + contagem[STATUS_CRITICO]

    chips = "".join(
        f'<span class="hm-count" style="--c:{sev(s)["cor"]}">{contagem[s]} {sev(s)["rotulo"]}</span>'
        for s in ordem
    )
    if not lotes:
        aviso = (
            f'<p class="cp-hint">Nenhum lote de {e(item)} marcado. '
            "Use <b>Carrinho de Parada? = Sim</b> no cadastro ou na edição.</p>"
        )
    elif urgentes:
        aviso = (
            f'<p class="cp-alert">{icon("triangle", 15)} {urgentes} lote(s) vencido(s) ou crítico(s) '
            "no carrinho: substitua com prioridade.</p>"
        )
    else:
        aviso = f'<p class="cp-ok">{icon("check", 15)} Nenhum lote vencido ou crítico no carrinho.</p>'

    return (
        '<div class="cp-kpi">'
        f'<div class="cp-icon">{icon("heart-pulse", 28)}</div>'
        '<div class="cp-body"><span class="cp-title">Carrinho de Parada</span>'
        f'<div class="cp-value"><strong>{lotes}</strong><span>lote(s) de {e(item)} · {unidades} unidade(s)</span></div>'
        f"{aviso}</div>"
        f'<div class="cp-chips">{chips}</div>'
        "</div>"
    )
