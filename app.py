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

with st.sidebar:
    try:
        st.image("assets/logo.png", width=160)
    except Exception:
        st.markdown(
            '<div style="text-align:center;padding:.8rem 0 .4rem;">'
            '<span style="font-size:2.2rem;">💊</span>'
            '<div style="font-size:1rem;font-weight:700;margin-top:.3rem;color:#f8fafc;">'
            'Controle de<br>Medicamentos</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    st.page_link("pages/home.py",                  label="🏠  Página Inicial")
    st.page_link("pages/estoque.py",               label="📦  Estoque")
    st.page_link("pages/cadastrar_medicamento.py", label="➕  Cadastrar Medicamento")
    st.page_link("pages/registrar_aplicacao.py",   label="💉  Registrar Aplicação")
    st.page_link("pages/historico.py",             label="📜  Histórico")
    st.page_link("pages/alertas.py",               label="⚠️  Alertas")
    st.page_link("pages/configuracoes.py",         label="⚙️  Configurações")

    st.markdown("---")
    st.markdown(
        '<p style="color:#475569;font-size:.73rem;text-align:center;margin:0;">'
        'v1.0.0 · Google Sheets</p>',
        unsafe_allow_html=True,
    )

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