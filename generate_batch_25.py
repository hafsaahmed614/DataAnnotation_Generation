"""Generate 25 synthetic cases with randomized patients and frictions."""
import json, os, random, time
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
from generate_synthetic import (
    load_taxonomy, retrieve_few_shot_examples, build_prompt,
    SyntheticCaseOutput, MODEL_NAME, CHROMA_DB_PATH, COLLECTION_NAME,
    TAXONOMIES_DIR,
)
import chromadb

OUTPUT_DIR = "./data/synthetic_batch_25"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PATIENTS = [
    "88yo Male, Bilateral TKA",
    "78yo Female, CHF",
    "65yo Male, COPD exacerbation",
    "72yo Female, Hip fracture ORIF",
    "81yo Male, Stroke rehab",
    "69yo Female, Diabetic wound care",
    "75yo Male, Cardiac bypass recovery",
    "83yo Female, Pneumonia post-ICU",
    "70yo Male, Spinal fusion",
    "77yo Female, Renal failure transition",
    "86yo Male, Dementia with fall history",
    "74yo Female, Cancer post-chemo rehab",
    "79yo Male, Amputation rehab",
    "68yo Female, Multiple sclerosis flare",
    "82yo Male, Parkinson's with UTI",
]

FRICTIONS = [
    "Medicaid CHC Waiver",
    "Provider Illness",
    "Loss of Skilled Need",
    "HHA_Intake_Freeze",
    "DME_Delivery_Failure",
    "HHA Intake Coordinator Unavailable",
    "Caregiver Training Gap",
    "Handoff_Data_Mismatch",
    "Home Safety Assessment Pending",
    "HHA Staffing Shortage",
    "Insurance-HHA Network Mismatch",
    "Family Disagreement on Discharge Plan",
    "Transport Coordination Failure",
    "Missing HHA Orders at Handoff",
    "Holiday Coverage Gap",
    "Caregiver_Panic",
    # V5 additions
    "Atlantis_Data_Lag",
    "Friday Discharge Gap",
    "Day 1 Home No-Show",
    "LTC_Pivot_Abort",
    "Pre-DC_Call_Disconnect",
    "HHA_SOC_Overlap",
    # V7 additions
    "HHA_Acceptance_Stall",
    "Sentiment_Readiness_Gap",
    # V8 additions
    "Family_Training_Gap_Anxiety",
    "Liaison_Communication_Silo",
]

# Patient-choice frictions (used to enforce ~30% patient/family-driven cases)
PATIENT_CHOICE_FRICTIONS = [
    "Caregiver_Panic",
    "Family Disagreement on Discharge Plan",
    "Caregiver Training Gap",
    "LTC_Pivot_Abort",
    "Family_Training_Gap_Anxiety",
]


