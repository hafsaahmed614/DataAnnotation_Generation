This markdown guide serves as the **Standard Operating Procedure (SOP)** for your synthetic data generation. It bridges the gap between the raw taxonomies and the final, high-quality JSON outputs by using a **"Matrix-Randomization"** approach.

---

# SOP: Systematic Synthetic Case Generation (Matrix-Randomization)

## 1. The Core Philosophy
To generate **560+ unique logical arcs**, we do not rely on AI "creativity." Instead, we treat the taxonomies as a coordinate system. A case is defined as the intersection of three specific points:
1.  **A Friction Point** (The Problem)
2.  **A Logic Gate** (The Constraint)
3.  **An Outcome** (The Result)

## 2. The Logic Gate Framework
Before randomizing, the generator must respect these three "Gates" to prevent high-quality "collisions" (logical errors).

| Gate Name | Applicable Frictions | Valid Outcomes |
| :--- | :--- | :--- |
| **The Recovery Gate** | Operational, Family/Caregiver, Logistical | Success, Failure, Alt Agency |
| **The Hard Stop Gate** | Eligibility (Loss of Skilled Need), Administrative | Failure, Neutral_LTC_Closure |
| **The Pivot Gate** | LTC_Pivot_Abort, Sentiment_Readiness_Gap | Neutral_LTC_Closure |



---

## 3. The 3-Step Generation Workflow

### Step A: Coordinate Selection (The "Seed")
Randomly select one item from each taxonomy, ensuring they pass the **Logic Gate** check.
* **Pick 1 Friction:** (e.g., `HHA_Acceptance_Stall`)
* **Pick 1 Outcome:** (e.g., `Success_Home_with_First_Visit`)
* **Pick 2-3 Actions:** (e.g., `Audit Atlantis demographics`, `Verify_Wound_Qualification`, `Schedule the MA`)

### Step B: The "Fog of War" Injection
To prevent repetitive stories, every case must have one **Information Gap**. Randomly assign one of the following "Missing" variables to the PN:
* **Missing HHA Name:** PN knows someone is coming, but doesn't know who.
* **Missing D/C Time:** PN knows the day, but the SW hasn't confirmed the "Med-Van" window.
* **Missing Contact:** The phone number in Atlantis is disconnected; PN is "Waiting" for SW to provide a new one.

### Step C: Prose Expansion (The "Skinning")
The AI takes the coordinates and the gap and "skins" them into a professional narrative.
* **Constraint:** The PN must stay "In-Lane" (No vendor calls, no clinical advice).
* **Tone:** Professional, 3rd-person, progress-note style.

---

## 4. Permutation Math (Excluding Personas)
By focusing purely on the logical combinations of your current taxonomies:

* **Primary Arcs:** 21 Frictions $\times$ (Weighted) Outcomes $\approx$ **75-80 Base Scenarios.**
* **Action Combinations:** Each Base Scenario can be paired with ~7 different "Action Groupings" (Stage 1 focus vs. Stage 3 focus).
* **Total High-Quality Logical Arcs:** **~560 Unique Permutations.**

---

## 5. Quality Control & Guardrails
To ensure the 560 cases are usable for human navigators, the following "Banned Logic" must be enforced during generation:

> **The "Kidnapping" Rule:** The AI cannot "force" a Success Outcome if the Friction is a Hard Stop (LTC Pivot).
>
> **The "Vendor Silence" Rule:** The PN never speaks to an HHA. If the case requires HHA info, the PN must get it from the **SW** or the **Family**.
>
> **The "Endpoint" Rule:** No narrative can take place *after* the first MA visit is scheduled. The PN's world ends at the handoff.

---

## 6. Systematic Batching Strategy
When generating in bulk, use "Tranches" to maintain diversity:
1.  **Tranche 1 (The "Clean" 100):** Focus on Operational Frictions leading to Success.
2.  **Tranche 2 (The "Messy" 100):** Focus on Family/Caregiver Frictions leading to Success/Failure.
3.  **Tranche 3 (The "Closures" 100):** Focus on Administrative/Eligibility Frictions leading to Neutral/LTC.

---

**Next Steps for Implementation:**
* Use this Markdown as a "System Instruction" prefix when starting a new generation session.
* Begin with **Tranche 1** to calibrate the AI's understanding of the "Wait Default" and "HHA-First" rules.
