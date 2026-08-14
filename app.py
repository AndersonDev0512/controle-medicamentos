import streamlit as st
import streamlit.components.v1 as components
from utils.helpers import load_css

st.set_page_config(
    page_title="Controle de Medicamentos",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()

pages = [
    st.Page("pages/home.py",                   title="Página Inicial",       icon="🏠", default=True),
    st.Page("pages/dashboard.py",              title="Dashboard",             icon="📊"),
    st.Page("pages/estoque.py",                title="Estoque",               icon="📦"),
    st.Page("pages/cadastrar_medicamento.py",  title="Cadastrar Medicamento", icon="➕"),
    st.Page("pages/registrar_aplicacao.py",    title="Registrar Aplicação",   icon="💉"),
    st.Page("pages/historico.py",              title="Histórico",             icon="📜"),
    st.Page("pages/alertas.py",                title="Alertas",               icon="⚠️"),
    st.Page("pages/configuracoes.py",          title="Configurações",         icon="⚙️"),
    st.Page("pages/debug.py",                  title="Debug",                 icon="🐞"),
]

pg = st.navigation(pages, position="hidden")

# Top horizontal navigation bar using page links
nav_items = [
    ("pages/home.py", "🏠 Página Inicial"),
    ("pages/dashboard.py", "📊 Dashboard"),
    ("pages/estoque.py", "📦 Estoque"),
    ("pages/cadastrar_medicamento.py", "➕ Cadastrar Medicamento"),
    ("pages/registrar_aplicacao.py", "💉 Registrar Aplicação"),
    ("pages/historico.py", "📜 Histórico"),
    ("pages/alertas.py", "⚠️ Alertas"),
    ("pages/configuracoes.py", "⚙️ Configurações"),
]

# CSS for top nav (fixed) and spacing for main content
st.markdown(
    """
    <style>
    .top-nav {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: linear-gradient(90deg, #071228 0%, #052031 50%, #061827 100%);
        padding: 8px 22px;
        display: flex;
        align-items: center;
        gap: 18px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        box-shadow: 0 6px 20px rgba(2,6,23,0.6);
        overflow-x: auto;
        white-space: nowrap;
        border-left: 6px solid #6d28d9;
    }
    .top-nav::-webkit-scrollbar { height: 8px; }
    .top-nav::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.04); border-radius: 8px; }
    .top-nav .logo { display:flex; align-items:center; gap:12px; color:#f8fafc; font-weight:800; font-size:18px; }
    .top-nav .logo img { border-radius:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.5); }
    .top-nav .nav-link { color:#e6eef8; padding:10px 14px; border-radius:12px; text-decoration:none; display:inline-flex; align-items:center; gap:10px; font-weight:600; font-size:15px; background: rgba(255,255,255,0.01); }
    .top-nav .nav-link:hover { background: rgba(255,255,255,0.04); color:#fff; transform: translateY(-1px); transition: all 140ms cubic-bezier(.2,.9,.2,1); }
    .top-nav .nav-link.active { background: linear-gradient(90deg,#1e3a8a,#3b82f6); color:#fff; box-shadow: 0 8px 22px rgba(59,130,246,0.18); border-radius:14px; }
    .top-nav .nav-link .icon { font-size:18px; opacity:0.98; }
    .content-offset { padding-top: 18px; }
    @media (max-width: 900px){
        .top-nav { padding: 8px 12px; }
        .top-nav .nav-link { padding:8px 10px; font-size:14px; }
        .content-offset { padding-top: 10px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Render top nav using HTML anchors that will be enhanced with streamlit's page links below
links_html = ['<div class="top-nav">']
try:
    # try to show logo image
    from pathlib import Path
    if Path('assets/logo.png').exists():
        links_html.append('<div class="logo"><img src="assets/logo.png" height="36"/></div>')
    else:
        links_html.append('<div class="logo">💊 Controle de Medicamentos</div>')
except Exception:
    links_html.append('<div class="logo">💊 Controle de Medicamentos</div>')

for path, label in nav_items:
    links_html.append(f'<a class="nav-link" href="?page={path}" data-page="{path}" target="_self">{label}</a>')

# Render topbar HTML so CSS `.top-nav` applies to anchors
links_html.append('</div>')
st.markdown("".join(links_html), unsafe_allow_html=True)

st.markdown('<div class="content-offset"></div>', unsafe_allow_html=True)

# Small client-side script to mark the active nav item based on `?page=` query param
st.markdown(
    """
    <script>
    (function(){
        try{
            const params = new URLSearchParams(window.location.search);
            const p = params.get('page') || localStorage.getItem('cm_active_page') || 'pages/home.py';
            document.querySelectorAll('.top-nav .nav-link').forEach(a=>{
                a.classList.toggle('active', a.getAttribute('data-page')===p);
                a.addEventListener('click', ()=>{ try{ localStorage.setItem('cm_active_page', a.getAttribute('data-page')); }catch(e){} });
            });
        }catch(e){console.error(e)}
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

# Route to the page requested via ?page= query param
_qp_page = st.query_params.get('page', '')
if _qp_page and _qp_page.endswith('.py'):
    try:
        st.switch_page(_qp_page)
    except Exception:
        pass

pg.run()

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