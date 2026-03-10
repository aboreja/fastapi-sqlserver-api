import os
import msal
import httpx

PBI_TENANT_ID = os.getenv("PBI_TENANT_ID")
PBI_CLIENT_ID = os.getenv("PBI_CLIENT_ID")
PBI_CLIENT_SECRET = os.getenv("PBI_CLIENT_SECRET")

AUTHORITY = f"https://login.microsoftonline.com/{PBI_TENANT_ID}"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]
BASE_URL = "https://api.powerbi.com/v1.0/myorg"

def _get_access_token() -> str:
    if not (PBI_TENANT_ID and PBI_CLIENT_ID and PBI_CLIENT_SECRET):
        raise RuntimeError("Missing PBI_TENANT_ID / PBI_CLIENT_ID / PBI_CLIENT_SECRET")

    app = msal.ConfidentialClientApplication(
        client_id=PBI_CLIENT_ID,
        client_credential=PBI_CLIENT_SECRET,
        authority=AUTHORITY,
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(f"MSAL token error: {result.get('error')} - {result.get('error_description')}")
    return result["access_token"]

def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

def pbi_get(path: str, params: dict | None = None):
    token = _get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    url = f"{BASE_URL}{path}"
    with httpx.Client(timeout=60) as client:
        r = client.get(url, headers=headers, params=params)

    if r.status_code >= 400:
        raise RuntimeError(f"PBI {r.status_code} calling {url} params={params}\n{r.text}")

    return r.json() if r.text else None

def pbi_post(path: str, json: dict | None = None, params: dict | None = None):
    token = _get_access_token()
    url = f"{BASE_URL}{path}"
    with httpx.Client(timeout=60) as client:
        r = client.post(url, headers=_headers(token), json=json, params=params)

    if r.status_code in (202, 204):
        return None

    if r.status_code >= 400:
        raise RuntimeError(f"PBI {r.status_code} calling {url} params={params}\n{r.text}")

    return r.json() if r.text else None