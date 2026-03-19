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
    "HHA Intake Coordinator Unavailable",
    "Caregiver Training Gap",
    "Handoff_Data_Mismatch",
    "HHA Staffing Shortage",
    "Family Disagreement on Discharge Plan",
    "Transport Coordination Failure",
    "Missing HHA Orders at Handoff",
    "Holiday Coverage Gap",
    "Caregiver_Panic",
    "Atlantis_Data_Lag",
    "Friday Discharge Gap",
    "Day 1 Home No-Show",
    "LTC_Pivot_Abort",
    "Pre-DC_Call_Disconnect",
    "HHA_SOC_Overlap",
    "HHA_Acceptance_Stall",
    "Sentiment_Readiness_Gap",
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
        "the PN, SW, and HHA.\n\n"

        "=== HOW THE PN GETS UPDATES ===\n\n"

        "The PN learns new information through exactly three channels:\n"
        "1. The SW calls, texts, or emails the PN with an update.\n"
        "2. The family tells the PN during a visit or phone call.\n"
        "3. The PN asks the SW directly for a verbal status update.\n\n"

        "If none of these have happened, the PN does NOT have the information. "
        "The PN documents what they were told, by whom, and when — in Atlantis.\n\n"

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
        "Atlantis for the SW's awareness.\n\n"

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
        "The PN waits for the SW to communicate the discharge date and plan, then acts within "
        "their lane.\n\n"

        "The PN Endpoint: The PN's role ends when the patient is discharged and the MA first "
        "visit is scheduled within 24 hours. After this point, the case transitions to the MA "
        "and Healing Partners care management. The PN does not follow up post-discharge or "
        "address issues that arise after the patient leaves the facility.\n\n"

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
        "- Telling families to refuse discharge or go AMA\n\n"

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
