# PROJECT WORKFLOW
## One Health Partners Patient Navigator Data Annotation Project — End-to-End Process

**Audience**: Internal stakeholder evaluating whether to repeat this process for a different patient-navigator setting.
**Scope**: The human and AI workflow only. No code, schemas, or repo layout — those live in `MASTER_PROJECT_HISTORY.md`.
**Document Generated**: 2026-05-04

---

## At a Glance — The Process Flow

```
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 0  — Initial PN Interviews                   │
                    │  Goal: Understand the role from the navigator's     │
                    │  own words (daily work, discharge volume, insurance,│
                    │  the questions they wish someone had asked them)    │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 1  — Action Items Lists                      │
                    │  Each PN authored a phased Action+Intent list       │
                    │  (Admission / Maintenance / Discharge). These are   │
                    │  the raw inputs to the Action Taxonomy.             │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 2  — Seed Case Collection (Streamlit App)    │
                    │  Two-part annotation: Abbreviated Intake (clinical  │
                    │  state + friction + stage) → AI-generated Liaison   │
                    │  Follow-Ups (Atlantis Audit / Political Move /      │
                    │  Sentiment Check)                                   │
                    └────────────────────────┬────────────────────────────┘
                                             │
                              ┌──────────────┴──────────────┐
                              ▼                             ▼
            ┌─────────────────────────────┐   ┌──────────────────────────────┐
            │  STAGE 3 — Audit Questions  │   │  STAGE 4 — Follow-Up         │
            │  AI-generated audit Qs per  │   │  Question Ranking            │
            │  seed case → PN ranked 0/1  │   │  PN ranked 0/1 on three      │
            │  → fed taxonomy + synthetic │   │  criteria (Wordy /           │
            │  prompt design              │   │  Case-Specific / Relevance)  │
            │                             │   │  → revised meta-prompts      │
            └─────────────────────────────┘   └──────────────────────────────┘
                              │                             │
                              └──────────────┬──────────────┘
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 5  — Taxonomy Construction (with AI)         │
                    │  Action / Friction / Outcome JSON taxonomies.       │
                    │  Sieved from Rank-5 (Masterful) seed cases;         │
                    │  exclusions sieved from Rank-2 (Overstep).          │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 6  — Synthetic Case Generation               │
                    │  14 batches (v1 → v14) of synthetic cases, each     │
                    │  carrying Format 1 (timeline), Format 2 (tactical   │
                    │  triples), Format 3 (Passive/Proactive/Overstep).   │
                    │  Batches 1–2: 4 PNs. Batches 3+: 2 PNs.             │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 7  — PN Evaluation of Synthetic Cases        │
                    │  PNs scored Format 1/2/3 + overall field            │
                    │  authenticity (1–5) + reasoning + improvement       │
                    │  suggestion. Suggestions fed the next batch's       │
                    │  prompt revision.                                   │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 8  — Qwen Auditor (Inference)                │
                    │  Jackrong/Qwen3.5-2B-Claude-4.6-Opus-Reasoning-     │
                    │  Distilled produces Format 2 scores (1–5) and       │
                    │  Format 3 categories on the synthetic corpus.       │
                    │  Mandatory rationale before score.                  │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  STAGE 9  — Human Review of Qwen (RLHF surface)     │
                    │  One PN reviews Qwen's calls case-by-case:          │
                    │  Agree / Disagree + rationale + corrected score     │
                    │  or category. Output is the RLHF training signal.   │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  Fine-Tuning    │
                                    │  (next phase)   │
                                    └─────────────────┘
```

---

## The Patient Navigators — Onboarding Chronology

The project did **not** start with all four navigators in the room. It started with **one** — Kristin — and grew from there as the artifacts produced with her became concrete enough to onboard the others.

| Navigator | Joined at | Active through |
|---|---|---|
| **Kristin** | Stage 0 — sole participant in the initial interviews; the role definition, daily-work mapping, and insurance-landscape conversation all happened with her | Synthetic batch 2 |
| **Lyndsey** | Stage 1 / Stage 2 — joined when the other three were brought on to author Action Items lists and add their own seed cases | Synthetic batch 14 (deepest set, Cases 1–7 in seeds) |
| **Mark** | Stage 1 / Stage 2 — joined alongside Lyndsey and Melissa for case authoring | Synthetic batch 2 |
| **Melissa** | Stage 1 / Stage 2 — joined alongside Lyndsey and Mark for case authoring | Synthetic batch 14; finished the Qwen RLHF review (Stage 11) as the final remaining PN |

