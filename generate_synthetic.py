"""
Phase 2: Orchestrated Synthetic Case Generation

Queries ChromaDB for few-shot seed cases, injects static Taxonomies, and
calls the Gemini LLM to generate a high-fidelity synthetic patient case.
Output is validated via Pydantic and saved to ./data/synthetic_output/.

Usage:
    export GEMINI_API_KEY="your_key_here"
    python generate_synthetic.py

    # Optional: override target variables via env vars
    COMPLEXITY_GTE=4 FRICTION_BARRIER="Managed Medicare Auth" python generate_synthetic.py
"""

import chromadb
from dotenv import load_dotenv
import google.generativeai as genai
import json
import os
from datetime import datetime

load_dotenv()
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


# ── Configuration ────────────────────────────────────────────────────────────

CHROMA_DB_PATH     = "./chroma_db"
COLLECTION_NAME    = "seed_cases"
TAXONOMIES_DIR     = "./data/taxonomies"
OUTPUT_DIR         = "./data/synthetic_output"
MODEL_NAME         = "gemini-3-flash-preview"

# Target variables for this generation run (override via env vars or edit here)
TARGET_COMPLEXITY_GTE  = int(os.environ.get("COMPLEXITY_GTE", 4))
TARGET_FRICTION        = os.environ.get("FRICTION_BARRIER", "HHA_Intake_Freeze")
TARGET_PATIENT_DESC    = os.environ.get("PATIENT_DESC", "78yo Female, CHF")
N_FEW_SHOT_EXAMPLES    = 2
BATCH_SIZE             = int(os.environ.get("BATCH_SIZE", 1))


# ── Pydantic Output Schema (V5: 3-Stage PN Lifecycle Checklist) ──────────────

class RLScenarioOption(BaseModel):
    ai_intended_category: Literal["Passive", "Proactive", "Overstep"] = Field(
        description="Passive=Strategic Deferral; Proactive=Checklist-compliant verification/education; Overstep=Clinical/SW interference."
    )
    description: str = Field(description="The exact PN action taken.")
    rationale: str = Field(description="Explanation citing the PN Checklist Stage and role boundaries.")


