import traceback
import streamlit as st
import streamlit.components.v1 as components
from utils.helpers import load_css
from utils.ui import icon
from utils.auth import exigir_login, login_ativo
from services.alerta_service import get_alertas, get_alertas_materiais, ordenar_alertas
from utils.components import notification_drawer

st.set_page_config(
    page_title="Controle de Enfermagem",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()
exigir_login()

paginas = {
    "pages/home.py":                  st.Page("pages/home.py",                  title="Página Inicial",        icon="🏠", default=True),
    "pages/dashboard.py":             st.Page("pages/dashboard.py",             title="Dashboard de Controle", icon="📊"),
    "pages/estoque.py":               st.Page("pages/estoque.py",               title="Estoque Geral",         icon="📦"),
    "pages/estoque_materiais.py":     st.Page("pages/estoque_materiais.py",     title="Estoque de Materiais",  icon="🧴"),
    "pages/cadastrar_medicamento.py": st.Page("pages/cadastrar_medicamento.py", title="Medicamentos",          icon="➕"),
    "pages/cadastrar_material.py":    st.Page("pages/cadastrar_material.py",    title="Materiais",             icon="🧴"),
    "pages/registrar_aplicacao.py":   st.Page("pages/registrar_aplicacao.py",   title="Registrar Aplicação",   icon="💉"),
    "pages/historico.py":             st.Page("pages/historico.py",             title="Relatórios",            icon="📊"),
    "pages/debug.py":                 st.Page("pages/debug.py",                 title="Debug",                 icon="🐞"),
}
pages = list(paginas.values())

pg = st.navigation(pages, position="hidden")

# Barra de navegação superior (estilos em assets/style.css, seção TOP NAV)
nav_items = [
    ("pages/home.py", "Página Inicial", "home"),
    ("pages/dashboard.py", "Dashboard de Controle", "layout-dashboard"),
    ("pages/estoque.py", "Estoque Geral", "boxes"),
    ("pages/cadastrar_medicamento.py", "Medicamentos", "pill"),
    ("pages/cadastrar_material.py", "Materiais", "package"),
    ("pages/registrar_aplicacao.py", "Aplicações", "syringe"),
    ("pages/historico.py", "Relatórios", "file-chart"),
]

try:
    _alertas = ordenar_alertas(get_alertas() + get_alertas_materiais())
except Exception:
    _alertas = []
_total_alertas = len(_alertas)

links_html = [
    '<nav class="top-nav">'
    f'<a class="logo" href="?page=pages/home.py" target="_self" data-nav="0">{icon("heart-pulse", 24)}'
    "<span>Controle de Enfermagem</span></a>"
    '<div class="nav-links">'
]
for i, (path, label, nome_icone) in enumerate(nav_items):
    ativo = " active" if paginas[path].url_path == pg.url_path else ""
    links_html.append(
        f'<a class="nav-link{ativo}" href="?page={path}" target="_self" data-nav="{i}">'
        f"{icon(nome_icone, 15)}<span>{label}</span></a>"
    )
links_html.append('</div><div class="nav-actions">')

badge = f'<span class="nav-badge">{min(_total_alertas, 99)}</span>' if _total_alertas else ""
links_html.append(
    f'<label class="nav-bell{" has-alerts" if _total_alertas else ""}" for="nt-toggle" '
    f'title="{_total_alertas} alerta(s) de validade">{icon("bell", 19)}{badge}</label>'
)
if login_ativo():
    links_html.append(
        '<div class="nav-user" tabindex="0">'
        '<span class="nav-avatar">EQ</span>'
        '<span class="nav-user-text"><b>Equipe</b><small>Enfermagem</small></span>'
        f'{icon("chevron-down", 15)}'
        '<div class="nav-menu">'
        f'<a class="nav-menu-item logout" href="?logout=1" target="_self">{icon("logout", 15)}<span>Sair</span></a>'
        "</div></div>"
    )
links_html.append("</div></nav>")
st.markdown("".join(links_html), unsafe_allow_html=True)
st.markdown(notification_drawer(_alertas), unsafe_allow_html=True)

# Os links acima recarregariam o navegador inteiro (nova sessão + switch_page = duas execuções).
# O script repassa o clique em a[data-nav] para o st.page_link oculto correspondente, que troca
# de página pela conexão já aberta. Sem o script, ou com Ctrl/clique do meio, vale o href normal.
with st.container(key="nav-shadow"):
    for i, (path, label, _) in enumerate(nav_items):
        with st.container(key=f"nav-shadow-{i}"):
            st.page_link(paginas[path], label=label)

components.html(
    """<script>
(function () {
  var d = window.parent.document;
  if (d.getElementById("cm-nav-js")) return;
  var s = d.createElement("script");
  s.id = "cm-nav-js";
  s.textContent = `document.addEventListener("click", function (ev) {
    if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var a = ev.target.closest && ev.target.closest(".top-nav a[data-nav]");
    if (!a) return;
    var alvo = document.querySelector(".st-key-nav-shadow-" + a.dataset.nav + " a");
    if (!alvo) return;
    ev.preventDefault();
    document.querySelectorAll(".top-nav .nav-link.active").forEach(function (l) { l.classList.remove("active"); });
    if (a.classList.contains("nav-link")) a.classList.add("active");
    alvo.click();
  }, true);`;
  d.head.appendChild(s);
})();
</script>""",
    height=0,
)

st.markdown('<div class="content-offset"></div>', unsafe_allow_html=True)

# Route to the page requested via ?page= query param
_qp_page = st.query_params.get('page', '')
if _qp_page and _qp_page.endswith('.py'):
    try:
        # Repassa os demais parâmetros (ex.: ?busca=) para a página de destino
        st.switch_page(_qp_page, query_params={k: v for k, v in st.query_params.items() if k != "page"})
    except Exception:
        pass

try:
    pg.run()
except Exception:
    st.error(
        "Não foi possível carregar a página. Verifique as configurações do Streamlit Cloud: "
        "`gcp_service_account`, `SPREADSHEET_ID` e as permissões da planilha."
    )
    st.code(traceback.format_exc())
    st.stop()

# ====================================================
# CSS FULLSCREEN
# ====================================================

st.markdown("""
<style>

#MainMenu {
    visibility: hidden;
}

header {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

[data-testid="stToolbar"] {
    display: none;
}

[data-testid="stDecoration"] {
    display: none;
}

[data-testid="stStatusWidget"] {
    display: none;
}

[data-testid="stHeader"] {
    display: none;
}

.block-container {
    padding: 0rem !important;
    margin: 0rem !important;
    max-width: 100% !important;
}

section.main > div {
    padding: 0rem !important;
}

iframe {
    border: none !important;
    width: 100% !important;
}

.stApp {
    background: #000000;
}

</style>
""", unsafe_allow_html=True)

# (Removed hardcoded iframes; each page should render its own content)