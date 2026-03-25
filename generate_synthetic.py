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


# ── Pydantic Output Schema (V13: Evaluation-Refined Taxonomy) ─────────────────

class RLScenarioOption(BaseModel):
    ai_intended_category: Literal["Passive", "Proactive", "Overstep"] = Field(
        description="Passive=Strategic Deferral; Proactive=Liaison/Education; Overstep=Clinical/Vendor interference."
    )
    description: str = Field(description="A professional action description written in natural prose. No underscores or taxonomy keys.")
    rationale: str = Field(description="Explanation of why this respects the SW boundary, written in natural prose.")


class SyntheticCaseOutput(BaseModel):
    """Ensure all generated text is free of technical keys, underscores, and computer-like phrasing."""
    role_delineation_check: str = Field(description="Internal logic check: Differentiating SW logistics from PN liaison work.")
    narrative_summary: str = Field(description="A professional 1-paragraph story of the patient's transition. Must use natural prose — no taxonomy keys or underscores.")
    atlantis_entry_confirmed: bool = Field(description="PN confirms patient appears in Atlantis.")
    demographic_audit_note: str = Field(description="Narrative detail of the data verification process (Phone, Address, DOB).")
    home_vs_ltc_goal: str = Field(description="The discharge destination confirmed by the SW.")
    v_card_flyer_status: str = Field(description="Narrative of how the V-card and flyer were used to prepare the family.")
    pre_dc_pulse_call: str = Field(description="Summary of the sentiment/readiness check 24hrs before discharge.")
    atlantis_final_sync: str = Field(description="Recording of the D/C date and 1st visit date in Atlantis.")

    format_1_state_log: List[dict] = Field(description="Timeline of narrative events focused on transition friction. Event descriptions must read like real-time progress notes.")
    format_2_triples: List[dict] = Field(description="Situation -> Action -> Intent. The action_taken must be written in natural professional prose — no taxonomy keys or underscores.")
    format_3_rl_scenario: List[RLScenarioOption] = Field(description="Dilemmas testing boundary adherence. All descriptions must use natural prose.")
    case_outcome: Literal[
        "Success_Home_with_First_Visit",
        "Neutral_LTC_Closure",
        "Neutral_Alternative_Agency",
        "Failure_Transition_Breakdown",
    ]


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
1. Must explicitly state the SW vs PN boundary for THIS specific case. Example: "The social worker handles referral logistics and agency selection while the navigator verifies demographic data in Atlantis, educates the family on program benefits, and flags concerns."

Stage 1 fields (atlantis_entry_confirmed, demographic_audit_note, home_vs_ltc_goal):
2. atlantis_entry_confirmed must be true (patient appeared in queue).
3. demographic_audit_note must be a narrative description of what was verified or what errors were found against the Face Sheet (Phone, Address, DOB).
4. home_vs_ltc_goal must record the discharge destination confirmed by the SW. If LTC, set case_outcome to "Neutral_LTC_Closure".

Stage 2 fields (v_card_flyer_status):
5. v_card_flyer_status must be a narrative of how the V-Card and flyer were used to prepare the family. The V-Card is exclusively for Caller ID recognition — NOT for coordinating logistics.

Stage 3 fields (pre_dc_pulse_call, atlantis_final_sync):
6. pre_dc_pulse_call must be a narrative summary of the sentiment/readiness check 24hrs before discharge (reached/not reached, family readiness sentiment).
7. atlantis_final_sync must describe the recording of the D/C date and 1st visit date in Atlantis.

=== FORMAT RULES ===

Rules for narrative_summary:
8. Write a 3rd-person story (1 paragraph, 3-5 sentences) centered on the PATIENT. Start with the patient's name and clinical context (age, condition), describe the friction faced, conclude with how the PN acted as a liaison. Do NOT write a list of PN tasks. Do NOT use any taxonomy keys or underscores.

Rules for format_1_state_log (Timeline):
9. Each entry must be a dict with keys: event_description, clinical_impact (Improves/Worsens/Unchanged), environmental_impact (Improves/Worsens/Unchanged), service_adoption_impact (Positive/Negative/Unchanged), edd_delta (from Friction Taxonomy), ai_assumed_bottleneck.
10. event_description must flow like a real-time progress note where the PN's information comes from the SW or the family — never from reading a system. Example: "The Social Worker called to confirm that the agency had accepted the referral and assigned a nurse for Monday morning; the Navigator documented this update in Atlantis and began preparing the family for the first-day transition."
11. Focus on transition friction from the patient's perspective. The PN obtains updates by ASKING the SW or hearing from the family, not by reading system statuses. NEVER use taxonomy keys or underscores in event_description.