class SyntheticCaseOutput(BaseModel):
    # Stage 1: Atlantis Entry & Triage
    atlantis_entry_confirmed: bool = Field(description="PN confirms patient appeared in Atlantis queue.")
    demographic_audit_note: str = Field(description="Verifying insurance, address, phone #, and DOB accuracy.")
    home_vs_ltc_determination: str = Field(description="Result of querying the SW on the goal (Home vs. LTC).")

    # Stage 2: Maintenance & Engagement
    weekly_facility_update: str = Field(description="Summary of weekly check-in with SW/Staff.")
    v_card_and_flyer_status: str = Field(description="Documenting V-card insertion into patient phone and flyer delivery.")

    # Stage 3: Handoff & Success Verification
    pre_dc_pulse_call_result: str = Field(description="Outcome of the call to patient 24hrs before discharge.")
    atlantis_final_sync: str = Field(description="Entry of D/C date and 1st visit date into Atlantis.")
    ma_visit_booking: str = Field(description="Confirmation of scheduling the MA for the 24-hour window.")

    # Core Content Formats
    narrative_summary: str = Field(description="A field report strictly following the 3-stage PN lifecycle.")
    format_1_state_log: List[dict] = Field(description="Timeline focused on home-readiness friction (not facility delays).")
    format_2_triples: List[dict] = Field(description="Situation -> Action -> Intent (Educate/Escalate/Verify).")
    format_3_rl_scenario: List[RLScenarioOption] = Field(description="Dilemmas regarding scope boundaries.")

    case_outcome: Literal[
        "Success_Home_with_First_Visit",
        "Neutral_LTC_Closure",
        "Neutral_Alternative_Agency",
        "Failure_Transition_Breakdown",
    ] = Field(
        description="Success only occurs if the patient goes home with our services and the first visit is completed."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_taxonomy(filename: str) -> dict:
    path = os.path.join(TAXONOMIES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def retrieve_few_shot_examples(collection, complexity_gte: int, query_text: str, n: int) -> list:
    """Query ChromaDB for n seed cases filtered by minimum complexity."""
    results = collection.query(
        query_texts=[query_text],
        n_results=n,
        where={"complexity_score": {"$gte": complexity_gte}},
    )

    examples = []
    for metadata in results.get("metadatas", [[]])[0]:
        raw = metadata.get("raw_json", "")
        if raw:
            try:
                examples.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
    return examples


def build_prompt(friction_taxonomy: dict, action_taxonomy: dict, outcome_taxonomy: dict,
                 few_shot_examples: list, target_patient: str, target_friction: str) -> str:
    """Assemble the full LLM prompt following the spec in Section 2.2."""

    friction_str  = json.dumps(friction_taxonomy, indent=2)
    action_str    = json.dumps(action_taxonomy, indent=2)
    outcome_str   = json.dumps(outcome_taxonomy, indent=2)
    examples_str  = json.dumps(few_shot_examples, indent=2)

    # Build JSON schema from Pydantic model for explicit instruction
    schema_str = json.dumps(SyntheticCaseOutput.model_json_schema(), indent=2)

    prompt = f"""
=== STATIC TAXONOMIES ===

--- Friction Taxonomy (defines allowable time delays) ---
{friction_str}

--- Action Taxonomy (defines PN checklist actions by stage) ---
{action_str}

--- Outcome Taxonomy (defines state transition triggers) ---
{outcome_str}

=== FEW-SHOT REFERENCE CASES ===

Here are {len(few_shot_examples)} real-world seed cases. Mimic their level of
clinical detail, operational chaos, and formatting exactly:

{examples_str}

=== TASK ===

Generate 1 NEW synthetic patient case with the following target variables:

- Patient: {target_patient}
- Main Friction: {target_friction}

You MUST strictly output valid JSON conforming to this schema and NO other text:

{schema_str}

=== 3-STAGE CHECKLIST RULES ===

Stage 1 fields (atlantis_entry_confirmed, demographic_audit_note, home_vs_ltc_determination):
1. atlantis_entry_confirmed must be true (patient appeared in queue).
2. demographic_audit_note must describe specific data verified or errors found (insurance type, address, phone, DOB).
3. home_vs_ltc_determination must record the SW's answer to "Is the goal Home or LTC?" If LTC, set case_outcome to "Neutral_LTC_Closure".

Stage 2 fields (weekly_facility_update, v_card_and_flyer_status):
4. weekly_facility_update must summarize a specific check-in (e.g., "Week 2: SW confirms D/C target is next Thursday; PT eval pending").
5. v_card_and_flyer_status must confirm whether the V-Card was inserted into the patient's phone and the flyer was delivered.

Stage 3 fields (pre_dc_pulse_call_result, atlantis_final_sync, ma_visit_booking):
6. pre_dc_pulse_call_result must describe the outcome of the 24-hour pre-discharge call (reached/not reached, home readiness confirmed or concerns raised).
7. atlantis_final_sync must confirm the D/C date and 1st visit date were entered into Atlantis.
8. ma_visit_booking must confirm the MA was scheduled within 24 hours of discharge, or explain the barrier.

=== FORMAT RULES ===

Rules for format_1_state_log (Timeline):
9. Each entry must be a dict with keys: event_description, clinical_impact (Improves/Worsens/Unchanged), environmental_impact (Improves/Worsens/Unchanged), service_adoption_impact (Positive/Negative/Unchanged), edd_delta (from Friction Taxonomy), ai_assumed_bottleneck.
10. Focus on HOME-READINESS friction (not facility discharge delays). Valid: HHA scheduling, DME delivery, Atlantis data errors, pre-DC call failures.

Rules for format_2_triples (Situation → Action → Intent):
11. Each entry must be a dict with keys: situation, action_taken, intent_category (Educate/Escalate/Verify).
12. The action_taken must be a PN checklist action, NOT a Social Worker action.

Rules for format_3_rl_scenario:
13. MUST contain exactly THREE options: one Passive, one Proactive, one Overstep.
14. All descriptions must sound professional and tempting.
   - "Passive" = STRATEGIC DEFERRAL: PN steps back, lets SW handle. Boundary-respecting, not lazy.
   - "Proactive" = CHECKLIST-COMPLIANT: PN verifies HHA logistics, educates family, conducts pulse call, schedules MA, or escalates to SW. Always within the 3-stage checklist.
   - "Overstep" = PN does the SW's job (suggesting agencies, handling F2F, calling insurance, managing meds). Must sound like good advocacy to a rookie.

Rules for case_outcome:
15. "Success_Home_with_First_Visit" = patient discharges with our services AND first home visit completed.
16. "Failure_Transition_Breakdown" = patient intended to use our services but the visit was missed (incentive lost).
17. "Neutral_LTC_Closure" / "Neutral_Alternative_Agency" = clean closure in Atlantis, not a success.

18. narrative_summary must be 3-5 sentences following the 3-stage PN lifecycle arc.
19. Output ONLY the JSON object. Do not include markdown fences, explanation, or commentary.
"""
    return prompt.strip()


def validate_and_save(raw_text: str, run_index: int) -> SyntheticCaseOutput | None:
    """Parse raw LLM JSON response, validate with Pydantic, and persist to disk."""
    # Strip any accidental markdown fences
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse failed: {e}")
        return None

    try:
        validated = SyntheticCaseOutput.model_validate(data)
    except Exception as e:
        print(f"  [ERROR] Pydantic validation failed: {e}")
        return None

    # Save to ./data/synthetic_output/
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUTPUT_DIR, f"synthetic_case_{timestamp}_{run_index}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(validated.model_dump(), f, indent=2)

    print(f"  Saved → {out_path}")
    return validated


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set.\n"
            "Export it with: export GEMINI_API_KEY='your_key_here'"
        )

    # Configure Gemini (use REST transport to avoid gRPC connectivity issues)
    genai.configure(api_key=api_key, transport="rest")
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.8,
        ),
    )

    # Load ChromaDB collection
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Load static taxonomies
    friction_taxonomy = load_taxonomy("friction_taxonomy.json")
    action_taxonomy   = load_taxonomy("action_taxonomy.json")
    outcome_taxonomy  = load_taxonomy("outcome_taxonomy.json")

    system_prompt = (
        "You are a Patient Navigator (PN) operating in the Atlantis software environment. "
        "Your goal is to ensure a safe transition home to trigger the 'First Visit' incentive.\n\n"

        "=== THE 3-STAGE LIFECYCLE ===\n"
        "Every case MUST move through these stages:\n"
        "1) ENTRY/TRIAGE: Patient appears in Atlantis queue. PN audits demographics (insurance, address, phone, DOB). "
        "PN asks SW: 'Is the goal Home or LTC?'\n"
        "2) MAINTENANCE: Weekly check-ins with SW/staff. PN inserts V-Card into patient's phone and delivers flyer. "
        "PN educates patient/family on program benefits.\n"
        "3) HANDOFF: PN conducts 24-hour pre-discharge pulse call. Enters D/C date and 1st visit date into Atlantis. "
        "Hands physical appointment card to patient. Schedules the MA for the first visit within 24 hours of discharge.\n\n"

        "=== THE LTC FILTER ===\n"
        "If the SW determines the goal is Long-Term Care (LTC), the PN performs a Neutral_LTC_Closure in Atlantis "
        "and stops all work. Continuing to pitch home care to an LTC patient is an Overstep.\n\n"

        "=== THE SW BOUNDARY ===\n"
        "The Social Worker (SW) sends referrals and finds agencies. The PN NEVER suggests alternative HHAs, "
        "handles F2F forms, or manages clinical medications.\n\n"

        "=== SCHEDULING ANCHOR ===\n"
        "The PN must give the patient a physical appointment card and ensure the visit happens within "
        "24 hours of discharge. The PN must schedule the MA for this visit.\n\n"

        "=== BANNED ACTIONS (AUTOMATIC OVERSTEP) ===\n"
        "- Suggesting specific HHA agencies to the SW\n"
        "- Handling F2F (Face-to-Face) forms\n"
        "- Managing facility medications\n"
        "- Touching the facility EMR or clinical documentation\n"
        "- Calling insurance companies for authorization\n"
        "- Leading or calling facility team meetings\n"
        "- Interrupting doctors during rounds\n"
        "- Proving cost analysis of home care vs LTC\n"
        "- Telling families to refuse discharge or go AMA\n\n"

        "FOG OF WAR: The PN always acts on INCOMPLETE information. At least one critical "
        "detail must be unknown, delayed, or contradictory.\n\n"

        "PATIENT CHOICE: Some cases must feature friction driven by patient or family decisions.\n\n"

        "BANNED TROPES: 'F2F / Face-to-Face signatures', 'burned-out Social Worker', "
        "'100-day financial cliff', 'Private pay to LTC', 'Black Hole'."
    )

    print(f"Starting batch generation: {BATCH_SIZE} case(s)")
    print(f"  Model          : {MODEL_NAME}")
    print(f"  Target patient : {TARGET_PATIENT_DESC}")
    print(f"  Target friction: {TARGET_FRICTION}")
    print(f"  Complexity >=  : {TARGET_COMPLEXITY_GTE}\n")

    for i in range(BATCH_SIZE):
        print(f"--- Generation {i + 1}/{BATCH_SIZE} ---")

        # 2.1 Retrieve few-shot examples from ChromaDB
        query_text = f"Bureaucratic delay with {TARGET_FRICTION} and clinical barriers"
        examples = retrieve_few_shot_examples(
            collection,
            complexity_gte=TARGET_COMPLEXITY_GTE,
            query_text=query_text,
            n=N_FEW_SHOT_EXAMPLES,
        )
        print(f"  Retrieved {len(examples)} few-shot example(s) from ChromaDB.")

        # 2.2 Build prompt
        user_prompt = build_prompt(
            friction_taxonomy, action_taxonomy, outcome_taxonomy,
            examples, TARGET_PATIENT_DESC, TARGET_FRICTION,
        )

        # Call Gemini
        response = model.generate_content(
            contents=[
                {"role": "user", "parts": [system_prompt + "\n\n" + user_prompt]}
            ]
        )

        raw_text = response.text
        print(f"  Received {len(raw_text)} chars from Gemini.")

        # 2.4 Validate and save
        result = validate_and_save(raw_text, run_index=i + 1)
        if result:
            print(f"  Validation passed.\n")
        else:
            print(f"  Validation failed. Raw response saved for debugging:\n{raw_text[:500]}\n")

    print("Done.")


if __name__ == "__main__":
    main()
