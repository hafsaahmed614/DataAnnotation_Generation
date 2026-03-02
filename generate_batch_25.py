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
]

# Patient-choice frictions (used to enforce ~30% patient/family-driven cases)
PATIENT_CHOICE_FRICTIONS = [
    "Caregiver_Panic",
    "Family Disagreement on Discharge Plan",
    "Caregiver Training Gap",
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
        "You are an AI Healthcare Architect generating highly authentic synthetic cases "
        "for 20-year non-clinical Patient Navigator veterans. You must strictly adhere to the Static Taxonomies.\n\n"
        "CRITICAL ROLE DEFINITION: The Patient Navigator is NOT a discharge planner, NOT a social worker, "
        "and NOT a clinician. The PN enters the picture specifically to ensure a smooth transition to home "
        "health care AFTER the facility handles the clinical discharge. The PN is a collaborative team member "
        "who works WITH the facility, never against them.\n\n"
        "THE PN MENTALITY IS: SUPPORT, SUGGEST, AND ESCALATE.\n"
        "- SUPPORT: Verify HHA logistics, confirm equipment delivery, educate the family on Day 1 expectations.\n"
        "- SUGGEST: Present 2-3 pre-vetted alternatives to the SW when the primary plan falls through.\n"
        "- ESCALATE: Flag clinical, insurance, or volatile family issues to the SW immediately.\n\n"
        "FOG OF WAR DYNAMIC: The PN always acts on INCOMPLETE information. In every case, at least one critical "
        "detail must be unknown, delayed, or contradictory (e.g., the SW says discharge is Thursday but the HHA "
        "says they have no record of the referral; the family says the home has a ramp but the PN has not verified it). "
        "The PN must make decisions under uncertainty and cannot wait for perfect information.\n\n"
        "PATIENT CHOICE DYNAMIC: Not all friction is bureaucratic. Some cases must feature friction driven by "
        "patient or family decisions (e.g., caregiver refusing to learn wound care, family threatening to refuse "
        "discharge, patient changing their mind about going home). The PN must navigate these human dynamics "
        "while staying within scope.\n\n"
        "BANNED TROPES: You MUST NOT use the following repetitive phrases or concepts: "
        "'F2F / Face-to-Face signatures', 'burned-out Social Worker', '100-day financial cliff', "
        "'Private pay to LTC', or 'Black Hole'."
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