The "1 → 4 → 2 → 1" trajectory is worth naming up front: data-annotation projects in clinical settings rarely keep their full panel, and they often *don't start with one* either. Beginning with a single deeply-engaged navigator (Kristin) before scaling to a panel let us pressure-test the role definition and the meta-prompts in a low-stakes setting before the other three saw any of it. The pipeline was also designed so that the *highest-information* stages — seed-case authoring, the v1→v2 prompt iteration, and the Atlantis-Illusion-breaking v10 critiques — had the most navigator coverage, even as the panel later contracted.

---

## STAGE 0 — Initial PN Interviews (with Kristin only)

Before any artifact existed, we held semi-structured conversations with **Kristin** — the project's first navigator. Lyndsey, Mark, and Melissa were not involved at this stage; they were brought on later, once the role definition and meta-prompts produced with Kristin were concrete enough to hand to a wider panel.

The goals of these initial conversations:

- **Understand the role.** What does a PN do, and — more importantly — what are they *not allowed* to do?
- **Get volume context.** How many discharges does Kristin handle? What is her median caseload at any given moment?
- **Map the insurance landscape.** Medicare vs. Managed Medicare Advantage vs. Medicaid vs. CHC waiver. Which plans cause which kinds of friction?
- **Surface the daily texture.** We asked Kristin to describe her daily work to ChatGPT and to *let ChatGPT ask her clarifying questions* until the gaps were filled. This was deliberate — we wanted the AI's blind spots about the role to be exposed early, in a low-stakes setting with the most engaged navigator, before they could leak into production prompts seen by the rest of the panel.

The output of Stage 0 was not a deliverable file; it was a shared mental model — between Kristin and the team — of the PN role, its constraints, and the questions worth asking. From this point forward, every prompt we wrote could reference "the role we agreed on in the interviews" rather than guessing. When Lyndsey, Mark, and Melissa joined at Stage 1, they were onboarded against this already-validated frame rather than asked to negotiate it from scratch.

---

## STAGE 1 — Action Items Lists

Each navigator authored a structured **Action Items list** organized by phase of the patient transition:

