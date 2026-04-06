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

SYNTHETIC_DIR = "./data/synthetic_batch_25_v15"
BATCH_ID = "synthetic_batch_25_v15"
TABLE_NAME = "synthetic_cases_v15"


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
            # Cognitive Delineation
            "role_delineation_check": data.get("role_delineation_check", ""),
            # Stage 1
            "atlantis_entry_confirmed": data.get("atlantis_entry_confirmed", False),
            "demographic_audit_note": data.get("demographic_audit_note", ""),
            "home_vs_ltc_goal": data.get("home_vs_ltc_goal", ""),
            # Stage 2
            "v_card_flyer_status": data.get("v_card_flyer_status", ""),
            # Stage 3
            "pre_dc_pulse_call": data.get("pre_dc_pulse_call", ""),
            "atlantis_final_sync": data.get("atlantis_final_sync", ""),
            # Core content
            "narrative_summary": data.get("narrative_summary", ""),
            "format_1_state_log": data.get("format_1_state_log", []),
            "format_2_triples": data.get("format_2_triples", []),
            "format_3_rl_scenario": data.get("format_3_rl_scenario", []),
            "case_outcome": data.get("case_outcome", ""),
        })

    result = client.table(TABLE_NAME).insert(rows).execute()
    print(f"Inserted {len(result.data)} rows into {TABLE_NAME}.")
    print("Upload complete.")


if __name__ == "__main__":
    main()