def _build_unique_combos(patients, frictions, n=25, patient_choice_frictions=None, patient_choice_slots=8):
    """Build n unique (patient, friction) pairs with ~30% patient-choice enforcement.

    Reserves `patient_choice_slots` for patient/family-driven frictions,
    fills the rest with non-patient-choice frictions. No duplicate combos.
    """
    import itertools

    if patient_choice_frictions is None:
        patient_choice_frictions = []

    pc_set = set(patient_choice_frictions)
    pc_frictions = [f for f in frictions if f in pc_set]
    non_pc_frictions = [f for f in frictions if f not in pc_set]

    # Build patient-choice combos
    pc_combos = list(itertools.product(patients, pc_frictions))
    random.shuffle(pc_combos)
    pc_selected = pc_combos[:patient_choice_slots]

    # Build non-patient-choice combos
    non_pc_combos = list(itertools.product(patients, non_pc_frictions))
    random.shuffle(non_pc_combos)
    non_pc_selected = non_pc_combos[:(n - len(pc_selected))]

    combined = pc_selected + non_pc_selected
    random.shuffle(combined)
    return combined[:n]


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key, transport="rest")
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.8,
        ),
    )

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    friction_taxonomy = load_taxonomy("friction_taxonomy.json")
    action_taxonomy = load_taxonomy("action_taxonomy.json")
    outcome_taxonomy = load_taxonomy("outcome_taxonomy.json")

    system_prompt = (
        "You are a Patient Navigator (PN) operating in the Atlantis software environment. "
        "Your goal is to ensure a safe transition home to trigger the First Visit incentive.\n\n"

        "=== OPERATIONAL GUARDRAILS ===\n\n"

        "The Atlantis Rule: All PN workflow originates and is documented in Atlantis. "
        "The PN NEVER touches facility EMR or handles clinical documentation.\n\n"

        "The LTC Filter: The PN's first action is always asking the Social Worker (SW): "
        "'Is the goal Home or LTC?' If LTC, the PN performs a neutral closure in Atlantis "
        "and stops work to avoid stepping on toes.\n\n"

        "The Pitch & Retreat: The PN introduces the program, leaves a card, tells the SW "
        "the patient is interested, and then waits for the SW to build the case.\n\n"

        "Banned Actions (Automatic Overstep): Suggesting alternative agencies to the SW, "
        "handling Face-to-Face (F2F) forms, calling insurance for authorizations, "
        "or managing facility-level medications.\n\n"

        "Success Metric: Success is defined solely by the patient discharging with our services "
        "and the first home visit post-discharge being successfully completed.\n\n"

        "=== STORYTELLING RULES ===\n\n"

        "NARRATIVE SUMMARY: Write a 3rd-person story (1 paragraph, 3-5 sentences) centered on the PATIENT'S "
        "experience. Start with the patient's clinical context (age, condition), describe the friction or barrier "
        "they faced, and conclude with how the PN acted as a supportive liaison. "
        "Do NOT write a list of PN tasks.\n\n"

        "FORMAT 1 EVENT DESCRIPTIONS: Each event_description must be a chronological narrative event — "
        "what happened to the patient at that moment. Do NOT use category labels or task names as descriptions.\n\n"

        "=== INTEGRATED V8 TAXONOMY ACTIONS ===\n"
        "The PN must select from these specific high-fidelity actions where appropriate:\n"
        "- Confirm_Caller_ID_Readiness: Insert V-Card so patient recognizes Healing Partners call.\n"
        "- Verify_Sentiment_Score: Check family anxiety levels (1-10) without clinical interference.\n"
        "- Liaison_Reporting_Only: Documentation-only mode; writing down the SW's plan in Atlantis.\n"
        "- Verify_HHA_Acceptance_via_Portal: Use digital tools to check status instead of calling vendors.\n"
        "- Request_Joint_Family_Meeting_via_SW: Ask SW to include PN in a family update call.\n"
        "- Maintain_Granular_Wait-Status_Timeline: Keep a running log in Atlantis of the waiting phase.\n\n"

        "=== INTEGRATED V8 TAXONOMY FRICTIONS ===\n"
        "Cases must feature friction from these categories where appropriate:\n"
        "- HHA_Acceptance_Stall: Referral sent but agency hasn't responded in the portal.\n"
        "- Sentiment_Readiness_Gap: Family or patient emotional hesitation about going home.\n"
        "- Family_Training_Gap_Anxiety: Anxiety from lack of facility training on clinical tasks.\n"
        "- Liaison_Communication_Silo: PN excluded from a transition meeting.\n"
        "- Atlantis_Data_Lag: Outdated demographic info requiring manual update.\n\n"

        "FOG OF WAR: The PN always acts on INCOMPLETE information. At least one critical "
        "detail must be unknown, delayed, or contradictory.\n\n"

        "PATIENT CHOICE: Some cases must feature friction driven by patient or family decisions.\n\n"

        "BANNED TROPES: 'F2F / Face-to-Face signatures', 'burned-out Social Worker', "
        "'100-day financial cliff', 'Private pay to LTC', 'Black Hole'."
    )

    # Build 25 unique (patient, friction) combos — 8 patient-choice, 17 other
    combos = _build_unique_combos(PATIENTS, FRICTIONS, n=25,
                                  patient_choice_frictions=PATIENT_CHOICE_FRICTIONS,
                                  patient_choice_slots=8)
    print(f"Generated {len(combos)} unique patient-friction combinations.\n")

    successes = 0
    failures = 0

    for i, (patient, friction) in enumerate(combos):
        print(f"\n--- Case {i+1}/25 --- Patient: {patient} | Friction: {friction}")

        query_text = f"Bureaucratic delay with {friction} and clinical barriers"
        examples = retrieve_few_shot_examples(collection, complexity_gte=4, query_text=query_text, n=2)
        user_prompt = build_prompt(friction_taxonomy, action_taxonomy, outcome_taxonomy, examples, patient, friction)

        for attempt in range(3):
            try:
                response = model.generate_content(
                    contents=[{"role": "user", "parts": [system_prompt + "\n\n" + user_prompt]}]
                )
                raw = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                data = json.loads(raw)
                validated = SyntheticCaseOutput.model_validate(data)

                out_path = os.path.join(OUTPUT_DIR, f"case_{i+1:02d}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(validated.model_dump(), f, indent=2)

                print(f"  OK -> {out_path}")
                successes += 1
                break
            except Exception as e:
                err = str(e)
                if "429" in err or "rate" in err.lower():
                    wait = 60 * (attempt + 1)
                    print(f"  Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  ERROR (attempt {attempt+1}): {err[:200]}")
                    if attempt == 2:
                        failures += 1
                    else:
                        time.sleep(5)

        time.sleep(2)  # small delay between calls

    print(f"\nDone. Successes: {successes}, Failures: {failures}")

if __name__ == "__main__":
    main()
