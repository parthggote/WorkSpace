import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Missing credentials")
    exit(1)

headers = {
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
}

resp = httpx.get(f"{SUPABASE_URL}/storage/v1/bucket", headers=headers)
if resp.status_code == 200:
    buckets = [b["id"] for b in resp.json()]
    if "documents" not in buckets:
        print("Creating documents bucket...")
        create_resp = httpx.post(
            f"{SUPABASE_URL}/storage/v1/bucket",
            headers=headers,
            json={"id": "documents", "name": "documents", "public": False}
        )
        print("Create response:", create_resp.status_code, create_resp.text)
    else:
        print("documents bucket already exists.")
else:
    print("Failed to list buckets:", resp.status_code, resp.text)
