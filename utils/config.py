from __future__ import annotations
from dataclasses import dataclass
import streamlit as st


@dataclass
class Config:
    spreadsheet_id: str = ""
    aba_estoque: str = "Estoque de Medicamentos"
    aba_materiais: str = "Estoque de Materiais"
    aba_registro: str = "Registro Diário de Medicamentos"
    aba_historico: str = "Histórico de Movimentações"
    aba_auditoria: str = "AUDITORIA"
    clinic_name: str = "Clínica"
    responsible_email: str = ""
    dias_alerta_atencao: int = 30
    dias_alerta_proximo: int = 90


def get_config() -> Config:
    try:
        # Prefer environment variables (useful for CI / containers), then Streamlit secrets
        import os
        sid = os.environ.get('SPREADSHEET_ID') or os.environ.get('SPREADSHEET_NAME')
        clinic = os.environ.get('CLINIC_NAME')
        resp = os.environ.get('RESPONSIBLE_EMAIL')

        secrets = None
        try:
            secrets = st.secrets
        except Exception:
            secrets = None

        if not sid and secrets:
            sid = secrets.get("SPREADSHEET_ID") if isinstance(secrets, dict) or hasattr(secrets, 'get') else None
        if not clinic and secrets:
            clinic = secrets.get("CLINIC_NAME", "Clínica")
        if not resp and secrets:
            resp = secrets.get("RESPONSIBLE_EMAIL", "")

        # Fallback: if running outside streamlit runtime, read .streamlit/secrets.toml
        if not sid:
            try:
                import os
                try:
                    import tomllib as toml
                except Exception:
                    import toml

                repo_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
                secrets_path = os.path.join(repo_root, '.streamlit', 'secrets.toml')
                if os.path.exists(secrets_path):
                    with open(secrets_path, 'rb') as f:
                        data = toml.load(f)
                    sid = sid or data.get('SPREADSHEET_ID') or data.get('SPREADSHEET_NAME')
                    clinic = clinic or data.get('CLINIC_NAME')
                    resp = resp or data.get('RESPONSIBLE_EMAIL')
            except Exception:
                pass

        return Config(
            spreadsheet_id=sid or "",
            clinic_name=clinic,
            responsible_email=resp,
        )
    except Exception:
        return Config()
