import traceback
import os
import sys


def main():
    print("Starting sheets service tests...")
    # ensure repo root is on sys.path so imports like `services.sheets_service` work
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    try:
        import services.sheets_service as sheets
    except Exception as e:
        print("Failed to import services.sheets_service:", e)
        traceback.print_exc()
        return

    try:
        print("\n-> Testing _get_client()")
        client = sheets._get_client()
        print("Client type:", type(client))
    except Exception as e:
        print("_get_client error:", e)
        traceback.print_exc()

    try:
        print("\n-> Testing _get_spreadsheet()")
        # Prefer the package helper which uses st.secrets, but if st.secrets is not
        # configured (running outside streamlit CLI), fall back to reading the
        # .streamlit/secrets.toml and creating a client manually for the test.
        try:
            ss = sheets._get_spreadsheet()
            print("Spreadsheet type:", type(ss))
            print("Spreadsheet repr:", repr(ss))
        except Exception as e:
            print("_get_spreadsheet via service failed, attempting manual fallback:", e)
            # Manual fallback: read secrets.toml and create gspread client
            try:
                import tomllib
            except Exception:
                import toml as tomllib

            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            secrets_path = os.path.join(repo_root, '.streamlit', 'secrets.toml')
            if not os.path.exists(secrets_path):
                raise RuntimeError(f"secrets file not found at {secrets_path}")

            with open(secrets_path, 'rb') as f:
                data = tomllib.load(f)

            gsa = data.get('gcp_service_account')
            sid = data.get('SPREADSHEET_ID') or data.get('SPREADSHEET_NAME')
            if not gsa or not sid:
                raise RuntimeError('secrets.toml missing gcp_service_account or SPREADSHEET_ID')

            try:
                from utils.helpers import sanitize_service_account
                info = sanitize_service_account(gsa)
            except Exception:
                info = gsa

            try:
                from google.oauth2.service_account import Credentials
                import gspread
                creds = Credentials.from_service_account_info(info, scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive.readonly",
                ])
                client = gspread.authorize(creds)
                # extract id if URL provided
                m = __import__('re').search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", str(sid))
                key = m.group(1) if m else sid
                ss = client.open_by_key(key)
                print("(fallback) Spreadsheet type:", type(ss))
                print("(fallback) Spreadsheet repr:", repr(ss))
            except Exception as e2:
                print("Manual fallback open error:", e2)
                traceback.print_exc()
    except Exception as e:
        print("_get_spreadsheet error:", e)
        traceback.print_exc()

    try:
        print("\n-> Testing ler_estoque()")
        df = sheets.ler_estoque()
        print("DataFrame shape:", getattr(df, 'shape', None))
        try:
            print(df.head(5).to_dict())
        except Exception:
            print(df)
    except Exception as e:
        print("ler_estoque error:", e)
        traceback.print_exc()


if __name__ == '__main__':
    main()
