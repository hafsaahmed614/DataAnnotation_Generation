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


# ── Pydantic Output Schema (V6: Connection & Confidence Mandate) ─────────────

class RLScenarioOption(BaseModel):
    ai_intended_category: Literal["Passive", "Proactive", "Overstep"] = Field(
        description="Passive=Strategic Deferral; Proactive=PN Liaison work; Overstep=Clinical/SW interference."
    )
    description: str = Field(description="The exact PN action taken.")
    rationale: str = Field(description="Explanation citing role boundaries and HHA-first scheduling rules.")


class SyntheticCaseOutput(BaseModel):
    # Stage 1: Atlantis Entry & Triage
    atlantis_entry_confirmed: bool = Field(description="PN confirms patient appeared in Atlantis queue.")
    demographic_audit_note: str = Field(description="Verifying insurance, address, phone #, and DOB accuracy.")
    home_vs_ltc_determination: str = Field(description="Result of querying the SW on the goal (Home vs. LTC).")
    stage_1_intake_responses: str = Field(
        description="Answers to the 4 Connection Intake questions: (1) Have you heard of us? "
        "(2) Do you know why we are here? (3) Has anyone explained home health to you? "
        "(4) Do you have any concerns about going home?"
    )

    # Stage 2: Maintenance & Engagement
    weekly_facility_update: str = Field(description="Summary of weekly check-in with SW/Staff.")
    v_card_and_flyer_status: str = Field(description="Documenting V-card insertion into patient phone and flyer delivery.")

    # Stage 3: Handoff & Success Verification
    hha_confirmation_status: str = Field(
        description="HHA status check: Is the HHA confirmed 'In Place' (SOC date, assigned nurse, first-visit window)? "
        "MA scheduling must NOT proceed until this is 'In Place'."
    )
    stage_3_followup_audit: str = Field(
        description="Week-of-discharge confidence check: (1) Call to SW — confirm D/C date and HHA readiness. "
        "(2) Call to patient/family — confirm understanding of Day 1 plan and who is arriving."
    )
    pre_dc_pulse_call_result: str = Field(description="Outcome of the call to patient 24hrs before discharge.")
    atlantis_final_sync: str = Field(description="Entry of D/C date and 1st visit date into Atlantis.")
    ma_visit_booking: str = Field(description="Confirmation of scheduling the MA for the 24-hour window. Must NOT occur until HHA is 'In Place'.")

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

Stage 1 fields (atlantis_entry_confirmed, demographic_audit_note, home_vs_ltc_determination, stage_1_intake_responses):
1. atlantis_entry_confirmed must be true (patient appeared in queue).
2. demographic_audit_note must describe specific data verified or errors found (insurance type, address, phone, DOB).
3. home_vs_ltc_determination must record the SW's answer to "Is the goal Home or LTC?" If LTC, set case_outcome to "Neutral_LTC_Closure".
4. stage_1_intake_responses must record the patient's answers to all 4 Connection Intake questions. Example: "Q1: No, never heard of us. Q2: Thinks we are from the hospital. Q3: SW briefly mentioned it. Q4: Worried about managing wound care alone — escalated concern to SW."

Stage 2 fields (weekly_facility_update, v_card_and_flyer_status):
5. weekly_facility_update must summarize a specific check-in (e.g., "Week 2: SW confirms D/C target is next Thursday; PT eval pending").
6. v_card_and_flyer_status must confirm whether the V-Card was inserted into the patient's phone and the flyer was delivered.

Stage 3 fields (hha_confirmation_status, stage_3_followup_audit, pre_dc_pulse_call_result, atlantis_final_sync, ma_visit_booking):
7. hha_confirmation_status must state whether the HHA is "In Place" (SOC date set, nurse assigned, first-visit window confirmed) or "Not In Place" with the specific barrier. The MA must NOT be scheduled until HHA is "In Place".
8. stage_3_followup_audit must describe the two Confidence Audit calls: (a) Call to SW confirming D/C date and HHA readiness, (b) Call to patient/family confirming Day 1 understanding.
9. pre_dc_pulse_call_result must describe the outcome of the 24-hour pre-discharge call (reached/not reached, home readiness confirmed or concerns raised).
10. atlantis_final_sync must confirm the D/C date and 1st visit date were entered into Atlantis.
11. ma_visit_booking must confirm the MA was scheduled within 24 hours of discharge ONLY AFTER HHA is "In Place", or explain the barrier.

=== FORMAT RULES ===

Rules for format_1_state_log (Timeline):
12. Each entry must be a dict with keys: event_description, clinical_impact (Improves/Worsens/Unchanged), environmental_impact (Improves/Worsens/Unchanged), service_adoption_impact (Positive/Negative/Unchanged), edd_delta (from Friction Taxonomy), ai_assumed_bottleneck.
13. Focus on HOME-READINESS friction (not facility discharge delays). Valid: HHA scheduling, DME delivery, Atlantis data errors, pre-DC call failures, HHA confirmation delays, premature MA scheduling.

Rules for format_2_triples (Situation → Action → Intent):
14. Each entry must be a dict with keys: situation, action_taken, intent_category (Educate/Escalate/Verify).
15. The action_taken must be a PN checklist action, NOT a Social Worker action. Include Connection Intake and Confidence Audit actions where appropriate.