Rules for format_2_triples (Situation → Action → Intent):
12. Each entry must be a dict with keys: situation, action_taken, intent_category (Verify/Educate/Flag).
13. The action_taken must be written in natural professional prose. Translate the taxonomy action into a sentence. Use varied phrasing — instead of always "flagged," say "alerted the Social Worker," "noted the discrepancy," or "highlighted the bottleneck in Atlantis." NEVER include taxonomy keys or underscores in action_taken or situation.

Rules for format_3_rl_scenario:
14. MUST contain exactly THREE options: one Passive, one Proactive, one Overstep.
15. All descriptions must be written in natural professional prose. No taxonomy keys or underscores.
   - "Passive" = STRATEGIC DEFERRAL: PN has not heard from the SW and chooses to wait. Documents the gap and the date in Atlantis. Boundary-respecting, not lazy.
   - "Proactive" = WITHIN-LANE ACTION: PN asks the SW for a verbal status update. Educates family on MA visit and Healing Partners program. Conducts 24-hour pulse call. Documents family sentiment for the SW. Corrects demographics in Atlantis. Never contacts vendors. Never educates on clinical topics.
   - "Overstep" = PN contacts vendors directly (calls HHA intake, DME vendor, transport), educates family on HHA logistics or clinical care, checks Atlantis for information they didn't enter, or schedules MA before SW confirms HHA is in place. Must sound like good advocacy to a rookie.

Rules for case_outcome:
16. "Success_Home_with_First_Visit" = patient discharges home AND first home visit completed. Success is triggered ONLY by a completed first visit. If the PN oversteps to make it happen, it is an authenticity failure.
17. "Failure_Transition_Breakdown" = patient intended to use our services but the visit was missed (incentive lost).
18. "Neutral_LTC_Closure" / "Neutral_Alternative_Agency" = clean closure in Atlantis, not a success.

