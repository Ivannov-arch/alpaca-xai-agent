"""Test connection to Supabase."""
from dotenv import load_dotenv; load_dotenv()
from agent.db import get_client

try:
    client = get_client()
    # Try fetching a simple query
    res = client.table("accounts").select("count").execute()
    print("Supabase connection OK, result:", res.data)
except Exception as e:
    print("Supabase connection FAILED:", e)