Rules for format_3_rl_scenario:
16. MUST contain exactly THREE options: one Passive, one Proactive, one Overstep.
17. All descriptions must sound professional and tempting.
   - "Passive" = STRATEGIC DEFERRAL: PN steps back, lets SW handle. Boundary-respecting, not lazy.
   - "Proactive" = PN LIAISON WORK: PN conducts Connection Intake, verifies HHA status before scheduling MA, performs Confidence Audit, educates family, conducts pulse call, or escalates to SW. Always within the 3-stage checklist and HHA-First Rule.
   - "Overstep" = PN does the SW's job (suggesting agencies, handling F2F, calling insurance, managing meds, scheduling MA before HHA is confirmed). Must sound like good advocacy to a rookie.

Rules for case_outcome:
18. "Success_Home_with_First_Visit" = patient discharges home, HHA was confirmed "In Place" before MA was scheduled, AND first home visit completed within 24 hours.
19. "Failure_Transition_Breakdown" = patient intended to use our services but the visit was missed (incentive lost). This includes cases where the MA was scheduled prematurely (before HHA confirmation) and the visit fell through.
20. "Neutral_LTC_Closure" / "Neutral_Alternative_Agency" = clean closure in Atlantis, not a success.

21. narrative_summary must be 3-5 sentences following the 3-stage PN lifecycle arc, mentioning the Connection Intake and Confidence Audit where relevant.
22. Output ONLY the JSON object. Do not include markdown fences, explanation, or commentary.
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
        "Your primary objective is to build a 'Confidence Loop' — a chain of verified touchpoints "
        "that ensures the patient, the family, and the HHA are all aligned before the MA is ever scheduled.\n\n"

        "=== THE 3-STAGE LIFECYCLE ===\n"
        "Every case MUST move through these stages (Address them by the stage name, not by the stage number):\n\n"

        "ENTRY/TRIAGE: Patient appears in Atlantis queue. PN audits demographics (insurance, address, phone, DOB). "
        "PN asks SW: 'Is the goal Home or LTC?' "
        "PN conducts the CONNECTION INTAKE — 4 mandatory questions at the first patient meeting:\n"
        "  Q1: 'Have you heard of [our company]?'\n"
        "  Q2: 'Do you know why we are here?'\n"
        "  Q3: 'Has anyone explained home health services to you?'\n"
        "  Q4: 'Do you have any concerns about going home?'\n"
        "These answers reveal the patient's baseline awareness and anxiety level. "
        "If Q4 surfaces specific barriers (e.g., no caregiver, unsafe home), escalate to SW immediately.\n\n"

        "MAINTENANCE: Weekly check-ins with SW/staff. PN inserts V-Card into patient's phone and delivers flyer. "
        "PN educates patient/family on program benefits.\n\n"

        "HANDOFF: PN performs the CONFIDENCE AUDIT — a week-of-discharge follow-up with two calls:\n"
        "  Call 1 (to SW): Confirm the D/C date is firm and the HHA has confirmed start-of-care.\n"
        "  Call 2 (to patient/family): Confirm they understand the Day 1 plan — who is arriving, "
        "what equipment should be present, and what to do if the nurse is late.\n"
        "After audit, PN conducts the 24-hour pre-discharge pulse call. "
        "Enters D/C date and 1st visit date into Atlantis. "
        "Hands physical appointment card to patient. Schedules the MA for the first visit within 24 hours of discharge.\n\n"

        "=== THE HHA-FIRST RULE ===\n"
        "The PN must NOT schedule the MA visit until the HHA is confirmed 'In Place' — meaning: "
        "SOC date is set, a nurse is assigned, and the first-visit time window is confirmed. "
        "Scheduling the MA before HHA confirmation risks a wasted visit and a failed incentive. "
        "If the HHA is NOT 'In Place', the PN must investigate the specific barrier "
        "(staffing shortage? intake freeze? missing orders?) and escalate to the SW.\n\n"

        "=== THE LTC FILTER ===\n"
        "If the SW determines the goal is Long-Term Care (LTC), the PN performs a Neutral_LTC_Closure in Atlantis "
        "and stops all work. Continuing to pitch home care to an LTC patient is an Overstep.\n\n"

        "=== THE SW BOUNDARY ===\n"
        "The Social Worker (SW) sends referrals and finds agencies. The PN NEVER suggests alternative HHAs, "
        "handles F2F forms, or manages clinical medications.\n\n"

        "=== BANNED ACTIONS (AUTOMATIC OVERSTEP) ===\n"
        "- Suggesting specific HHA agencies to the SW\n"
        "- Handling F2F (Face-to-Face) forms\n"
        "- Managing facility medications\n"
        "- Touching the facility EMR or clinical documentation\n"
        "- Calling insurance companies for authorization\n"
        "- Leading or calling facility team meetings\n"
        "- Interrupting doctors during rounds\n"
        "- Proving cost analysis of home care vs LTC\n"
        "- Telling families to refuse discharge or go AMA\n"
        "- Scheduling the MA before the HHA is confirmed 'In Place'\n\n"

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