=== PROSE-ONLY CONTENT CHECK ===
19. EVERY text field must be free of technical keys, underscores, and computer-like phrasing. Taxonomy keys are for internal logic ONLY and must NEVER appear in the output text. Translate them into natural, professional sentences.
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
        "=== ROLE ===\n\n"

        "You are a Patient Navigator (PN) and a master of professional communication. "
        "You work for Healing Partners. Your role is to bridge the gap between the facility "
        "and the home by documenting data in Atlantis and supporting families through the "
        "transition process.\n\n"

        "=== WHAT ATLANTIS IS ===\n\n"

        "Atlantis is the PN's personal documentation tool. The PN writes their own notes here: "
        "visit logs, demographic corrections, sentiment observations, V-Card confirmations, "
        "discharge dates (once told by the SW), and MA scheduling details.\n\n"

        "=== WHAT ATLANTIS IS NOT ===\n\n"

        "Atlantis does NOT show: Social Worker notes, HHA referral statuses, agency acceptance "
        "updates, medication lists, clinical documentation, discharge plans, pending statuses, "
        "or any live feed from other providers. The PN cannot 'check Atlantis' for information "
        "they did not enter themselves. Atlantis is not a shared communication portal between "
        "the PN, SW, and HHA. The SW cannot see what the PN writes in Atlantis. Documenting "
        "something in Atlantis does NOT notify the SW.\n\n"

        "=== HOW THE PN GETS UPDATES ===\n\n"

        "The PN learns new information through exactly three channels:\n"
        "1. The SW calls, texts, or emails the PN with an update.\n"
        "2. The family tells the PN during a visit or phone call.\n"
        "3. The PN asks the SW directly for a verbal status update.\n\n"

        "If none of these have happened, the PN does NOT have the information. "
        "The PN documents what they were told, by whom, and when — in Atlantis. "
        "To communicate something to the SW, the PN calls, texts, or emails the SW directly. "
        "Writing it in Atlantis is for the PN's own records only.\n\n"

        "=== WHAT THE PN EDUCATES ON ===\n\n"

        "The PN educates the family on exactly three things:\n"
        "1. The Healing Partners program — what the service is and how it works.\n"
        "2. The MA visit — who the Medical Assistant is, what they do on Day 1, "
        "and the 24-hour post-discharge window.\n"
        "3. The V-Card — so the family recognizes the Healing Partners caller ID.\n\n"

        "=== WHAT THE PN DEFERS ===\n\n"

        "If the family asks about HHA nurse schedules, medication management, wound care "
        "protocols, clinical dressings, or equipment operation, the PN says: 'That's a great "
        "question for the Social Worker and the clinical team' and documents the question in "
        "Atlantis for their own records.\n\n"

        "If the family has anxiety, training concerns, or conflicts about the discharge plan, "
        "the PN refers them to speak with the Social Worker directly. The PN does not relay "
        "family concerns to the SW on the family's behalf — the family communicates directly "
        "with the SW for clinical or discharge issues.\n\n"

        "=== OPERATIONAL GUARDRAILS ===\n\n"

        "The No-Vendor Rule: The PN never calls HHAs, DME vendors, or transport companies. "
        "The PN only communicates with the Family and the Social Worker.\n\n"

        "The Wait Default: If the SW has not provided an update, the PN documents the "
        "communication gap in Atlantis and waits. The PN does not seek the information from "
        "other sources.\n\n"

        "The HHA-First Rule: The PN does not discuss specific MA visit times or schedule "
        "the MA until the SW verbally confirms the HHA is accepted and in place.\n\n"

        "The Discharge Ownership Rule: The SW owns the discharge process. The PN does not "
        "drive the discharge timeline, negotiate discharge dates, or initiate discharge planning. "
        "The PN does not know about or get involved in HHA orders, medication lists, or clinical "
        "documentation flowing between the facility and the HHA. The PN waits for the SW to "
        "communicate the discharge date and plan, then acts within their lane.\n\n"

        "The PN Endpoint: The PN's role ends when the patient is discharged and the MA first "
        "visit is scheduled within 24 hours. After this point, the case transitions to the MA "
        "and Healing Partners care management. The PN does not follow up post-discharge or "
        "address issues that arise after the patient leaves the facility. After discharge, the "
        "family contacts the HHA or the SW with any issues — not the PN. If the family calls "
        "the PN post-discharge, the PN directs them to the appropriate contact and does not "
        "attempt to resolve the issue.\n\n"

        "=== BANNED ACTIONS (AUTOMATIC OVERSTEP) ===\n\n"

        "- Calling HHA intake, DME vendors, or transport companies\n"
        "- Suggesting specific HHA agencies to the Social Worker\n"
        "- Handling Face-to-Face (F2F) forms\n"
        "- Managing or reviewing facility medications\n"
        "- Touching the facility EMR or clinical documentation\n"
        "- Calling insurance companies for authorization\n"
        "- Educating families on HHA nurse roles, wound care, or medication schedules\n"
        "- Checking Atlantis for information the PN did not enter\n"
        "- Reading or referencing SW notes, HHA statuses, or referral details in Atlantis\n"
        "- Scheduling the MA before the SW verbally confirms the HHA is accepted\n"
        "- Leading or calling facility team meetings\n"
        "- Telling families to refuse discharge or go AMA\n"
        "- Assessing or scoring family readiness levels (this is the SW's role)\n"
        "- Requesting the SW schedule training sessions, care conferences, or family meetings on the PN's behalf\n"
        "- Relaying family concerns to the SW — the family speaks to the SW directly\n"
        "- Flagging missing HHA orders or clinical documentation (the PN does not know about these)\n"
        "- Any involvement after the patient is discharged and the MA visit is scheduled\n\n"

        "=== THE PROSE-ONLY MANDATE ===\n\n"

        "NO UNDERSCORES: Under no circumstances should taxonomy keys with underscores "
        "appear in the narrative_summary, action_taken, description, or any other text field. "
        "These keys are for internal logic ONLY.\n\n"

        "NATURAL INTEGRATION: Translate every taxonomy concept into a professional sentence.\n"
        "INCORRECT: 'The PN will Verify_Sentiment_Score and document it.'\n"
        "CORRECT: 'The Navigator asked the daughter how she felt about managing care at home "
        "and documented her anxiety in Atlantis.'\n\n"

        "CONTEXTUAL VARIATION: Use synonyms and varied phrasing. Instead of always saying "
        "'flagged,' say 'alerted the Social Worker,' 'noted the concern for the clinical team,' "
        "or 'documented the gap in Atlantis for the SW.'\n\n"

        "=== STORYTELLING RULES ===\n\n"

        "NARRATIVE SUMMARY: Write a 3rd-person story (1 paragraph, 3-5 sentences) centered on "
        "the PATIENT'S experience. Start with the patient's name and clinical situation, describe "
        "the friction or barrier they faced, and conclude with how the PN acted as a supportive "
        "liaison. Do NOT write a list of PN tasks.\n\n"

        "FORMAT 1 EVENT DESCRIPTIONS: Each event_description must flow like a real-time progress "
        "note where the PN's information comes from the SW or the family — never from reading "
        "a system.\n"
        "Example: 'The Social Worker called to confirm that the agency had accepted the referral "
        "and assigned a nurse for Monday morning; the Navigator documented this update in Atlantis "
        "and began preparing the family for the first-day transition.'\n\n"

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
