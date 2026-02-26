"""
Phase 2: Orchestrated Synthetic Case Generation

Queries ChromaDB for few-shot seed cases, injects static Taxonomies, and
calls the Gemini LLM to generate a high-fidelity synthetic patient case.
Output is validated via Pydantic and saved to ./data/synthetic_output/.

Usage:
    export GEMINI_API_KEY=""
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
from typing import List, Literal


# ── Configuration ────────────────────────────────────────────────────────────

CHROMA_DB_PATH     = "./chroma_db"
COLLECTION_NAME    = "seed_cases"
TAXONOMIES_DIR     = "./data/taxonomies"
OUTPUT_DIR         = "./data/synthetic_output"
MODEL_NAME         = "gemini-3-flash-preview"

# Target variables for this generation run (override via env vars or edit here)
TARGET_COMPLEXITY_GTE  = int(os.environ.get("COMPLEXITY_GTE", 4))
TARGET_FRICTION        = os.environ.get("FRICTION_BARRIER", "Managed Medicare Auth")
TARGET_PATIENT_DESC    = os.environ.get("PATIENT_DESC", "78yo Female, CHF")
N_FEW_SHOT_EXAMPLES    = 2
BATCH_SIZE             = int(os.environ.get("BATCH_SIZE", 1))


# ── Pydantic Output Schema (Section 2.3) ─────────────────────────────────────

class StateLogEntry(BaseModel):
    event_description: str = Field(description="Describe the event, including specific institutional friction.")
    clinical_impact: Literal["Improves", "Worsens", "Unchanged"]
    environmental_impact: Literal["Improves", "Worsens", "Unchanged"]
    service_adoption_impact: Literal["Positive", "Negative", "Unchanged"]
    edd_delta: str = Field(description="Must match Friction Taxonomy rule, e.g., '+30 Days'")
    ai_assumed_bottleneck: str = Field(description="The specific human or systemic reason for the delay (e.g., 'SW ignored emails because it was Friday at 4 PM').")


class ReasoningTriple(BaseModel):
    situation: str = Field(description="The specific barrier, conflict, or institutional friction.")
    action_taken: str = Field(description="The tactical, specific action the PN took to solve it.")
    taxonomy_category: str = Field(description="Must match exactly with an intent from the Action Taxonomy.")
    tactical_field_intent: str = Field(description="The unwritten, political, or highly specific secondary motive behind the action (e.g., 'Force a verbal commitment without leaving an aggressive email trail').")


class RLScenarioOption(BaseModel):
    ai_intended_category: Literal["Passive", "Proactive", "Overstep"] = Field(description="The hidden classification. Do not reveal this in the description.")
    description: str = Field(description="The exact action taken by the PN. It MUST sound professional and clinically appropriate, even if it is technically a passive move or a boundary overstep.")
    rationale: str = Field(description="The hidden explanation of why the AI classified it this way (e.g., explaining exactly whose toes are stepped on for an Overstep).")


class SyntheticCaseOutput(BaseModel):
    format_1_state_log: List[StateLogEntry]
    format_2_triples: List[ReasoningTriple]
    format_3_rl_scenario: List[RLScenarioOption]
    narrative_summary: str


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

--- Action Taxonomy (defines Rank 1 success intents) ---
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

Rules:
1. All edd_delta values must reference a delay from the Friction Taxonomy.
2. The `ai_assumed_bottleneck` must be a specific, testable claim about a HOME HEALTH TRANSITION barrier (e.g., "The HHA could not schedule a weekend admission because their intake coordinator only works Mon-Fri").

NEGATIVE CONSTRAINTS (What a PN NEVER does):
- The PN NEVER touches F2F forms, clinical documentation, or the EMR.
- The PN NEVER calls insurance companies for authorization.
- The PN NEVER calls or leads facility team meetings.
- The PN NEVER interrupts doctors during rounds or gathers charts from the nurse's station.
- The PN NEVER proves cost analysis of home care vs LTC.
- The PN NEVER tells families to refuse discharge or go Against Medical Advice (AMA).

POSITIVE CONSTRAINTS (What a PN ACTUALLY does):
- The PN focuses entirely on Home Health Agency (HHA) coordination and transition logistics.
- Valid PN friction includes: HHA weekend admission scheduling limits, delays in Durable Medical Equipment (DME) delivery to the home, family caregiver training gaps, or discrepancies in the medication list at handoff.

Rules for Format 2 (Triples):
3. The `situation` must involve a specific stakeholder bottleneck WITHIN THE PN's SCOPE (e.g., HHA not returning calls, DME vendor backordered, family caregiver not trained on wound care, medication list mismatch between facility and home).
4. The `action_taken` must be a specific field maneuver that a PN would realistically take, not a Social Worker action.
5. The `tactical_field_intent` MUST contain a political or operational trade-off that a 20-year PN veteran could debate. Use PN-specific motives (e.g., 'Lock in the HHA admission slot before the weekend so the discharge does not slip to Monday').

Rules for Format 3 (RL Scenarios):
6. The format_3_rl_scenario MUST contain exactly THREE options for a single difficult dilemma.
7. You must generate one "Passive" option, one "Proactive" option, and one "Overstep" option.
8. CRITICAL: The `description` for all three options must sound highly professional, reasonable, and tempting.
   - "Passive" means the PN waits for the SW/facility to handle everything and fails to follow up on HHA setup or home equipment.
   - "Proactive" means the PN takes a great field action WITHIN THEIR SCOPE (e.g., confirming the HHA admission date, verifying supplies are waiting at home, educating the family on what to expect on Day 1, checking weekend HHA availability).
   - "Overstep" MUST feature the PN accidentally doing the Social Worker's job (e.g., handling discharge documentation, confronting facility staff, calling the patient's insurance, or drafting clinical notes). It must still sound like good patient advocacy to a rookie.
9. narrative_summary must be 3-5 sentences capturing the home health transition arc, not the facility discharge process.
10. Output ONLY the JSON object. Do not include markdown fences, explanation, or commentary.
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

    # Configure Gemini
    genai.configure(api_key=api_key)
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
        "You are an AI Healthcare Architect generating highly authentic synthetic cases "
        "for 20-year non-clinical Patient Navigator veterans. You must strictly adhere to the Static Taxonomies.\n\n"
        "CRITICAL ROLE DEFINITION: The Patient Navigator is NOT a discharge planner, NOT a social worker, "
        "and NOT a clinician. The PN enters the picture specifically to ensure a smooth transition to home "
        "health care AFTER the facility handles the clinical discharge. The PN is a collaborative team member "
        "who works WITH the facility, never against them.\n\n"
        "BANNED TROPES: You MUST NOT use the following repetitive phrases or concepts: "
        "'F2F / Face-to-Face signatures', 'burned-out Social Worker', '100-day financial cliff', "
        "'Private pay to LTC', or 'Black Hole'."
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
