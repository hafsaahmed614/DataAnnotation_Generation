"""
Upload synthetic case JSON files into Supabase synthetic_cases table.

Usage:
    python upload_cases.py

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env
(service_role key bypasses RLS for batch inserts).
"""

import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SYNTHETIC_DIR = "./data/synthetic_batch_25"
BATCH_ID = "synthetic_batch_25"


def main():
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ["SUPABASE_KEY"])
    client = create_client(url, key)

    files = sorted([
        f for f in os.listdir(SYNTHETIC_DIR)
        if f.endswith(".json")
    ])

    print(f"Found {len(files)} JSON files in {SYNTHETIC_DIR}")

    rows = []
    for idx, filename in enumerate(files, start=1):
        filepath = os.path.join(SYNTHETIC_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        rows.append({
            "batch_id": BATCH_ID,
            "label": f"Case_{idx}",
            "narrative_summary": data.get("narrative_summary", ""),
            "format_1_state_log": data.get("format_1_state_log", []),
            "format_2_triples": data.get("format_2_triples", []),
            "format_3_rl_scenario": data.get("format_3_rl_scenario", []),
        })

    result = client.table("synthetic_cases").insert(rows).execute()
    print(f"Inserted {len(result.data)} rows into synthetic_cases.")
    print("Upload complete.")


if __name__ == "__main__":
    main()
