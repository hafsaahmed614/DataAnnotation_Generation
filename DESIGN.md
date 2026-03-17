This `DESIGN.md` serves as the master blueprint for the Patient Navigator (PN) AI ecosystem. It integrates the synthetic data generation strategy (the Flywheel) with the multi-mode assistant architecture (the Universal Chatbot).

---

# DESIGN.md: Patient Navigator AI Ecosystem

## 1. Executive Summary

The goal of this project is to build a specialized AI Assistant for Patient Navigators (PNs) that ensures role-boundary compliance, data hygiene, and successful patient transitions. The project uses a "Synthetic Data Flywheel" to generate high-fidelity training data, which is then used to prompt, evaluate, and eventually fine-tune a multi-mode PN Chatbot.

---

## 2. The Data Flywheel Architecture

The Flywheel is the engine that generates the professional "standard of truth" for the AI.

### 2.1 Synthetic Generation (Version 10+)

* **Narrative Style:** 3rd-person, patient-centered storytelling (Mrs. Smith's journey) rather than a task list.
* **Prose Mandate:** All outputs must use professional, field-ready language. Technical keys (e.g., `Verify_Sentiment_Score`) and underscores are strictly forbidden in user-facing fields.
* **Role Boundaries:** PNs are defined as **Liaisons and Auditors**, not Logistical Fixers.

### 2.2 Human-in-the-Loop (HITL) Alignment

* **Ranking (1–5):** Veteran PNs evaluate cases.
* **Masterful Moves (Rank 5):** These are isolated as positive training data.
* **Electric Fences (Rank 1–2):** These are isolated as negative constraints (the "what NOT to do" dataset).

---

## 3. Universal Chatbot Assistant: The 5 Modes

The assistant is designed as a "Router" architecture. A central controller interprets user input and activates one of five specialized sub-agents.

| Mode | AI Technique | Role in Field |
| --- | --- | --- |
| **1. Boundary Guard** | Few-Shot Classification | Warns the PN if an intended action oversteps into Social Worker (SW) territory. |
| **2. Sentiment Translator** | Intent Extraction (NER) | Converts patient/family quotes into actionable friction data for Atlantis. |
| **3. Atlantis Auditor** | OCR & Data Extraction | Cross-references physical "Face Sheets" against digital Atlantis records for errors. |
| **4. Political Navigator** | RAG (Retrieval) | Drafts professional, non-confrontational scripts for SW or family communication. |
| **5. Checklist Sentinel** | State Machine Logic | Tracks the 3-Stage Lifecycle to ensure no milestones (e.g., V-Card insertion) are missed. |

---

## 4. Implementation Strategy

### 4.1 Phase 1: Prompt Engineering & RAG (Current)

* Use the "Golden Cases" (Rank 5) as examples in the Chatbot's prompt.
* Use the "Boundary Failures" (Rank 1-2) to build hard constraints.

### 4.2 Phase 2: Modular Testing

* Build and test each of the 5 modes as standalone "mini-bots" to ensure the logic for one (e.g., Auditor) doesn't conflict with another (e.g., Navigator).

### 4.3 Phase 3: Fine-Tuning (Target: 200+ Rank 5 Cases)

* **Technique:** Direct Preference Optimization (DPO).
* **Goal:** "Bake" the Liaison persona into the model's weights so it naturally avoids overstepping without needing a massive instruction prompt.

---

## 5. Strategy for the Next 25-Case Batches (Edge Case Focus)

To harden the AI, we will move away from "standard" cases and force the generator to create "Stress Tests":

1. **The Aggressive SW:** Focus on political boundaries. How does the PN maintain data hygiene in Atlantis when the facility staff is uncooperative?
2. **The Ghosting HHA:** Focus on the "Wait" default. How does the PN proactively flag a delay to the SW when an agency goes silent for 48+ hours?
3. **The Complex Handoff:** Focus on `Handoff_Data_Mismatch`. Generate scenarios with conflicting medication lists, allergy errors, or complex equipment needs (Oxygen + Wound Vac + CPAP).

---

## 6. Organized List of Future Tasks

### **Data & Generation Tasks**

* [ ] Execute **Batch 11 (25 cases)** focusing on "The Aggressive SW" edge case.
* [ ] Execute **Batch 12 (25 cases)** focusing on "The Ghosting HHA."
* [ ] Execute **Batch 13 (25 cases)** focusing on "Complex Handoffs/Medication Mismatches."
* [ ] Develop a script to automatically format "Rank 5" cases into a **JSONL Fine-Tuning Dataset**.

### **Assistant Development Tasks**

* [ ] Build the **Boundary Guard Prototype**: Create a prompt that specifically references "Overstep" examples from V6 failed cases.
* [ ] Build the **Political Navigator Prototype**: Create a RAG system that retrieves "Masterful Field Move" scripts based on PN queries.
* [ ] Develop the **Checklist Sentinel State-Tracker**: A simple UI or logic flow that remembers which stage a case is currently in.

### **Evaluation & Refinement**

* [ ] Conduct a "Bot Stress Test" with Melissa to see if the Boundary Guard can catch intentional overstepping.
* [ ] Review Batch 11-13 for "Prose Legibility" to ensure Version 10's anti-bot-speak rules are holding.

Would you like me to begin by drafting the specific "Aggressive SW" prompt for the next batch of 25 cases?
