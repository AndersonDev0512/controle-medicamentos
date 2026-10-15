"""Carregamento central dos arquivos visuais locais (imagens e ícones).

Imagens ficam em ``static/`` e são servidas pelo static serving do Streamlit
(``[server] enableStaticServing = true`` no config.toml), em ``app/static/<arquivo>``.
Assim o navegador baixa e guarda em cache cada imagem uma vez, sem reenviar base64
a cada rerun. Se o static serving estiver desligado, cai para um data URI em base64,
calculado uma única vez por processo.

Ícones SVG ficam em ``assets/icons/`` e viram máscaras CSS (ver ``utils/ui.py``).
"""
from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
STATIC_DIR = RAIZ / "static"
ICONS_DIR = RAIZ / "assets" / "icons"

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")


@lru_cache(maxsize=32)
def _data_uri(caminho: Path) -> str:
    mime = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(caminho.read_bytes()).decode()}"


def static_url(nome: str) -> str | None:
    """URL utilizável em CSS/HTML para um arquivo de ``static/``, ou None se não existir."""
    caminho = (STATIC_DIR / nome).resolve()
    if STATIC_DIR not in caminho.parents or not caminho.is_file():
        return None
    try:
        servindo = bool(st.get_option("server.enableStaticServing"))
    except Exception:
        servindo = False
    # Caminho relativo: funciona em localhost e no Streamlit Cloud (que serve o app sob um prefixo).
    return f"app/static/{caminho.name}" if servindo else _data_uri(caminho)


@lru_cache(maxsize=1)
def icones_svg() -> dict[str, str]:
    """SVGs de ``assets/icons`` por nome do arquivo (sem extensão). Ausentes são ignorados."""
    if not ICONS_DIR.is_dir():
        return {}
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(ICONS_DIR.glob("*.svg"))}
