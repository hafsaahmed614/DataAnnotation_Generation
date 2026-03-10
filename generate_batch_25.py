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
    "HHA_Acceptance_Lag",
    "Sentiment_Readiness_Gap",
]

# Patient-choice frictions (used to enforce ~30% patient/family-driven cases)
PATIENT_CHOICE_FRICTIONS = [
    "Caregiver_Panic",
    "Family Disagreement on Discharge Plan",
    "Caregiver Training Gap",
    "LTC_Pivot_Abort",
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
