import streamlit as st
import streamlit.components.v1 as components

# ====================================================
# CONFIGURAÇÃO
# ====================================================

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed"
)

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