- **Phase 1 — Assigned / New Referral.** Examples (from Kristin's list): *Confirm insurance eligibility. Identify short-term-discharge vs. long-term-care goal. Gather full demographic and contact info on day one. Ensure prompt notification of new wound-care admissions.*
- **Phase 2 — Inpatient at SNF / Maintaining the Case.** *Meet patients early. Build relationships with SNF social workers. Monitor progress via SNF updates.*
- **Phase 3 — Upcoming Discharge.** *Confirm first home appointment with patient. Meet with SW to gather final coordination info. Pass key info to in-home wound-care team. Share appointment back with the SW.*

Each line was an **Action + Intent** pair, e.g. *"Action: Build ongoing relationships with SNF SWs and staff. Intent: Ensure immediate updates if plans change and continue strong relationships for future referrals."*

These four lists were the raw input to the Action Taxonomy in Stage 5. Without them, the AI would have hallucinated a Liaison vocabulary based on its prior; with them, the taxonomy was sieved from the navigators' own verbs.

---

## STAGE 2 — Seed Case Collection (Streamlit App #1)

We built a Streamlit app for the navigators to document historical SNF cases. The app was deliberately split into two registers:

### Part A — Abbreviated Intake (Setting the Scene)

Designed to be **fast but high-context** — roughly the time it takes to describe a case to a colleague at the nurse's station. Three load-bearing fields:

| Field | Example |
|---|---|
| Patient Initials & Clinical Context | "M.B., 82yo with Parkinson's" |
| Primary Friction Point | "SW is gatekeeping face sheet" / "HHA is ghosting" |
| Current Transition Stage | Stage 1 (Intake) / Stage 2 (Maintenance) / Stage 3 (Transition) |

This forces the navigator to commit to a *clinical state*, a *specific friction*, and a *transition stage* before any AI generates anything — the three coordinates that anchor every downstream artifact.

The meta-prompt we used to design the intake bank:

> *"Create a set of intake questions for a veteran Patient Navigator that forces them to define the patient's clinical state, the specific friction in the facility, and the current 'Stage' of the transition (Intake, Maintenance, or Transition)."*

### Part B — Liaison Follow-Ups

Once the scene was set, an AI-generated follow-up bank extracted the **tactical** layer — what the navigator actually *did*, in the language of Verify / Flag / Educate rather than Resolve / Fix / Advocate. Three pillars:

| Pillar | Example Question |
|---|---|
| **Atlantis Audit** | "What specific discrepancy did you find between the Face Sheet and the Atlantis record?" |
| **Political Move** | "How did you alert the SW to this barrier without taking over the referral process?" |
| **Sentiment Check** | "How did the family's anxiety impact the timing of the Medical Assistant (MA) visit?" |

The meta-prompt that produced this bank:

> *"Generate follow-up questions that force the navigator to distinguish their role from a Social Worker. Focus on 'Verification' and 'Escalation' rather than 'Resolution'."*

This is the moment the **Liaison/Fixer dichotomy** entered the system. Every downstream artifact — the action taxonomy, the Format-3 Passive/Proactive/Overstep tiers, the Kill-Switch guardrails — is a refinement of this one instruction.

The follow-up bank had two variants depending on the case outcome:
- **Abbreviated** (patient discharged home) — max 12 questions, min 4 per section across (A) Reasoning Trace, (B) Discharge Timing Dynamics, (C) SNF Patient State Transitions & Navigator Time Allocation.
- **Abbreviated General** (any SNF outcome including return to hospital or death in SNF) — max 9 questions, 3 per section across (A) Reasoning Trace, (B) Early Warning Signals (LT vs Hospital), (C) Decision Points & Triggers.

Both variants enforced: past tense, every question must reference a specific case detail (e.g., ramp, CHC waiver, HHA), no abstract jargon ("mental model," "leading indicators"), no hypotheticals not triggered by the case.

---

## STAGE 3 — Audit Questions

For each seed case, we ran a separate prompt (in Gemini) that took the case as input and produced **5 audit questions per case**. These were AI-generated probes of *what the PN might have missed* — overlooked options, unexplored angles, misinterpreted information.

The PNs then ranked each audit question on a binary scale:

| Rank | Meaning |
|---|---|
| **0** | Not insightful / not part of the PN job role |
| **1** | Insightful and part of the PN job role |

Plus an explicit instruction: *answer every question you ranked 1.* That meant a Rank-1 audit question forced the navigator to actually write the missing-but-relevant follow-up they would have asked themselves.

Concrete pattern from Kristin's annotations:

> *"Audit Answer 3: The PN did not specifically ask about how frequently the patient's surgeon's follow-up appointments would occur. If the four-week interval had been known from the start, it would have likely prompted the PN to change the estimated discharge timeline beyond the 100-day mark on day one."* — Ranked 1.

The audit-question rankings became a **data point we fed back to the AI** when designing both the taxonomies and the synthetic-case generation prompts. They told us which classes of question were genuinely role-relevant vs. which were AI-generated noise.

---

## STAGE 4 — Follow-Up Question Ranking

Once the navigators had answered their seed-case follow-ups, we asked them to rank the follow-up questions themselves on three binary criteria:

| Criterion | 1 means |
|---|---|
| **Wordy** | The question is too long / over-engineered |
| **Case-Specific** | The question references concrete case details (good) |
| **Relevance** | The question is genuinely useful to a PN (good) |

This was a critique loop on the *meta-prompt* itself. Patterns we saw:

- Questions that scored Wordy=1 / Case-Specific=0 / Relevance=0 → the meta-prompt was generating abstract jargon. We tightened the instruction to *"every question must reference a specific case detail."*
- Questions that scored Wordy=1 / Case-Specific=1 / Relevance=1 → the question was good but the prompt was producing them as long compound sentences. We added the rule *"prefer 1-sentence questions."*
- Questions that scored Case-Specific=0 across multiple PNs → those question templates were dropped from the bank.

The output of Stage 4 was a **revised meta-prompt** for the follow-up bank, which the navigators then used to answer a new round of follow-ups.

---

## STAGE 5 — Taxonomy Construction

With the action items lists (Stage 1), the audit-ranking signal (Stage 3), and the follow-up rankings (Stage 4) in hand, we worked with AI to construct three controlled vocabularies:

### Action Taxonomy
The constrained verb set the PN is permitted to use, anchored to **Verify / Flag / Educate** plus adjacent neutral verbs (alert, document, refer, audit, ask). Built from the navigators' Action Items lists and the actions present in their Rank-5 (Masterful) seed cases.

### Friction Taxonomy
The categorized obstacle set a case can surface — insurance denials, transport delays, SW non-response windows, family anxiety, demographic mismatches, EDD-delta categories. Built from the friction patterns in the seed cases.

### Outcome Taxonomy
The discrete outcome states a case can resolve to: `Success_Home_with_First_Visit`, `Failure_Transition_Breakdown`, `Neutral_LTC_Closure`, `Neutral_Alternative_Agency`.

### How the Rank-5 vs Rank-2 sieving worked

- **Promotions to canonical (from Rank-5 cases)**: actions like `Verify_Demographics`, `Educate_on_MA_Visit`, `Document_Communication_Gap`, `Refer_Family_to_SW`, and (added later) `Manual_SW_Status_Inquiry`.
- **Demotions / bans (from Rank-2 cases)**: actions like `Call_HHA_Intake`, `Recommend_Specific_Agency`, `Lead_Care_Conference`, `Schedule_MA_Before_HHA_Confirmation`, `Relay_Family_Concern_to_SW_on_Behalf`. These became the seeds of the Banned Actions list (see Kill-Switch Guardrails below).
- **Friction removals (v13)**: frictions tied to clinical-documentation problems the PN cannot legitimately know about — `Missing_HHA_Orders`, `Handoff_Data_Mismatch` — were removed because their presence implied the PN had visibility they don't actually have.

Together, these three JSONs became the bounded vocabulary that prevents a generated case from drifting into freeform clinical, advocacy, or vendor-recommendation language.

---

## STAGE 6 — Synthetic Case Generation (14 Batches)

With taxonomies locked, we generated synthetic cases in batches. Each case carried three parallel evaluation surfaces:

| Format | What it captures |
|---|---|
| **Format 1 — State Log** | A timeline of events. Each event has a description (in PN voice — information arrives via SW or family, never by "reading a system"), a clinical impact, an environmental impact, a service-adoption impact, an EDD delta, and an AI-assumed bottleneck. |
| **Format 2 — Reasoning Triples** | A list of `(Situation, Intent, Action Taken)` triples. Each triple represents a single tactical decision the navigator made. |
| **Format 3 — RL Scenarios** | Exactly three options per case — one Passive (Strategic Deferral), one Proactive (Within-Lane), one Overstep (Banned Interference) — designed to surface boundary judgment under realistic pressure. |

Total volume across the 14 batches: **406 synthetic cases**. Batches 1–2 had four navigators reviewing; batches 3–14 ran with two.

### Per-batch system prompts

Every batch had its own system-prompt version (v1 → v14) embedded in `data/prompts/current_prompt.json`. The system prompt contained:
- The **PN role definition** (a master of professional communication; bridges facility and home; documents in Atlantis; supports the family).
- A precise **"What Atlantis Is / Is Not"** block (added after Stage 8 / v10 — see "Atlantis Illusion" below).
- The three channels through which the PN gets updates (SW contacts the PN; family contacts the PN; PN asks the SW directly). If none of these have happened, the PN does not have the information.
- The four **Operational Guardrails** (No-Vendor / Wait Default / Discharge Ownership / PN Endpoint).
- The **Banned Actions** list (automatic Overstep).
- A **Prose-Only Mandate** (taxonomy keys with underscores must never appear in narrative text).
- **Storytelling rules** — narrative summary structure, "fog of war" requirement, banned tropes (`F2F signatures`, `burned-out Social Worker`, `100-day financial cliff`, etc.).

---

## STAGE 7 — PN Evaluation of Synthetic Cases (Streamlit App #2)

After each batch was generated, the navigators reviewed every case in a second Streamlit app — the **Annotation Platform**. (This is the same app that, in Stage 9, hosts the Qwen RLHF review surface.)

For each case, the navigator scored:

- **Format 1** — for each timeline event: clinical impact (Improves/Worsens/Unchanged/Unclear), environmental impact, home-service-adoption impact, EDD delta (eight buckets from `+ >14 Days` to `- >14 Days`), and a True/False judgment on whether the AI-assumed bottleneck was realistic.
- **Format 2** — for each tactical triple: a **Tactical Viability Score (1–5)** with anchors **1 = Politically Reckless, 5 = Masterful Field Move**.
- **Format 3** — for each of the three options: a **Passive / Proactive / Overstep** classification.
- **Final — Overall Field Authenticity** — a single 1–5 score (*"1 = Completely Artificial, 5 = Highly Authentic / Rings 100% True"*) plus two free-text fields: *"Why did you give this score?"* and *"What is one specific change that would make this case feel more realistic?"*

The improvement-suggestion field was the **closing-the-loop primitive**: each batch's improvement suggestions, in aggregate, became the input to the next batch's prompt revision.

---

## STAGE 8 — The Iteration Arc (v1 → v14)

The 14 batches are *not* fourteen redundant runs. Each version was a sharper cut at the same target, driven by what the navigators flagged in Stage 7. The core tension the iteration was working through: **the AI wants to be helpful; the PN must be politically neutral.**

| Batch | Driving Input | Key Learning / Logic Shift |
|---|---|---|
| **v1–v4** | Initial brainstorm + first-batch reviews | **AI is too "helpful."** It acted like a Case Manager, not a Liaison — rewrote clinical plans, advocated for vendors, inserted opinion into adjudication-bound situations. "Political overstepping" surfaced as the core failure mode. |
| **v5–v7** | Action Taxonomy (Stage 5 output) | **Role hardening.** The **No-Vendor Rule** was defined: the PN only talks to Families and SWs. JSON taxonomies imposed as hard constraints on generation. |
| **v8–v9** | Navigator feedback logs | **"Bot-Speak" fix.** Taxonomy keys with underscores (e.g. `HHA_Acceptance_Stall`) were leaking into the prose. Output read like a templated clinical-customer-service script. The Prose-Only Mandate was introduced and applied retroactively. |
| **v10** | `evaluation_sessions_v10_rows.csv` | **The Atlantis Illusion broken.** Navigators flagged that the AI thought Atlantis was a live clinical feed. PNs actually have *no visibility* into SW or HHA notes. (See dedicated section below.) |
| **v11** | Improvement-suggestion analysis | **Manual Inquiry.** Added `Manual_SW_Status_Inquiry` because PNs must work for their data verbally — phone, text, hallway conversation, case-conference notes. Verbal inputs became first-class evidence. |
| **v12** | Stress-test runs | PN Endpoint sharpening for post-discharge cases; first hard pass at *"the PN's role ends when the MA visit is scheduled."* |
| **v13** *(current)* | Cross-corpus regression | **Evaluation-Refined Taxonomy.** Removed PN intermediary patterns (`Verify_Sentiment_Score`, `Request_Joint_Family_Meeting_via_SW`); removed clinical-documentation frictions (`Missing_HHA_Orders`, `Handoff_Data_Mismatch`); explicitly clarified that the SW cannot see Atlantis; strengthened the PN Endpoint. **17 actions, 21 frictions.** |
| **v14** | v13 stress regression | Iteration of v13 conventions with tightened narrative tone. |

---

## STAGE 8b — The Atlantis Illusion (Inflection Point)

This is the single most reproducible learning of the project, and the meta-pattern most worth mimicking for a different navigator vertical.

Before v10, the system prompt assumed Atlantis behaved like a live EMR feed — the model wrote cases where the PN "checks Atlantis" for SW updates, HHA referral statuses, and medication lists. The navigators flagged this in the Stage-7 improvement suggestions of three specific cases:

| Case | Improvement Suggestion (Verbatim Style) | Resulting v11 Change |
|---|---|---|
| **Case 10** | The PN cannot "see" SW updates in Atlantis; updates are obtained verbally. | Atlantis re-scoped to *"the PN's personal documentation tool"*; banned all language implying live SW visibility. |
| **Case 21** | PN must work for clinical context — call/text/in-person, not via portal. | Introduced `Manual_SW_Status_Inquiry` as a first-class action. |
| **Case 24** | The portal is **not** a shared communication channel between PN and SW. | Wait Default formalized: *"If the SW has not provided an update, the PN documents the gap and waits."* |

After v10, Atlantis was reframed as **the PN's own notebook** — and from that single reframing, the No-Vendor Rule, Wait Default, and Manual Inquiry logic followed naturally. Cases 10, 21, and 24 are preserved in the corpus as the "before" reference for any future regression test.

**Meta-lesson for a different navigator vertical**: *Your system-of-record assumption is probably wrong.* Find the equivalent inflection in your domain — the moment when a navigator says "we don't actually see that" — and rebuild the prompt around the actual information-flow.

---

## STAGE 9 — The Four Kill-Switch Guardrails

These four rules are non-negotiable across the entire generated corpus. Any Format-2 action that violates one is — by construction — capped at Score ≤ 2; any Format-3 option that violates one is classified Overstep.

| Rule | Statement |
|---|---|
| **No-Vendor Rule** | The PN never calls HHAs, DME vendors, or transport companies. The PN only communicates with the Family and the Social Worker. |
| **Wait Default** | If the SW has not provided an update, the PN documents the communication gap and waits. The PN does not seek the information from other sources. |
| **Discharge Ownership** | The SW owns the discharge process. The PN does not drive the discharge timeline, negotiate dates, or initiate discharge planning. The PN does not get involved in HHA orders, medication lists, or clinical documentation. |
| **PN Endpoint** | The PN's role ends when the patient is discharged AND the MA first visit is scheduled within 24 hours. After this, the case transitions to the MA and Healing Partners care management. |

For a different navigator vertical, the *content* of these four rules will change — but the *pattern* is what to mimic. Define 3–5 hard "this is automatically out-of-role" rules early, derive them from real Rank-2 cases (not from imagination), and use them as the spine of every downstream evaluation.

---

## STAGE 10 — The Qwen Auditor (Inference)

With the synthetic corpus stable through v14, we moved to the next phase: training a small reasoning model to mimic the navigators' Format 2 / Format 3 grading, then doing **error analysis** on the model's calls before fine-tuning.

### Model Choice

- **Model**: `Jackrong/Qwen3.5-2B-Claude-4.6-Opus-Reasoning-Distilled` (Hugging Face)
- **Why a small model**: a 2B-parameter reasoning-distilled model that can correctly classify boundary violations is a *proof of taxonomy clarity*. If the rules are unambiguous, a small model should be able to apply them. It also keeps the human annotator's role unambiguous (agree, disagree, or correct).
- **Why reasoning-distilled**: the grading task is decompositional — read the case, locate the relevant guardrail, decide if the action respects it. Reasoning-distilled bases handle this kind of step-wise judgment far better than vanilla instruction-tuned models of the same size.

### The Setup Prompt (in Gemini, when scoping the work)

This is the prompt we used to scope the Qwen integration with an AI assistant. Including a shortened version here as an exhibit, since it captures the framing we operated under:

> *"Our end goal is to create a patient navigator chatbot. I will give you a system prompt that includes the role of the patient navigator, what they do and don't do, where they input/gather data, an example of a case that they don't do, and an example of a case that they do. Then I will give you a user prompt with a new case that I want you to verify whether it [is] the role of a patient navigator on a scale of 1–5. We're doing this to do error analysis and compare the model's role-verification scores [against] those annotated by humans. Once we get that data, we will want to fine-tune the model to better determine the role of the patient navigator."*

We attached the **v13 system prompt** (the Evaluation-Refined Taxonomy — same prompt that drove synthetic-case generation), plus two anchored examples:
- A **Rank-1 case** (Case 14, batch v1) where the PN bypassed the SW, called the HHA pharmacist directly, and "advocated" the family into refusing discharge — every Kill-Switch rule violated, used as the canonical "not the PN role."
- A **Rank-5 case** (Case 8, batch v14) where the PN documented the agency stall, asked the SW for a verbal update, educated the family on the MA visit, and corrected the demographic record in Atlantis — clean liaison work, used as the canonical "this is exactly the PN role."

The user prompt was a **new synthetic case** the model had not seen, and the model was asked to score Format 2 (1–5) and classify Format 3 (Passive / Proactive / Overstep). Crucially, the model was required to **write a rationale before assigning a score**. We discovered early that without the rationale, the 2B model collapses (frequent `None` returns, incoherent classifications). Chain-of-thought is a hard requirement at this scale.

### Inference vs. Fine-Tuning Prompt Length

A pragmatic note on prompt length, which came up while scoping this stage:
- **At inference**, the long v13 prompt is fine. Latency and token cost are tolerable for an audit pipeline.
- **At fine-tuning**, the prompt should shrink — but selectively. *Keep* the role definition, the four Kill-Switch rules, and a one-line Atlantis frame. *Cut* the meta-instructions about prose-vs-underscores, the banned-tropes list, and the storytelling rules — those exist for *generation*, not for a 1–5 *scoring* task.

---

## STAGE 11 — Human Review of Qwen (RLHF Surface)

The same Streamlit Annotation Platform that hosted Stage 7 has a second page — the **RLHF Q&A page** — where one navigator reviews Qwen's calls case by case.

For each case the page shows the narrative summary, then expanders for each Format-2 triple and Format-3 option. Inside each expander:
- The situation / action / intent (or scenario description).
- **Qwen's score (1–5) or category** with its **rationale**.
- An **Agree / Disagree** radio with no default (forces an explicit choice).
- A free-text field prompted *"I agree or disagree with Qwen's score because:"*
- If the navigator selects Disagree, a conditional control to enter the **corrected score** (1–5) or **corrected category** (Passive / Proactive / Overstep).

Saves are split by section (Format 2 / Format 3) and triggered with explicit buttons. When a case is fully complete (both sections done), the toast reads "Case Annotations Saved" instead of the per-section message.

**Output of Stage 11**: a paired dataset of `(case, Qwen score+rationale, human agreement, optional human correction+rationale)`. This is the RLHF training signal — both the SFT target (`human_corrected_score` / `human_corrected_category`) and the DPO preference pair (Qwen's call vs. the corrected call).

---

## Reproducibility Notes — Pattern for Another Navigator Vertical

The role we trained on is specific to Healing Partners' Patient Navigators in skilled-nursing-facility transitions. The *pattern* is generalizable. To redo this for a different navigator vertical:

1. **Start with one navigator, not a panel.** Stage 0 (interviews and role definition) should happen with a single deeply-engaged navigator before any artifact is shown to the wider group. Get the role's vocabulary, volume, and constraint structure from one person's mouth *before* writing any prompt — let an AI ask them clarifying questions and record where the AI guesses wrong. Only once the meta-prompts and role frame are validated should the rest of the panel be onboarded (typically at Stage 1, the Action Items list, or Stage 2, the seed-case authoring). This sequence avoids negotiating role boundaries by committee, and gives the later joiners a stable frame to react to rather than build from scratch.
2. **Ask each navigator for a phased Action Items list.** This is the seed of the Action Taxonomy. Skip this stage and the AI will hallucinate the verbs.
3. **Build a two-part annotation app.** Part A is a fast scene-setter (clinical state + friction + stage). Part B extracts the *tactical layer* with AI-generated follow-ups designed to distinguish the navigator's role from adjacent roles. The meta-prompts that produce Parts A and B are the leverage points — they encode the role boundary.
4. **Run AI-generated audit questions on each seed case** and have the navigators rank them 0/1. This surfaces which classes of question are role-relevant and which are noise.
5. **Run the navigators' follow-up-question rankings** (we used 0/1 across Wordy / Case-Specific / Relevance) on every batch of follow-ups, and use the ranking pattern to revise the meta-prompt.
6. **Sieve the taxonomies from real Rank-5 vs Rank-2 cases**, not from imagination. Rank-5 cases promote vocabulary; Rank-2 cases ban it.
7. **Generate in batches and iterate.** Plan for ~10–15 batches. Most of the value comes from the navigators' free-text *improvement suggestions* on each case, not from the numeric scores. The numeric scores are how you triage; the improvement suggestions are how you *learn*.
8. **Find your Atlantis Illusion.** Every domain has an assumption about a system-of-record that the navigators don't actually have access to. Find it. The reframe that follows is the largest single quality jump you'll get.
9. **Define 3–5 Kill-Switch rules** before you start generating at scale. Derive them from observed Rank-2 (Overstep) cases. They become the spine of every downstream evaluation.
10. **Audit with a small reasoning model before fine-tuning.** Use a 2B-class reasoning-distilled model with a mandatory rationale step. The cases where the small model and the navigator disagree are exactly the cases you want in the fine-tuning set.

---

## What Comes Next

The pipeline up to Stage 11 produces a complete RLHF-ready dataset. The remaining steps — outside the scope of the work documented here — are:

- **Level 1 Supervised Fine-Tuning** of `Jackrong/Qwen3.5-2B-Claude-4.6-Opus-Reasoning-Distilled` on the human-corrected scores and categories.
- **DPO (Direct Preference Optimization)** using the paired (Qwen call, corrected call) data from Stage 11 — particularly the v6 "Overstep" failures paired against v11+ "Masterful Moves," which is the founding preference signal of the dataset.
- **Held-out evaluation** against a canary set built from the three Atlantis-Illusion-breaking cases (Cases 10, 21, 24) to confirm the largest reframe of the project survives fine-tuning intact.

---

*End of document. Generated 2026-05-04.*
