import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Esconde tudo do Streamlit
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

section.main > div {
    padding-top: 0rem;
    padding-bottom: 0rem;
}

.block-container {
    padding: 0rem !important;
    margin: 0rem !important;
    max-width: 100% !important;
}

iframe {
    border: none;
}

</style>
""", unsafe_allow_html=True)

# PLANILHA
components.iframe(
    src="https://docs.google.com/spreadsheets/d/12MFBwvjJmwvtJj2I3GzqWluh8NpYrFYK7oXQFHNryqU/edit?usp=sharing",
    height=900,
    scrolling=True
)

# LOOKER
components.iframe(
    src="https://datastudio.google.com/embed/reporting/31bc0f2d-27e1-466f-8759-8d73ff05c5cf/page/aoNyF",
    height=2000,
    scrolling=True
)