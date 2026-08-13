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
    st.Page("pages/estoque.py",                title="Estoque",               icon="📦"),
    st.Page("pages/cadastrar_medicamento.py",  title="Cadastrar Medicamento", icon="➕"),
    st.Page("pages/registrar_aplicacao.py",    title="Registrar Aplicação",   icon="💉"),
    st.Page("pages/historico.py",              title="Histórico",             icon="📜"),
    # Dashboard kept separate; not shown in main navigation
    st.Page("pages/alertas.py",                title="Alertas",               icon="⚠️"),
    st.Page("pages/configuracoes.py",          title="Configurações",         icon="⚙️"),
    st.Page("pages/debug.py",                  title="Debug",                 icon="🐞"),
]

pg = st.navigation(pages, position="hidden")

# Top horizontal navigation bar using page links
nav_items = [
    ("pages/home.py", "🏠 Página Inicial"),
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
        background: linear-gradient(90deg, #071228, #0b2333);
        padding: 8px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    .top-nav .logo { display:flex; align-items:center; gap:8px; color:#f8fafc; font-weight:700; }
    .top-nav .nav-link { color:#cbd5e1; padding:8px 12px; border-radius:6px; text-decoration:none; }
    .top-nav .nav-link:hover { background: rgba(255,255,255,0.03); color:#fff; }
    .content-offset { padding-top: 68px; }
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
    # make anchor navigate by setting query param ?page=...
    links_html.append(f'<a class="nav-link" href="?page={path}" data-page="{path}">{label}</a>')

links_html.append('</div>')
st.markdown("".join(links_html), unsafe_allow_html=True)

# JavaScript to persist active page highlight and set active on load
st.markdown(
    """
    <script>
    (function(){
        function setActive(page){
            document.querySelectorAll('.top-nav .nav-link').forEach(function(a){
                a.classList.toggle('active', a.getAttribute('data-page') === page);
            });
        }

        // On click, remember clicked page in localStorage
        document.querySelectorAll('.top-nav .nav-link').forEach(function(a){
            a.addEventListener('click', function(){
                try{ localStorage.setItem('cm_active_page', a.getAttribute('data-page')); }catch(e){}
            });
        });

        // On load, determine active page from query string or localStorage
        var params = new URLSearchParams(window.location.search);
        var p = params.get('page') || (localStorage.getItem('cm_active_page')) || '';
        if(p){ setActive(p); }
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="content-offset"></div>', unsafe_allow_html=True)

# run navigation after rendering nav
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

# ====================================================
# PLANILHA (TELA 1)
# ====================================================

components.html(
    """
    <iframe
        src="https://docs.google.com/spreadsheets/d/12MFBwvjJmwvtJj2I3GzqWluh8NpYrFYK7oXQFHNryqU/edit?usp=sharing"
        style="
            width:100vw;
            height:100vh;
            border:none;
            margin:0;
            padding:0;
        "
        allowfullscreen>
    </iframe>
    """,
    height=1000
)

# ====================================================
# LOOKER (TELA 2)
# ====================================================

components.html(
    """
    <iframe
        src="https://lookerstudio.google.com/embed/reporting/31bc0f2d-27e1-466f-8759-8d73ff05c5cf/page/aoNyF"
        style="
            width:100vw;
            height:100vh;
            border:none;
            margin:0;
            padding:0;
        "
        allowfullscreen>
    </iframe>
    """,
    height=1000
)