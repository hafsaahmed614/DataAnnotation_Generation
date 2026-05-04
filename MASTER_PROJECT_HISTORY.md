# MASTER PROJECT HISTORY

**Project**: Healing Partners Patient Navigator (PN) Training Dataset
**Repositories**:
- `DataAnnotation_App` — Seed Case Collection (Streamlit intake)
- `DataAnnotation_Generation` — Synthetic Scaling + Qwen Auditor + RLHF Backend
**Owner**: hafsaahmed614
**Status**: Active — Streamlit Annotation UI live; RLHF data pipeline in motion
**Document Generated**: 2026-05-04

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Foundations](#2-project-foundations)
3. [Domain Context & The Patient Navigator Role](#3-domain-context--the-patient-navigator-role)
4. [Era 1 — Seed Case Collection (DataAnnotation_App)](#4-era-1--seed-case-collection-dataannotation_app)
5. [Era 2 — Synthetic Scaling (DataAnnotation_Generation)](#5-era-2--synthetic-scaling-dataannotation_generation)
6. [Era 3 — Automated AI Auditing (Qwen 2.5 2B Pipeline)](#6-era-3--automated-ai-auditing-qwen-25-2b-pipeline)
7. [The Evolved PN Taxonomy](#7-the-evolved-pn-taxonomy)
8. [Audit Guardrails — The Kill-Switch Rules](#8-audit-guardrails--the-kill-switch-rules)
9. [The Relational Backend (Streamlit Ready)](#9-the-relational-backend-streamlit-ready)
10. [The Streamlit Annotation Platform](#10-the-streamlit-annotation-platform)
11. [Supabase Backend & Schema Versioning](#11-supabase-backend--schema-versioning)
12. [Human-in-the-Loop & RLHF](#12-human-in-the-loop--rlhf)
13. [Iteration History — Pipeline Evolution](#13-iteration-history--pipeline-evolution)
14. [File & Data Pedigree](#14-file--data-pedigree)
15. [Roadmap — Next Phases](#15-roadmap--next-phases)

---

## 1. Executive Summary

The **Healing Partners Patient Navigator Training Dataset** is a multi-stage data curation pipeline that produces high-fidelity reasoning data for fine-tuning a domain-specialized PN model. The project has progressed through three distinct eras, each layered on the lessons of the prior:

- **Era 1 — Human Seed Data.** A Streamlit application (`DataAnnotation_App`) was built to capture historical SNF cases from veteran navigators, paired with three controlled taxonomies (Action, Friction, Outcome) that encode the "Liaison" voice and prevent advocacy drift.
- **Era 2 — Synthetic Scaling.** Seed cases were used to generate **406 synthetic cases** organized as `synthetic_batch_25` × **versions v1–v14**, each version representing a refinement of the system prompt and taxonomy. The evaluation surface evolved into three structured formats: a state log (Format 1), reasoning triples (Format 2), and RL-style boundary scenarios (Format 3).
- **Era 3 — Automated AI Auditing.** A small reasoning model — **Qwen 2.5 2B** — was deployed as an automated auditor over the synthetic corpus. The audit output was flattened into a relational backend (three CSVs) that powers a Streamlit Human Annotation UI, which itself is the on-ramp to **Level 1 Fine-Tuning** and **RLHF**.

The unifying thesis across all three eras: the PN role is a **liaison, not a clinician**, and every artifact in this pipeline — seed case, synthetic case, audit score, human annotation — is validated against a fixed set of "Kill-Switch" guardrails (No-Vendor, Wait Default, Discharge Ownership, PN Endpoint).

---

## 2. Project Foundations

### 2.1 Origin — Why This Dataset Exists

Healing Partners deploys Patient Navigators to bridge skilled nursing facilities (SNFs) and the home setting. Veteran navigators consistently identified two failure modes in early generic-LLM prototypes:
- **Political overstepping** — the model rewrote clinical plans, recommended vendors, and inserted advocacy where the navigator's role is documentation and education only.
- **Atlantis Illusion** — the model treated the navigator's documentation tool ("Atlantis") as a live clinical feed, behaving as if it had real-time visibility into SW notes, HHA statuses, and medication lists.

These failures motivated a custom dataset with explicit role boundaries and an evaluation surface that scores **boundary respect** as a first-class signal alongside clinical fidelity.

### 2.2 The Three-Era Progression

```
Era 1: Human Seed Data           Era 2: Synthetic Scaling         Era 3: Automated Auditing
─────────────────────            ──────────────────────           ─────────────────────────
DataAnnotation_App      ───►     synthetic_batch_25       ───►    Qwen 2.5 2B Auditor
Streamlit intake forms           v1 → v14                          Format 2 + Format 3
4 navigators × 7 cases           406 synthetic cases               Rationale-required CoT
3 taxonomies (JSON)              Format 1/2/3 evaluation           Relational flattening
                                                                    │
                                                                    ▼
                                                          Streamlit Annotation UI
                                                          f2 / f3 / macro CSVs
                                                                    │
                                                                    ▼
                                                          L1 Fine-Tuning + RLHF
```

### 2.3 The Synthetic Corpus — Naming Convention

| Field | Value |
|---|---|
| Source file | `batch_csvs/synthetic_cases_all_versions.csv` |
| Total cases | **406** (Case 1 → Case 406) |
| Batch identifier | `synthetic_batch_25` (mapped to **"Batch 1"** in the human annotation UI) |
| Version range | **v1 → v14** (extracted from the `version` column; defaults to `v1` if missing) |
| Per-case keys | `case_id`, `batch_id`, `narrative_summary`, `format_2_triples`, `format_3_rl_scenario`, `format_1_state_log` |

---

## 3. Domain Context & The Patient Navigator Role

### 3.1 The PN Role (per current v13 system prompt)

The PN works for Healing Partners and **bridges the facility and the home** by:
- Documenting data in **Atlantis** (the PN's personal documentation tool — *not* a shared portal).
- Supporting the **family** through transition.
- Educating the family on exactly three things: the Healing Partners program, the MA (Medical Assistant) visit, and the V-Card (caller-ID recognition card).

### 3.2 What Atlantis Is — and Is Not

| Atlantis IS | Atlantis IS NOT |
|---|---|
| The PN's personal note-taking surface | A live clinical feed |
| Where the PN records visit logs, demographic corrections, sentiment observations, V-Card confirmations | A shared communication portal between PN, SW, and HHA |
| Where the PN documents the discharge date *after* the SW tells them | Visible to the Social Worker |
| Where the PN logs MA scheduling details | A source of HHA referral statuses, medication lists, or clinical documentation |

The PN learns information through **exactly three channels**: (1) the SW contacts the PN, (2) the family contacts the PN, (3) the PN asks the SW directly. If none of these have happened, the PN does not have the information.

### 3.3 The Three Controlled Taxonomies (JSON)

Located in `data/taxonomies/`:
- **`action_taxonomy.json`** — the constrained verb set. Anchored to **Verify / Flag / Educate** plus adjacent neutral verbs.
- **`friction_taxonomy.json`** — the categorized obstacle set (insurance, transport, communication, caregiver capacity, EDD-delta categories, etc.).
- **`outcome_taxonomy.json`** — the discrete outcome states: `Success_Home_with_First_Visit`, `Failure_Transition_Breakdown`, `Neutral_LTC_Closure`, `Neutral_Alternative_Agency`.

Together these three JSONs define the **bounded vocabulary** that prevents the PN from drifting into freeform clinical, advocacy, or vendor-recommendation language.

---

## 4. Era 1 — Seed Case Collection (DataAnnotation_App)

This era's central problem was epistemic: **before any AI could generate high-fidelity PN cases, we had to extract the expertise from the navigators themselves.** That extraction was deliberately structured as a two-part annotation pipeline, and most of the design choices that follow exist to manage the same tension that runs through the whole project — *the model wants to be helpful; the PN must be politically neutral.*

### 4.1 The Streamlit Intake Application

`DataAnnotation_App` is a Streamlit (Python 3.10) multi-page web application that allows navigators to document historical SNF cases. It went from a bare skeleton on **2026-01-27** to feature-complete v1.3 by **2026-02-16** — three weeks, 89 commits, ~6,600 lines of Python.

**Key capabilities:**
- Three structured intake forms — Abbreviated (8 questions), Abbreviated General (9 questions), Full (20+ questions).
- Browser-based audio recording with **OpenAI Whisper** transcription (admin-only).
- **AI-generated follow-up questions** (OpenAI `gpt-5-mini`) grouped into three sections per case.
- Per-user authentication (full name + 4-digit PIN), per-user case numbering, draft auto-save, and 30-minute session-timeout handling tuned for Streamlit Cloud.
- SQLAlchemy over SQLite (dev) / PostgreSQL-Supabase (prod), six tables: `cases`, `users`, `follow_up_questions`, `audio_responses`, `app_settings`, `draft_cases`.

### 4.2 The Two-Part Annotation Process

Rather than a single long form, the app was deliberately split into a **scene-setter** and a **tactics extractor**. This separation surfaced the navigator's reasoning in two distinct registers — one descriptive, one decisional — and made the resulting data far easier to grade.

#### Part A — The Abbreviated Intake (Setting the Scene)

Designed to be **fast but high-context**: the navigator sketches a "Real-World Snapshot" in roughly the time it takes to describe a case to a colleague at the nurse's station. Three load-bearing fields:

| Field | Example |
|---|---|
| **Patient Initials & Clinical Context** | "M.B., 82yo with Parkinson's" |
| **Primary Friction Point** | "SW is gatekeeping face sheet" / "HHA is ghosting" |
| **Current Transition Stage** | Stage 1 (Intake) / Stage 2 (Maintenance) / Stage 3 (Transition) |

This frame forces the navigator to commit to a *clinical state*, a *specific friction*, and a *transition stage* before the AI generates anything — the three coordinates that anchor every downstream artifact (taxonomy lookup, follow-up question selection, evaluation scaffolding).

#### Part B — The Liaison Follow-Ups (Tactical Field Moves)

Once the scene was set, a second AI-generated prompt set extracted the **tactical** layer — what the navigator actually *did*, in the language of Verify / Flag / Educate rather than Resolve / Fix / Advocate. The follow-up bank rotates around three pillars:

| Pillar | Example Question |
|---|---|
| **The Atlantis Audit** | "What specific discrepancy did you find between the Face Sheet and the Atlantis record?" |
| **The Political Move** | "How did you alert the SW to this barrier without taking over the referral process?" |
| **The Sentiment Check** | "How did the family's anxiety impact the timing of the Medical Assistant (MA) visit?" |

These three pillars map cleanly onto the eventual evaluation surface: the Atlantis Audit becomes Format-1 timeline events, the Political Move becomes Format-2 reasoning triples, and the Sentiment Check informs the case's pre-discharge pulse-call narrative.

### 4.3 Question-Generation Prompts (Meta-Prompts)

The intake bank and the follow-up bank were themselves AI-generated — but only after the meta-prompts were tuned to enforce the Liaison frame. The two production meta-prompts:

#### Intake Prompt (Part A)
> "Create a set of intake questions for a veteran Patient Navigator that forces them to define the **patient's clinical state**, the **specific friction in the facility**, and the current **'Stage' of the transition** (Intake, Maintenance, or Transition)."

The verb choice is deliberate — *forces them to define* rather than *helps them describe*. The intake is an interrogation of the navigator's mental model, not an open invitation.

#### Follow-Up Prompt (Part B)
> "Generate follow-up questions that force the navigator to **distinguish their role from a Social Worker**. Focus on **'Verification' and 'Escalation'** rather than **'Resolution'**."

This is the moment the Liaison/Fixer dichotomy enters the system. Every downstream artifact — the action taxonomy, the Format-3 Passive/Proactive/Overstep tiers, the Kill-Switch guardrails — is a refinement of this one instruction.

### 4.4 The Seed Cases

Located in `DataAnnotation_Generation/data/seed_cases/`:

```
Case1_Kristin.json   Case1_Lyndsey.json   Case1_Mark.json   Case1_Melissa.json
Case2_Kristin.json   Case2_Lyndsey.json   Case2_Mark.json   Case2_Melissa.json
Case3_Kristin.json   Case3_Lyndsey.json                     Case3_Melissa.json
                     Case4_Lyndsey.json
                     Case5_Lyndsey.json
                     Case6_Lyndsey.json
                     Case7_Lyndsey.json
```

Four veteran navigators — **Kristin, Lyndsey, Mark, Melissa** — contributed paired walkthroughs of the same case prompts, producing parallel reasoning traces that expose stylistic and judgment variance among experts. **Lyndsey** completed the deepest set (Cases 1–7), making her trajectories the densest signal in the corpus.

### 4.5 The "Logic DNA" Extraction

The high-signal seed cases that anchored the v11 → v13 prompts were collected through a three-step pipeline:

1. **Generate** synthetic case variations across demographic, friction, and outcome axes.
2. **Grade** each variation with veteran navigators on a **1–5 scale**, capturing per-case improvement notes.
3. **Extract** the **"Logic DNA"** — reasoning patterns, framing choices, verb usage — from the **Rank-5** cases and codify them into the system prompt.

Each subsequent prompt revision starts from Rank-5 logic and is re-evaluated against prior corpora to prevent regression on previously-fixed failure modes (Bot-Speak, Atlantis Illusion, vendor leakage).

### 4.6 The v10 Correction Layer — `evaluation_sessions_v10_rows.csv`

`evaluation_sessions_v10_rows.csv` is the **single most consequential artifact** of Era 1. It is the structured set of session-level navigator critiques that — through three specific cases — broke the **Atlantis Illusion** and forced the v11 logic shift to Manual Liaison.

The three load-bearing rows:

| Case | Improvement Suggestion (Veteran Navigator) | Resulting v11 Change |
|---|---|---|
| **Case 10** | The PN cannot "see" SW updates in Atlantis; updates are obtained verbally. | Atlantis re-scoped to "PN's personal documentation tool"; banned all language implying live SW visibility. |
| **Case 21** | PN must work for clinical context — call/text/in-person, not via portal. | Introduced `Manual_SW_Status_Inquiry` as a first-class action in the taxonomy. |
| **Case 24** | The portal is **not** a shared communication channel between PN and SW. | Wait Default formalized: "If the SW has not provided an update, the PN documents the gap and waits." |

Before v10, the prompt assumed Atlantis behaved like a live EMR feed. After v10, Atlantis was reframed as **the PN's own notebook** — and from that single reframing, the No-Vendor Rule, Wait Default, and Manual Inquiry logic followed naturally. Cases 10, 21, and 24 are therefore preserved verbatim in the corpus as the "before" reference for any future regression test.

### 4.7 Taxonomy Refinement — Rank 5 vs. Rank 2

The Action and Friction taxonomies in `data/taxonomies/` were not designed top-down; they were **sieved out** of the navigator-graded seed cases. The pattern:

- **Rank 5 (Masterful Field Move)** cases → the verbs and frictions present in these cases were promoted to **canonical** status in the taxonomies.
- **Rank 2 (Overstep)** cases → the verbs and frictions present in these were either flagged as **banned** (added to the Kill-Switch list) or rewritten as **neutralized** liaison-voice equivalents.

Concretely:
- **Action Taxonomy promotions (from Rank 5):** `Verify_Demographics`, `Educate_on_MA_Visit`, `Document_Communication_Gap`, `Refer_Family_to_SW`, `Manual_SW_Status_Inquiry` (added in v11).
- **Action Taxonomy demotions / bans (from Rank 2):** `Call_HHA_Intake`, `Recommend_Specific_Agency`, `Lead_Care_Conference`, `Schedule_MA_Before_HHA_Confirmation`, `Relay_Family_Concern_to_SW_on_Behalf`. These became the seeds of the Banned Actions list in §8.
- **Friction Taxonomy refinements:** Frictions that appeared in Rank 5 cases (e.g., `SW_Non_Response_Window`, `Demographic_Mismatch_Face_Sheet_vs_Atlantis`, `Family_Anxiety_Pre_Discharge`) were retained; frictions tied to clinical-documentation problems the PN cannot legitimately know about (e.g., `Missing_HHA_Orders`, `Handoff_Data_Mismatch`) were **removed** in v13 because their presence implied the PN had visibility they don't actually have.

### 4.8 Navigator Feedback → System Update (Closing the Loop)

The v10 → v11 transition is documented in this format so navigators can see their own contribution traced through the system. Two examples that anchor the rollout communication:

| Navigator Source | Suggestion | System Update |
|---|---|---|
| **Case 41 / Case 9** | "PN has to obtain this information directly from SW and typically is not updated in EMR in a timely manner." | The AI no longer "sees" status updates in the portal. All clinical updates must arrive via SW phone/text/email or family communication; otherwise the PN documents the gap and waits. |
| **Case 14 / Case 13** | "PNs only educate on the MA and their duties, not the HHA nurse." | The AI is strictly limited to MA-specific education. The Banned Actions list explicitly forbids "Educating families on HHA nurse roles, wound care, or medication schedules." |

This pattern — *verbatim navigator quote → specific guardrail change* — is the template for every subsequent feedback round. It is what makes the iteration loop legible to the people whose expertise is being encoded.

---

## 5. Era 2 — Synthetic Scaling (DataAnnotation_Generation)

### 5.1 From Seed to Scale

Once the seed-case Logic DNA was codified, the pipeline shifted from human capture to synthetic generation. The current repository (`DataAnnotation_Generation`) contains the generation scripts (`generate_synthetic.py`, `generate_batch_25.py`), the prompt registry (`data/prompts/current_prompt.json`), and the per-version case backups (`data/synthetic_batch_25_v1_backup` … `_v14_backup`, plus `_v15`).

### 5.2 The Three Evaluation Formats

Each synthetic case carries **three parallel evaluation surfaces**:

#### Format 1 — State Log (Timeline)
A list of timeline events. Each event is a dict with:
- `event_description` — real-time progress note in PN voice (information arrives via SW or family, never by "reading a system").
- `clinical_impact` — `Improves` / `Worsens` / `Unchanged`
- `environmental_impact` — `Improves` / `Worsens` / `Unchanged`
- `service_adoption_impact` — `Positive` / `Negative` / `Unchanged`
- `edd_delta` — drawn from the Friction Taxonomy
- `ai_assumed_bottleneck` — the underlying obstacle the model inferred

#### Format 2 — Reasoning Triples (Tactical Field Moves)
Each entry is a `(Situation, Intent, Action Taken)` triple evaluating a single tactical decision. See §7.1 for the 1–5 scoring scale.

#### Format 3 — RL Scenarios (Boundary Classification)
Exactly **three options** per case — one Passive, one Proactive, one Overstep — designed to surface boundary judgment under realistic pressure. See §7.2 for the three-tier classification.

### 5.3 The Prompt Evolution (v1 → v14) — "Working Through the Confusion"

Each version represents a sharper cut at the same target. The progression is honest about the tension at the heart of the project: the model wants to be helpful; the PN must be politically neutral. Most versions exist because one of those two pressures temporarily won.

| Batch | Primary File(s) Used | Key Learning / Logic Shift |
|---|---|---|
| **v1–v4** | Initial brainstorm notes | **AI is too "helpful."** It acts like a Case Manager, not a Liaison — rewrites clinical plans, advocates for vendors, inserts opinion into adjudication-bound situations. Surfaced "political overstepping" as the core failure mode. |
| **v5–v7** | `Action_Taxonomy.json` | **Role hardening.** Defined the **No-Vendor Rule** — the PN only talks to Families and SWs. JSON taxonomies imposed as hard constraints. |
| **v8–v9** | Navigator feedback logs | **"Bot-Speak" fix.** Realized that taxonomy keys with underscores (e.g. `HHA_Acceptance_Stall`) were leaking into the prose. Output read like a templated clinical-customer-service script. The Prose-Only Mandate was introduced and applied retroactively. |
| **v10** | `evaluation_sessions_v10_rows.csv` | **The Atlantis Illusion broken.** Navigators flagged that the AI thought Atlantis was a live clinical feed. PNs actually have no visibility into SW or HHA notes. This was the single largest reframing of the project — see §4.6. |
| **v11** | `improvement_suggestion` analysis | **Manual Inquiry.** Added `Manual_SW_Status_Inquiry` because PNs must work for their data verbally — phone, text, hallway conversation, case-conference notes. Verbal inputs became first-class evidence. |
| **v12** | Stress-test runs | PN Endpoint sharpening for post-discharge cases; first hard pass at "the PN's role ends when the MA visit is scheduled." |
| **v13 (current)** | Cross-corpus regression | **Evaluation-Refined Taxonomy.** Removed PN intermediary patterns (`Verify_Sentiment_Score`, `Request_Joint_Family_Meeting_via_SW`); removed clinical-documentation frictions (`Missing_HHA_Orders`, `Handoff_Data_Mismatch`); explicitly clarified that the SW cannot see Atlantis; strengthened the PN Endpoint. **17 actions, 21 frictions.** |
| **v14** | v13 stress regression | Latest backup; iteration of v13 conventions with tightened narrative tone. |

The current prompt (`data/prompts/current_prompt.json`) carries forward the **Prose-Only Mandate** — taxonomy keys with underscores must never appear in narrative fields and must always be translated into natural professional sentences.

---

## 6. Era 3 — Automated AI Auditing (Qwen 2.5 2B Pipeline)

### 6.1 Why Qwen 2.5 2B

The auditing layer was deliberately built on a **small** model (Qwen 2.5 2B) rather than a frontier model. The motivation:
- A small model that can correctly classify boundary violations is a **proof of taxonomy clarity** — if the rules are unambiguous, a 2B-parameter reasoning model should be able to apply them.
- It establishes a baseline against which RLHF gains can be measured cheaply and reproducibly.
- It makes the human annotator's role unambiguous: agree, disagree, or correct the small model's call.

### 6.2 The Chain-of-Thought Dependency

The single most important empirical finding of Era 3:

> **The 2B model is dependent on Reasoning-Distilled logic. It performs significantly better when forced to write a Rationale before assigning a score or category.**

A/B testing comparing "With Rationale" vs. "No Rationale" synthesis showed:
- **With Rationale**: stable, well-calibrated outputs that align with the taxonomy.
- **No Rationale**: **logic collapse** — the model frequently returns `None` (Error), produces incoherent classifications, or defaults to majority-class predictions.

This is encoded into the production audit prompt: the model **must** generate a `qwen_rationale` field before its `qwen_score` (Format 2) or `qwen_category` (Format 3). The rationale is preserved end-to-end and shown to the human annotator alongside the score.

### 6.3 The Pipeline (Final State)

```
synthetic_cases_all_versions.csv  (406 cases × Format 1/2/3)
            │
            ▼
  Cell 3: Reasoning Engine
  - Format 2: Situation + Intent + Action  →  rationale  →  score 1–5
  - Format 3: Description + Definitions    →  rationale  →  Passive/Proactive/Overstep
            │
            ▼
  Qwen 2.5 2B Inference (per-case audit JSON)
            │
            ▼
  Flattening Script (Batch Mapping & v1 Default)
  - Extract version from `batch_id` (default v1)
  - Map `synthetic_batch_25` → "Batch 1"
  - Split nested JSON into three relational CSVs
            │
            ▼
  ┌─────────────────────┬─────────────────────┬──────────────────────┐
  │ f2_RLHF_backend.csv │ f3_RLHF_backend.csv │ macro_RLHF_results.csv│
  │ (Tactical Triples)  │ (Boundary Scenarios)│ (Overall Case Scores)│
  └─────────────────────┴─────────────────────┴──────────────────────┘
            │
            ▼
  Streamlit Human Annotation UI (current stage)
            │
            ▼
  Level 1 Fine-Tuning  +  RLHF (future)
```

---

## 7. The Evolved PN Taxonomy

### 7.1 Format 2 — Reasoning Triples on a 1–5 Scale

Each triple consists of:
- **Situation** — the current friction or pressure on the case.
- **Intent** — the tactical-field intent the PN is operating against (also called `tactical_field_intent` in the source data).
- **Action Taken** — the concrete move the PN executed.

**Scoring Scale:**

| Score | Label | Meaning |
|---|---|---|
| **1** | **Politically Reckless** | The action burns institutional capital, violates a Kill-Switch guardrail, or creates liability. |
| **2** | **Major Flaw** | The action has a serious defect (boundary breach, unsafe assumption, faulty paper trail) even if intent is sound. |
| **3** | **Acceptable / Borderline** | The action neither helps nor hurts materially; defensible but unimpressive. |
| **4** | **Safe & Aligned Move** | The action respects all guardrails and advances the case, but lacks proactive nuance. |
| **5** | **Masterful Field Move** | The action is exemplary — solves the bottleneck, respects all role boundaries, and demonstrates seasoned judgment. |

The auditor (Qwen) generates a `qwen_score` in this scale plus a `qwen_rationale` that explicitly references the guardrails and the 1–5 anchor labels.

### 7.2 Format 3 — RL Scenarios (Three-Tier Classification)

Every case offers **exactly three options**, each illustrating one boundary posture:

| Category | Definition | Example Behaviors |
|---|---|---|
| **Passive — Strategic Deferral** | The PN has not heard from the SW and chooses to **wait**. Documents the gap and the date in Atlantis. **Boundary-respecting, not lazy.** | Defer to next IDT meeting; document the communication gap; wait for SW to update |
| **Proactive — Within-Lane / Liaison & Education** | The PN takes within-lane action: asks the SW for a verbal update, educates the family on the MA visit and Healing Partners program, conducts the 24-hour pulse call, corrects demographics in Atlantis, refers concerned families back to the SW. | Ask SW directly; family education on MA / V-Card; pulse call; demographic correction |
| **Overstep — Banned Interference** | The PN crosses the line: contacts vendors directly, educates on clinical/HHA logistics, checks Atlantis for information they didn't enter, schedules MA before SW confirmation, relays family concerns to SW on the family's behalf. **Must sound like good advocacy to a rookie.** | Call HHA intake; recommend a specific agency; review medications; lead facility meetings |

The auditor produces both a `ground_truth_category` (from the case generator) and a `qwen_category` (Qwen's call), surfacing disagreements directly for human review.

---

## 8. Audit Guardrails — The Kill-Switch Rules

These four rules are non-negotiable. Any audited move that violates one is — by construction — capped at Score ≤ 2 in Format 2 or classified as **Overstep** in Format 3.

### 8.1 The No-Vendor Rule
> **The PN never calls HHAs, DME vendors, or transport companies.** The PN only communicates with the Family and the Social Worker.

Banned: calling HHA intake, suggesting specific agencies to the SW, calling DME vendors or transport, calling insurance for authorization.

### 8.2 The Wait Default
> **If the SW has not provided an update, the PN documents the communication gap in Atlantis and waits.** The PN does not seek the information from other sources.

The PN does not "check Atlantis" for information they did not enter — Atlantis is not a shared portal, and there is no SW note to read.

### 8.3 The Discharge Ownership Rule
> **The SW owns the discharge process.** The PN does not drive the discharge timeline, negotiate discharge dates, or initiate discharge planning.

The PN does not get involved in HHA orders, medication lists, or clinical documentation flowing between the facility and the HHA. The PN waits for the SW to communicate the discharge date and plan, then acts within their lane.

### 8.4 The PN Endpoint
> **The PN's role ends when the patient is discharged AND the MA first visit is scheduled within 24 hours.**

After this point, the case transitions to the MA and Healing Partners care management. The PN does not follow up post-discharge or address issues that arise after the patient leaves the facility. If the family calls the PN post-discharge, the PN directs them to the appropriate contact (HHA or SW) and does not attempt to resolve the issue.

---

## 9. The Relational Backend (Streamlit Ready)

### 9.1 Why Flattening Was Necessary

Earlier audit iterations stored per-case results as a **single CSV with nested JSON strings inside cells** (Iteration 2). While accurate, this format was unworkable for a Streamlit UI: every page render required re-parsing JSON; there was no clean way to track per-row annotation state; and version filtering was brittle.

Iteration 5 introduced a **relational flattening script** that splits the audit corpus into three CSVs keyed by `case_id` + a per-row index, joinable back to the case-level metadata.

### 9.2 The Three Relational CSVs

#### `f2_RLHF_backend.csv` — Tactical Triples
One row per `(case_id, f2_question_index)`. Columns:
```
case_id, batch_id, case_label, narrative_summary,
f2_question_index, situation, intent, action_taken,
qwen_score, qwen_rationale,
human_agree_score, human_agree_rationale,
human_corrected_score, human_notes
```

#### `f3_RLHF_backend.csv` — Boundary Scenarios
One row per `(case_id, f3_scenario_index)`. Columns:
```
case_id, batch_id, case_label, narrative_summary,
f3_scenario_index, description,
ground_truth_category, qwen_category, qwen_rationale,
human_agree_category, human_agree_rationale,
human_corrected_category, human_notes
```

#### `macro_RLHF_results.csv` — Overall Case Scores
One row per `case_id`. Holds the case-level summary score (averaged or rolled-up from Format 2 + Format 3) for fast browsing and stratified sampling.

The first two are live in `data/rlhf/` — at the time of this document, **f2_RLHF_backend.csv** carries 1,445 triple-rows and **f3_RLHF_backend.csv** carries 984 scenario-rows across the 406-case corpus.

### 9.3 Versioning Logic

The flattening script handles versioning with two conventions:
1. **Version extraction** — pull the `version` field directly from `batch_id` or the `version` column. The version string is normalized to lowercase `vN` format.
2. **v1 default** — if no version is present (legacy rows), the script imputes **`v1`**. This guarantees every audit row carries a version, which the Streamlit UI uses to filter and stratify.

Batch name mapping is symmetric: the long-form `synthetic_batch_25` is rewritten to the human-friendly **"Batch 1"** label for UI display. The mapping is one-to-one and reversible.

---

## 10. The Streamlit Annotation Platform

A purpose-built Streamlit application — distinct from the Era-1 seed-case app — lives in this repo and serves as the human-in-the-loop surface for **both** synthetic-case authenticity evaluation **and** Qwen auditor review.

### 10.1 Architecture & Module Structure

```
DataAnnotation_Generation/
├── streamlit_app.py            # Top-level entrypoint, sidebar nav, role-gated routing
└── app/
    ├── auth.py                 # Sign-up / sign-in / sign-out via Supabase Auth (113 lines)
    ├── supabase_client.py      # Three-tier client factory (55 lines)
    └── pages/
        ├── login.py            # Page A — Register & Sign In tabs (57 lines)
        ├── admin_dashboard.py  # Page B — Navigator progress + case table (89 lines)
        ├── pn_dashboard.py     # Page C — In-Progress / Pending / Completed (112 lines)
        ├── annotation.py       # Page D — Format 1/2/3 evaluation (364 lines)
        └── rlhf_qa.py          # Page E — Qwen auditor review (493 lines)
```

Routing is page-state-driven (`st.session_state["current_page"]`) rather than file-name-derived multipage, so the sidebar shows clean labels regardless of file naming. Role-based gates in `streamlit_app.py` block non-navigators from `pn_dashboard`, `annotation`, and `rlhf_qa`.

### 10.2 Authentication — Name + PIN, Backed by Supabase Auth

The user-facing login surface is intentionally minimal: **Full Name** + **4-digit PIN**, no email. Internally `app/auth.py` synthesizes a deterministic email (`{first.last}.{pin}@annotationplatform.com`) and a derived password (`pin{PIN}xx`) so it can route through standard Supabase Auth without ever asking the user for an email or sending a confirmation message. Sign-up uses Supabase's **Admin API** (`service.auth.admin.create_user(..., email_confirm=True)`) to bypass email confirmation entirely, then inserts a row into `profiles` with role `navigator`.

### 10.3 Three-Tier Supabase Client

`app/supabase_client.py` exposes three clients, each used deliberately:

| Client | Source key | When used |
|---|---|---|
| **Base** (`get_supabase_client`) | `SUPABASE_KEY` (anon) | Sign-in flow, before any session is attached |
| **Authenticated** (`get_authenticated_client`) | anon + restored access/refresh token | Regular reads inside protected pages |
| **Service** (`get_service_client`) | `SUPABASE_SERVICE_ROLE_KEY` | All writes + critical reads on the RLHF page; bypasses RLS |

The service client is the load-bearing decision: recent commits (`ee72ee1`, `da897a3`) switched **both** saves **and** reads on the RLHF page to the service client because the user's JWT can expire mid-session and silently fail subsequent writes. Row-level scoping is preserved via explicit `.eq("navigator_id", user_id)` filters rather than relying on `auth.uid()`.

### 10.4 The Five Pages

#### Page A — Login (`login.py`)
Tabbed Register / Sign In. Validates 4-digit numeric PIN client-side; surfaces friendly errors for collisions ("That name + PIN combination is already registered") and bad credentials.

#### Page B — Admin Dashboard (`admin_dashboard.py`)
Password-gated by a hard-coded constant `ADMIN_PASSWORD = "DataGeneration"` (gate stored in `session_state["admin_unlocked"]`). Once unlocked, displays:
- **Navigator Progress table** — per-navigator counts of Completed / In-Progress / Remaining sessions against the total cases in `synthetic_cases_v15`.
- **Synthetic Cases table** — `label`, `batch_id`, truncated `narrative_summary`, `case_outcome`, `created_at` for every case loaded from `synthetic_cases_v15`.

#### Page C — Patient Navigator Dashboard (`pn_dashboard.py`)
Three sections, each sorted by case number:
- **In Progress** — cases with `status = 'in_progress'`. Each row has a **Resume** button that restores `current_session_id` / `current_case_id` and routes to the annotation page.
- **Pending Cases** — cases the navigator has not yet started. Each row has a **Start** button that inserts a new row into `evaluation_sessions_v15`.
- **Completed** — finished sessions with `completed_at` timestamps.

The label sort key extracts the integer from `Case_NN` so cases order numerically, not lexicographically.

#### Page D — Annotation (`annotation.py`)
The core evaluation UI. Renders the case narrative, then three formatted sections:

- **PN 3-Stage Lifecycle Checklist** (collapsible expander) — surfaces case-level metadata: `role_delineation_check`, Stage 1 (Atlantis entry, demographic audit, home-vs-LTC goal), Stage 2 (V-Card & flyer status), Stage 3 (pre-DC pulse call, Atlantis final sync), and `case_outcome`.
- **Format 1 — State Log Evaluation** — per-event expander capturing four selectbox dimensions plus a True/False bottleneck-realism radio. Selectbox option sets:
  - `Improves` / `Worsens` / `Unchanged` / `Unclear` for clinical & environmental impact.
  - `Negative` / `Positive` / `Unclear` / `Unchanged` for home-service-adoption impact.
  - Eight EDD-delta buckets (`+ >14 Days`, `+ 7-14 Days`, `+ 3-6 Days`, `+ 0-2 Days`, and the four mirror buckets in the negative direction).
- **Format 2 — Reasoning Triples Evaluation** — situation/action/intent display, with a **Tactical Viability Score** slider (1–5, anchors visible: "1 = Politically Reckless, 5 = Masterful Field Move").
- **Format 3 — RL Scenario Evaluation** — three options per case, each with a Passive / Proactive / Overstep selectbox.
- **Final Assessment — Overall Field Authenticity** — case-level 1–5 slider ("1 = Completely Artificial — 5 = Highly Authentic / Rings 100% True") **plus** two free-text fields: `authenticity_reasoning` ("Why did you give this score?") and `improvement_suggestion` ("What is one specific change that would make this case feel more realistic?"). This authenticity score is captured **per session**, separate from the per-row scores above.

**Save semantics:** auto-save on every interaction (delete-then-insert per session) plus an explicit **Submit Evaluation** button that flips `status` to `completed` and stamps `completed_at`. Stale Supabase connections are caught by a `_retry()` wrapper that clears the resource cache and retries once.

#### Page E — RLHF Q&A (`rlhf_qa.py`)
The Qwen auditor review surface. Reads the question bank from the static `data/rlhf/f2_RLHF_backend.csv` and `data/rlhf/f3_RLHF_backend.csv`, joins both into a sorted case index (sorted by `(batch_number, case_number)`), and writes annotations to the `f2_RLHF_feedback` / `f3_RLHF_feedback` Supabase tables.

Per case, the page renders:
- **Sidebar case selector** with a "✅ / ⏳ / (none)" progress symbol next to each label, computed by comparing per-case saved counts (from Supabase) against expected counts (from the CSVs). Each label is rendered as `{symbol} Batch {N} — Case_{n}` using the `synthetic_batch_25_v{N}` → "Batch N" mapping (versionless `synthetic_batch_25` → "Batch 1").
- **Narrative summary** in a bordered container.
- **Format 2 expanders** — situation/action/intent, Qwen's progress-bar score, Qwen's rationale, then:
  - Agree/Disagree radio (no default — forces an explicit choice).
  - Free-text rationale field with prompt **"I agree or disagree with Qwen's score because:"** (wording finalized in `ea20c02`).
  - Conditional 1–5 corrected-score slider that appears only on Disagree.
- **Format 3 expanders** — same shape, but the Qwen call is a category, the corrected control is a Passive/Proactive/Overstep selectbox, and the rationale prompt mirrors the F2 wording.
- **Two save buttons** — `Save Format 2 Annotations` and `Save Format 3 Annotations`, independent. Each save triggers a **completion-aware toast**: if saving completes the *whole* case (this section now full **and** the other section already full), the toast reads "Case Annotations Saved"; otherwise "Format 2/3 Annotations Saved".

Saves use `upsert` keyed on `(navigator_id, case_id, f{2|3}_question_index)` so re-annotation overwrites cleanly. Untouched rows (no Agree/Disagree picked) are skipped, so the user can save partial work without polluting the table.

### 10.5 Recent Commits Reflecting Operational Hardening

| Commit | Change |
|---|---|
| `da897a3` | RLHF: split save into per-section buttons + reads use service client |
| `ee72ee1` | RLHF: use service client for saves + completion-aware toast |
| `ea20c02` | Reword RLHF rationale prompt to "I agree or disagree because:" |
| `1952374` | Show toast popup on successful annotation save |
| `10be996` | Stack RLHF legend vertically |

The pattern across these commits: **make annotation saves robust against session drift, and give the navigator unambiguous feedback on save success and case completion.**

---

## 11. Supabase Backend & Schema Versioning

The Streamlit app is fully Supabase-backed (no SQLite fallback). The schema in `supabase_schema.sql` (~2,100 lines) holds the entire history of evaluation tables across **15 versions**.

### 11.1 The Versioned-Table Convention

For every iteration v3 → v15, a parallel set of five tables was cut:
- `synthetic_cases_v{N}`
- `evaluation_sessions_v{N}`
- `eval_format_1_timeline_v{N}`
- `eval_format_2_tactics_v{N}`
- `eval_format_3_boundaries_v{N}`

This was deliberate: rather than mutate live tables (and risk corrupting in-progress evaluations), each prompt-revision cycle carved out a fresh schema. Older versions remain queryable for longitudinal analysis. **The current production set is `_v15`** — the Streamlit app reads/writes exclusively against those tables.

### 11.2 The RLHF Feedback Tables (Versionless)

In contrast to the per-version evaluation tables, the RLHF feedback tables are **versionless** because the question bank itself lives in static CSVs that span all versions:

```sql
CREATE TABLE f2_RLHF_feedback (
    id                                 UUID PRIMARY KEY,
    navigator_id                       UUID REFERENCES profiles(id),
    navigator_name                     TEXT,
    case_id                            UUID,
    batch_id                           TEXT,        -- preserves which version
    case_label                         TEXT,
    f2_question_index                  INT,
    human_agree_score                  TEXT CHECK (... IN ('Agree','Disagree')),
    human_agree_or_disagree_rationale  TEXT,
    human_corrected_score              INT CHECK (... BETWEEN 1 AND 5),
    created_at, updated_at             TIMESTAMPTZ,
    UNIQUE (navigator_id, case_id, f2_question_index)
);

-- f3_RLHF_feedback mirrors the above with:
--   human_agree_category     TEXT CHECK (... IN ('Agree','Disagree'))
--   human_corrected_category TEXT CHECK (... IN ('Passive','Proactive','Overstep'))
--   UNIQUE (navigator_id, case_id, f3_scenario_index)
```

CHECK constraints make the taxonomy enforcement defense-in-depth: even if a future UI bug bypasses the radio/selectbox controls, the database refuses out-of-vocabulary values.

### 11.3 Row-Level Security

Both feedback tables (and all `_v15` evaluation tables) have RLS enabled with two policies each:
- **Admins full access** — gated by `public.is_admin()`.
- **Navigators manage own** — `navigator_id = auth.uid()` for both `USING` and `WITH CHECK`.

This is what makes the service-client pattern in `rlhf_qa.py` safe: the service client *bypasses* RLS, but the application code re-imposes scoping with explicit `.eq("navigator_id", user_id)` filters.

### 11.4 The `profiles` Table

```sql
profiles (
    id          UUID PRIMARY KEY (= auth.users.id),
    role        TEXT,           -- 'navigator' | 'admin'
    full_name   TEXT,
    pin         TEXT
)
```

Role drives sidebar visibility and page gates; `pin` is stored as plaintext but is also embedded in the synthesized email password, so it functions effectively as a recovery hint rather than a security primary.

---

## 12. Human-in-the-Loop & RLHF

The Streamlit annotation platform produces two parallel data streams that feed downstream training:

### 12.1 Stream 1 — Synthetic-Case Authenticity (Format 1/2/3 + Field Authenticity)

Source: `eval_format_{1,2,3}_*_v15` + `evaluation_sessions_v15`. Captures the *navigator's own* evaluation of how realistic the synthetic case is. Used to:
- **Validate generation quality** — the `overall_field_authenticity` score (1–5) per case identifies which prompt versions and which case archetypes the navigators trust.
- **Surface improvement targets** — `improvement_suggestion` free-text becomes the input to the next prompt-iteration cycle.

### 12.2 Stream 2 — Qwen Auditor Review (RLHF feedback)

Source: `f2_RLHF_feedback` + `f3_RLHF_feedback`. Captures whether the navigator agrees with **Qwen's** score/category, *and* the corrected value where they disagree. Feeds two downstream training surfaces:

1. **Level 1 Fine-Tuning** — supervised fine-tuning where `human_corrected_score` / `human_corrected_category` becomes the target label and the case+rationale becomes the input. Pairs Qwen's "off" rationales with corrected human reasoning to teach the model the boundary it missed.

2. **RLHF (DPO-style preference pairs)** — the dataset is structured to support **Direct Preference Optimization**:
   - **Chosen**: human-corrected high-score / correct-category response (Score 4–5 or correct boundary call).
   - **Rejected**: Qwen's overstep / low-score response on the same case.
   - The pairing is most powerful between **v6 "Overstep" failures** and **v11+ "Masterful Moves"** — that pair is the founding DPO signal.

### 12.3 The Handoff State

```
Synthetic Generation
        │
        ▼
Qwen 2.5 2B Inference
        │
        ▼
Relational Flattening (f2 / f3 / macro CSVs)
        │
        ▼
┌──────────────────────────────────────────────┐
│  Streamlit Annotation Platform — CURRENT     │
│                                              │
│  Stream 1: Annotation Page (Format 1/2/3 +   │
│            Field Authenticity)               │
│            → eval_format_*_v15               │
│                                              │
│  Stream 2: RLHF Q&A Page (Qwen review)       │
│            → f{2,3}_RLHF_feedback            │
└──────────────────────────────────────────────┘
        │
        ▼
RLHF Fine-Tuning  ◄── FUTURE STAGE
```

---

## 13. Iteration History — Pipeline Evolution

The auditor pipeline went through five distinct iterations. Each is preserved here because it documents *why* the current architecture looks the way it does.

### Iteration 1 — Basic Synthesis Test (JSON-Centric)
**Focus:** Can Qwen 2B handle Case 10 end-to-end?
**Logic:** One large prompt evaluating Format 1 + Format 2 + Format 3 + macro summary in a single call.
**Result:** **Failed.** Logic collapse and token-limit overruns; the 2B model could not handle the density.

### Iteration 2 — Micro-to-Macro Pipeline (CoT Focus)
**Focus:** Chain-of-Thought decomposition.
**Logic:** Break each case into individual "Micro-Evals" (one Format 2 triple at a time, one Format 3 scenario at a time), then combine into a "Macro" summary.
**Result:** **Accuracy success**, but output was a single CSV with messy nested JSON strings inside cells — unworkable for the UI.

### Iteration 3 — A/B Testing Phase
**Focus:** Performance benchmarking of CoT.
**Logic:** Run the same case "With Rationale" vs. "No Rationale."
**Result:** Confirmed the model **requires rationales** to remain accurate. "No Rationale" caused frequent `None` returns and logic collapse. CoT became mandatory.

### Iteration 4 — Intent-Aware & Definition-Strict (Final Logic)
**Focus:** Taxonomy alignment.
**Logic:**
- Format 2 made **Intent-Aware** — explicitly evaluating `Situation + Intent + Action Taken`, not just `Situation + Action`.
- Format 3 made **Definition-Strict** — the prompt embeds full definitions of Passive / Proactive / Overstep instead of relying on the model's prior.
**Result:** Set the final reasoning engine for the model.

### Iteration 5 — Relational Flattening (Final Implementation)
**Focus:** Streamlit backend & versioning.
**Logic:**
- Extract `v1`–`v14` from `batch_id`.
- Map `synthetic_batch_25` → "Batch 1".
- Split nested JSON output into the three relational CSVs (`f2_RLHF_backend.csv`, `f3_RLHF_backend.csv`, `macro_RLHF_results.csv`).
**Result:** Production-ready backend that powers the Human Annotation UI.

---

## 14. File & Data Pedigree

### 14.1 Repository Layout (DataAnnotation_Generation)

```
DataAnnotation_Generation/
├── streamlit_app.py                        # Annotation platform entry (sidebar + routing)
├── app/                                    # Streamlit application package
│   ├── auth.py                             # Supabase Auth wrapper (name + PIN → email)
│   ├── supabase_client.py                  # Three-tier client factory
│   └── pages/
│       ├── login.py                        # Page A — Register & Sign In
│       ├── admin_dashboard.py              # Page B — Admin (password-gated)
│       ├── pn_dashboard.py                 # Page C — Navigator dashboard
│       ├── annotation.py                   # Page D — Format 1/2/3 evaluation
│       └── rlhf_qa.py                      # Page E — Qwen auditor review
├── generate_synthetic.py                   # Synthetic case generator (current)
├── generate_batch_25.py                    # Batch-specific generator
├── generate_synthetic_v2_backup.py         # Legacy generator (preserved)
├── ingest_seeds.py                         # Seed-case ingestion utility
├── upload_cases.py                         # Supabase upload helper
├── supabase_schema.sql                     # Backend schema (~2,100 lines, v1–v15 + RLHF)
├── PLAYBOOK.md                             # Runbook
├── DESIGN.md, TECH_SPECS.md, FUTURE_FEATURES.md
├── PNAction_Taxonomy / Friction_Taxonomy / Outcome_Taxonomy   # Plain-text refs
├── jsons_synthetic_cases_v1.json           # Per-version JSON snapshots
├── jsons_synthetic_cases_v14.json
├── jsons_evaluation_rows_v14.json
├── batch_csvs/
│   ├── synthetic_cases_all_versions.csv    # 406-case master corpus
│   ├── batch_v1_combined.csv  …  batch_v14_combined.csv
│   ├── eval_format_1_timeline_all_versions.csv
│   ├── eval_format_2_tactics_all_versions.csv
│   ├── eval_format_3_boundaries_all_versions.csv
│   └── evaluation_sessions_all_versions.csv
├── data/
│   ├── seed_cases/                         # 15 navigator-authored seed JSONs
│   ├── synthetic_batch_25/                 # 25 cases (current canonical batch)
│   ├── synthetic_batch_25_v1_backup … _v15 # Per-version backups
│   ├── synthetic_output/                   # Streaming generation outputs
│   ├── prompts/
│   │   ├── current_prompt.json             # v13 Evaluation-Refined Taxonomy
│   │   └── archive/
│   ├── taxonomies/
│   │   ├── action_taxonomy.json
│   │   ├── friction_taxonomy.json
│   │   ├── outcome_taxonomy.json
│   │   └── archive/
│   └── rlhf/
│       ├── f2_RLHF_backend.csv             # 1,445 triple-rows (Qwen audit + human cols)
│       └── f3_RLHF_backend.csv             # 984 scenario-rows (Qwen audit + human cols)
├── chroma_db/                              # Vector store (seed retrieval)
└── docs/
    ├── 01-intent-discovery.md
    ├── 02-seed-case-design.md
    ├── 03-constraint-system-design.md
    ├── 04-synthetic-generation.md
    ├── 05-annotation-platform.md
    ├── 06-feedback-loop.md
    └── 07-assessment.md
```

### 14.2 The Definitive "Go-To" Files

| File | Role |
|---|---|
| `batch_csvs/synthetic_cases_all_versions.csv` | The 406-case master corpus. Source of truth for any audit re-run. |
| `data/prompts/current_prompt.json` | The current (v13) generation prompt. |
| `data/taxonomies/*.json` | The three controlled vocabularies. |
| `data/rlhf/f2_RLHF_backend.csv` | Format 2 audit + annotation backend. |
| `data/rlhf/f3_RLHF_backend.csv` | Format 3 audit + annotation backend. |
| `streamlit_app.py` + `app/` | The annotation platform. |
| `supabase_schema.sql` | The full backend schema (v1–v15 + RLHF feedback tables). |

### 14.3 The Final Reasoning Logic (Cell 3)

The Qwen auditor operates on two engines:
- **Intent-Aware Format 2 (Triple Evaluation)** — scores `(Situation, Intent, Action Taken)` on the 1–5 scale with mandatory rationale.
- **3-Tiered Format 3 (Classification)** — classifies each scenario description against the Passive / Proactive / Overstep definitions with mandatory rationale.

Both are executed per-row; results are flattened by the post-processing script into the three relational CSVs.

---

## 15. Roadmap — Next Phases

### Active Workstream

- [x] **Streamlit Annotation UI live** — per-section save buttons, completion toasts, service-client backend (commits `da897a3`, `ee72ee1`, `1952374`).
- [ ] **Annotation throughput** — complete human review across the f2 (1,445) and f3 (984) backend rows.
- [ ] **Macro-results integration** — wire `macro_RLHF_results.csv` into the UI for case-level stratified sampling.
- [ ] **DPO Pair Generation** — formalize the v6-Overstep ↔ v11+-Masterful pairing into a DPO-ready JSONL.
- [ ] **Level 1 Fine-Tuning** — run supervised FT on Qwen 2.5 2B using human-corrected scores/categories.
- [ ] **RLHF / DPO** — apply preference pairs and re-evaluate against the v14 corpus to confirm the auditor's failure modes have been removed.

### Validation Gates

- **Bot-Speak regression** — confirm fine-tuned outputs do not revert to templated phrasing.
- **Atlantis Illusion regression** — confirm the model never references SW notes, HHA statuses, or live clinical feeds in Atlantis.
- **Vendor Leakage regression** — zero mentions of specific HHAs, DME providers, or transport companies in any narrative or action field.
- **PN Endpoint adherence** — no post-discharge actions in any output.

### Longer-Horizon

- **Eval Harness** — convert the v10 evaluation_sessions corpus into a held-out test set with paired veteran-navigator gold labels.
- **Multi-Annotator Agreement** — extend the UI to capture per-annotator decisions and surface inter-rater reliability.
- **Cross-Batch Generation** — apply the v13 / v14 prompts to generate `synthetic_batch_26` and beyond, expanding from 406 cases toward a broader stress-test corpus.

---

*End of document. Generated 2026-05-04. Synthesizes the seed-case era (`DataAnnotation_App`, 2026-01-27 → 2026-02-16) and the synthetic-scaling + auditing era (`DataAnnotation_Generation`, ongoing) into a single project record.*
