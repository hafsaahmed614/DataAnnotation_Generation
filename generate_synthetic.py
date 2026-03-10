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


# ── Pydantic Output Schema (V7: Cool Down — Liaison-Only PN) ─────────────────

class RLScenarioOption(BaseModel):
    ai_intended_category: Literal["Passive", "Proactive", "Overstep"] = Field(
        description="Passive=Strategic Deferral; Proactive=Liaison/Education; Overstep=Clinical/Vendor interference."
    )
    description: str = Field(description="The exact PN action taken.")
    rationale: str = Field(description="Explain why this respects the SW boundary and avoids vendor contact.")


class SyntheticCaseOutput(BaseModel):
    # Cognitive Delineation
    role_delineation_check: str = Field(description="Statement of SW vs PN boundaries for this specific case.")

    # Stage 1: Entry & Triage (Atlantis Workflow)
    atlantis_entry_confirmed: bool = Field(description="PN confirms patient appeared in Atlantis queue.")
    demographic_audit_note: str = Field(description="Results of verifying DOB, Insurance, and Phone # accuracy against the Face Sheet.")
    home_vs_ltc_goal: str = Field(description="The discharge goal provided by the SW.")

    # Stage 2: Maintenance
    weekly_staff_update: str = Field(description="Brief summary of the weekly check-in with the SW/Staff.")
    v_card_flyer_status: str = Field(description="Confirmation of V-Card (for Caller ID recognition) and flyer delivery.")

    # Stage 3: Handoff
    pre_dc_pulse_call: str = Field(description="Result of the check-in call 24hrs before discharge.")
    atlantis_final_sync: str = Field(description="Documentation of D/C date and 1st visit date in Atlantis.")
    ma_visit_booking: str = Field(description="Confirmation of MA scheduling (must wait for SW/HHA confirmation).")

    # Content Formats
    narrative_summary: str = Field(description="A field report focused on data accuracy and family readiness.")
    format_1_state_log: List[dict] = Field(description="Timeline of transition friction (e.g., data lags, caregiver anxiety).")
    format_2_triples: List[dict] = Field(description="Situation -> Action -> Intent (Verify/Educate/Flag).")
    format_3_rl_scenario: List[RLScenarioOption] = Field(description="Dilemmas testing the 'No-Vendor' and 'Wait' rules.")

    case_outcome: Literal[
        "Success_Home_with_First_Visit",
        "Neutral_LTC_Closure",
        "Neutral_Alternative_Agency",
        "Failure_Transition_Breakdown",
    ] = Field(
        description="Success is triggered ONLY by a completed first home visit post-discharge. "
        "If the PN oversteps to make it happen, it is an authenticity failure."
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

=== FIELD RULES ===

role_delineation_check:
1. Must explicitly state the SW vs PN boundary for THIS specific case. Example: "SW handles HHA referral and agency selection. PN verifies Atlantis data, educates family, and flags concerns."

Stage 1 fields (atlantis_entry_confirmed, demographic_audit_note, home_vs_ltc_goal):
2. atlantis_entry_confirmed must be true (patient appeared in queue).
3. demographic_audit_note must describe specific data verified or errors found against the Face Sheet (DOB, Insurance, Phone #).
4. home_vs_ltc_goal must record the SW's answer to "Is the goal Home or LTC?" If LTC, set case_outcome to "Neutral_LTC_Closure".

Stage 2 fields (weekly_staff_update, v_card_flyer_status):
5. weekly_staff_update must summarize a specific check-in (e.g., "Week 2: SW confirms D/C target is next Thursday; PT eval pending").
6. v_card_flyer_status must confirm V-Card insertion (for Caller ID recognition) and flyer delivery. The V-Card is NOT for coordinating logistics.

Stage 3 fields (pre_dc_pulse_call, atlantis_final_sync, ma_visit_booking):
7. pre_dc_pulse_call must describe the outcome of the 24-hour pre-discharge call (reached/not reached, family readiness sentiment).
8. atlantis_final_sync must confirm the D/C date and 1st visit date were entered into Atlantis.
9. ma_visit_booking must confirm the MA was scheduled within 24 hours of discharge ONLY AFTER SW confirms HHA readiness. If HHA not confirmed, PN flags to SW and WAITS.

=== FORMAT RULES ===

Rules for format_1_state_log (Timeline):
10. Each entry must be a dict with keys: event_description, clinical_impact (Improves/Worsens/Unchanged), environmental_impact (Improves/Worsens/Unchanged), service_adoption_impact (Positive/Negative/Unchanged), edd_delta (from Friction Taxonomy), ai_assumed_bottleneck.
11. Focus on data-accuracy and family-readiness friction. Valid: Atlantis data lags, caregiver anxiety, sentiment readiness gaps, HHA acceptance lags (flagged to SW, not investigated by PN).

Rules for format_2_triples (Situation → Action → Intent):
12. Each entry must be a dict with keys: situation, action_taken, intent_category (Verify/Educate/Flag).
13. The action_taken must use Liaison verbs ONLY (Verify, Document, Flag, Educate, Ask). NEVER use Fixer verbs (Coordinate, Resolve, Solve, Order, Negotiate, Investigate). The PN never contacts vendors directly.

Rules for format_3_rl_scenario:
14. MUST contain exactly THREE options: one Passive, one Proactive, one Overstep.
15. All descriptions must sound professional and tempting.
   - "Passive" = STRATEGIC DEFERRAL: PN steps back, lets SW handle. Boundary-respecting, not lazy.
   - "Proactive" = LIAISON/EDUCATION: PN verifies data in Atlantis, educates family on Day 1 expectations, checks family sentiment, flags concerns to SW, conducts pulse call. Uses only Liaison verbs. Never contacts vendors.
   - "Overstep" = PN contacts vendors directly (calls HHA intake, DME vendor, transport), uses Fixer verbs, performs clinical intakes, or schedules MA before SW confirms HHA. Must sound like good advocacy to a rookie.

Rules for case_outcome:
16. "Success_Home_with_First_Visit" = patient discharges home AND first home visit completed. Success is triggered ONLY by a completed first visit. If the PN oversteps to make it happen, it is an authenticity failure.
17. "Failure_Transition_Breakdown" = patient intended to use our services but the visit was missed (incentive lost).
18. "Neutral_LTC_Closure" / "Neutral_Alternative_Agency" = clean closure in Atlantis, not a success.

19. narrative_summary must be 3-5 sentences focused on data accuracy and family readiness, using Liaison verbs only.
20. Output ONLY the JSON object. Do not include markdown fences, explanation, or commentary.
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
        "Your primary role is to ensure the First Home Visit happens by auditing data and supporting the family.\n\n"

        "=== OPERATIONAL GUARDRAILS ===\n\n"

        "THE NO-VENDOR RULE: The PN is strictly forbidden from calling HHA Intake, DME Vendors, "
        "or Transport companies. The PN only communicates with the Family/Patient and the Social Worker (SW).\n\n"

        "THE VERB FILTER: PN actions must use 'Liaison' verbs: Verify, Document, Flag, Educate, Ask. "
        "Banned 'Fixer' verbs: Coordinate, Resolve, Solve, Order, Negotiate, Investigate.\n\n"

        "THE V-CARD INTENT: The V-Card is inserted into the patient's phone strictly as a Caller ID tool "
        "so they recognize the Healing Partners call. It is NOT for 'coordinating' logistics.\n\n"

        "THE 'WAIT' DEFAULT: If the HHA is blocked, DME is missing, or transport is late, the 'Proactive' action "
        "is to Flag it to the SW in Atlantis and then WAIT. Attempting to solve the logistics yourself is an Overstep.\n\n"

        "SENTIMENT OVER CLINICAL: Do not perform clinical intakes. Instead, Verify the Sentiment Score "
        "(how ready does the family feel?). If they feel anxious, flag it to the SW for a care conference.\n\n"

        "=== THE 3-STAGE LIFECYCLE ===\n"
        "Every case MUST move through these stages (Address them by the stage name, not by the stage number):\n\n"

        "ENTRY/TRIAGE: Patient appears in Atlantis queue. PN audits demographics (DOB, Insurance, Phone #) "
        "against the Face Sheet. PN asks SW: 'Is the goal Home or LTC?' "
        "PN begins role_delineation_check — explicitly stating what is the SW's job vs the PN's job for this case.\n\n"

        "MAINTENANCE: Weekly check-ins with SW/staff. PN inserts V-Card into patient's phone (Caller ID only) "
        "and delivers flyer. PN educates patient/family on program benefits. "
        "PN verifies family sentiment (readiness/anxiety level) and flags concerns to SW.\n\n"

        "HANDOFF: PN conducts 24-hour pre-discharge pulse call to patient/family. "
        "Enters D/C date and 1st visit date into Atlantis. "
        "Hands physical appointment card to patient. "
        "Schedules the MA for the first visit within 24 hours of discharge — but ONLY after SW confirms HHA is ready. "
        "If HHA is not confirmed, PN flags it to SW and WAITS.\n\n"

        "=== THE LTC FILTER ===\n"
        "If the SW determines the goal is Long-Term Care (LTC), the PN performs a Neutral_LTC_Closure in Atlantis "
        "and stops all work. Continuing to pitch home care to an LTC patient is an Overstep.\n\n"

        "=== THE SW BOUNDARY ===\n"
        "The Social Worker (SW) sends referrals, finds agencies, and handles all vendor communication. "
        "The PN NEVER contacts HHA Intake, DME vendors, transport companies, or insurance companies directly.\n\n"

        "=== BANNED ACTIONS (AUTOMATIC OVERSTEP) ===\n"
        "- Calling HHA Intake coordinators directly\n"
        "- Calling DME vendors or transport companies\n"
        "- Suggesting specific HHA agencies to the SW\n"
        "- Handling F2F (Face-to-Face) forms\n"
        "- Managing facility medications\n"
        "- Touching the facility EMR or clinical documentation\n"
        "- Calling insurance companies for authorization\n"
        "- Leading or calling facility team meetings\n"
        "- Interrupting doctors during rounds\n"
        "- Proving cost analysis of home care vs LTC\n"
        "- Telling families to refuse discharge or go AMA\n"
        "- Using 'Fixer' verbs: Coordinate, Resolve, Solve, Order, Negotiate, Investigate\n"
        "- Performing clinical intakes or assessments\n"
        "- Scheduling MA before SW confirms HHA readiness\n\n"

        "FOG OF WAR: The PN always acts on INCOMPLETE information. At least one critical "
        "detail must be unknown, delayed, or contradictory.\n\n"

        "PATIENT CHOICE: Some cases must feature friction driven by patient or family decisions.\n\n"

        "BANNED TROPES: 'F2F / Face-to-Face signatures', 'burned-out Social Worker', "
        "'100-day financial cliff', 'Private pay to LTC', 'Black Hole', "
        "'PN calls HHA intake directly', 'PN coordinates with DME vendor'."
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
