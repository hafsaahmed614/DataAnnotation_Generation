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
BATCH_ID = "synthetic_batch_25_v5"
TABLE_NAME = "synthetic_cases_v5"


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
            # Stage 1
            "atlantis_entry_confirmed": data.get("atlantis_entry_confirmed", False),
            "demographic_audit_note": data.get("demographic_audit_note", ""),
            "home_vs_ltc_determination": data.get("home_vs_ltc_determination", ""),
            # Stage 2
            "weekly_facility_update": data.get("weekly_facility_update", ""),
            "v_card_and_flyer_status": data.get("v_card_and_flyer_status", ""),
            # Stage 3
            "pre_dc_pulse_call_result": data.get("pre_dc_pulse_call_result", ""),
            "atlantis_final_sync": data.get("atlantis_final_sync", ""),
            "ma_visit_booking": data.get("ma_visit_booking", ""),
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
