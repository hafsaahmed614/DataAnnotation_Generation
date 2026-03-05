# Data Annotation Flywheel Playbook

A domain-agnostic methodology for building data flywheels through expert interviews, seed case design, taxonomy construction, synthetic data generation, and iterative expert annotation.

---

## Table of Contents

1. [Overview](#overview)
2. [The Flywheel Model](#the-flywheel-model)
3. [Phase 1: Intent Discovery](#phase-1-intent-discovery)
4. [Phase 2: Seed Case Design](#phase-2-seed-case-design)
5. [Phase 3: Constraint System Design](#phase-3-constraint-system-design)
6. [Phase 4: Synthetic Case Generation](#phase-4-synthetic-case-generation)
7. [Phase 5: Annotation Platform & Expert Review](#phase-5-annotation-platform--expert-review)
8. [Phase 6: Feedback Loop & Iteration](#phase-6-feedback-loop--iteration)
9. [Process Assessment & Lessons Learned](#process-assessment--lessons-learned)
10. [Quick-Start Checklist](#quick-start-checklist)

For deep-dives on each phase, see the [`docs/`](./docs/) folder.

---

## Overview

The goal of this playbook is to establish a repeatable process for any domain where:

1. You need to capture expert decision-making that lives in people's heads, not in databases
2. You want to generate synthetic training data that experts validate as authentic
3. You want a feedback loop where expert annotations improve future synthetic data

This process was developed and battle-tested on a healthcare patient navigation project, but the methodology applies to legal case analysis, customer service escalation, financial risk assessment, or any domain with complex expert judgment.

---

## The Flywheel Model

```
                    +---------------------+
                    | Intent Discovery    |
                    | (Expert Interviews) |
                    +--------+------------+
                             |
                             v
                    +--------+------------+
                    | Seed Case Design    |
                    | (Structured Cases)  |
                    +--------+------------+
                             |
                             v
                    +--------+------------+
                    | Constraint System   |
                    | Design (mine seeds) |
                    +--------+------------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
         Taxonomies    RAG / Vector   Knowledge Graph
         (categories)  (few-shot)     (entity triples)
              |              |              |
              +--------------+--------------+
                             |
                             v
                    +--------+------------+
                    | Synthetic Case      |
                    | Generation (LLM)    |
                    +--------+------------+
                             |
                             v
                    +--------+------------+
                    | Expert Annotation   |
                    | & Scoring           |
                    +--------+------------+
                             |
                             v
                    +--------+------------+
                    | Feedback Analysis   |----> Refine constraints,
                    | & Schema Evolution  |      prompts, and schema
                    +---------------------+      then re-generate
```

The flywheel accelerates because each round of expert annotation:
- Reveals missing constraint categories (new taxonomy entries, new entity relationships, new retrieval signals)
- Exposes unrealistic synthetic patterns ("banned tropes")
- Sharpens the generation prompts
- Evolves the data schema toward higher fidelity

---

## Phase 1: Intent Discovery

**Goal:** Understand what decisions experts make, what information they use, and what makes cases hard.

**Process:**
1. **Single-expert deep dive** -- Start with one domain expert. Map their entire workflow: daily tasks, decision points, information sources, tools, stakeholders, success/failure criteria.
2. **Panel expansion** -- Expand to 3-5 experts with diverse experience. Conduct structured interviews to surface disagreements and edge cases.
3. **Intent extraction** -- Identify the core "intents" (the decisions/actions experts take). These become the backbone of your taxonomy and annotation schema.

**Key Principle:** The initial intent will evolve. You won't discover all intents upfront. The flywheel exists precisely to surface intents you didn't know to ask about.

**Output:** A documented understanding of the expert workflow, a list of candidate intents, and identified friction points / complexity drivers.

See: [`docs/01-intent-discovery.md`](./docs/01-intent-discovery.md)

---

## Phase 2: Seed Case Design

**Goal:** Collect real-world cases from experts in a structured JSON format that can serve as few-shot examples for LLM generation.

**Process:**
1. **Design a case submission instrument** -- Build a simple app (or form) where experts can submit historical cases they've personally handled. Structure it in 3 sections:
   - **Demographics / Context** -- Who is the subject? What's the setting?
   - **The Case Narrative** -- What happened? What barriers arose? What decisions were made?
   - **Outcomes / Services** -- What was the result? What actions were taken?
2. **Target 10-20 seed cases** across 3-5 experts, covering a range of complexity and outcomes.
3. **Transform submissions into structured JSON** with consistent field names.
4. **Mine seed cases for constraint signals** -- Analyze the structured cases to determine which constraint techniques (taxonomies, RAG, knowledge graphs) are appropriate. This analysis feeds directly into Phase 3.

**Key Principle:** Seed cases are the DNA of your synthetic data. If they're shallow, your synthetic cases will be shallow. Invest in extracting rich, detailed cases from experts who have years of experience. The seed cases also determine your constraint strategy -- different patterns in the data call for different representation techniques.

See: [`docs/02-seed-case-design.md`](./docs/02-seed-case-design.md)

---

## Phase 3: Constraint System Design

**Goal:** Mine seed cases to determine which combination of constraint techniques -- **Taxonomies**, **RAG**, and/or **Knowledge Graphs/Triples** -- best fits your intent and data. These are not mutually exclusive; most projects benefit from combining two or all three.

**The Three Techniques:**

| Technique | Best When Seed Cases Reveal... | What It Gives the LLM |
|---|---|---|
| **Taxonomies** | Categorical, enumerable domain knowledge (friction types, action categories, outcome states) | Hard constraints on valid values; prevents hallucination of domain-specific details |
| **RAG (Vector Retrieval)** | Rich narrative detail and operational complexity that the LLM needs to mimic in tone, depth, and structure | Grounded few-shot examples retrieved by semantic similarity to the target scenario |
| **Knowledge Graph / Triples** | Complex entity relationships, causal chains, state transitions, or multi-stakeholder dependencies | Structured reasoning paths (entity -> relationship -> entity) that enforce logical consistency |

**How to Decide:** Analyze your seed cases and ask:
1. **Are there recurring categories** that you could enumerate? (friction types, error classes, outcome states) --> **Taxonomy**
2. **Do cases vary in narrative richness** and you need the LLM to match the best ones? --> **RAG**
3. **Do cases contain causal reasoning chains** (situation -> action -> intent -> result) or entity-relationship networks (stakeholders, dependencies, handoffs)? --> **Knowledge Graph / Triples**

**Design Principles (all techniques):**
1. Every constraint entry should carry a **"logical DNA rule"** -- the *why* behind the constraint, not just the label
2. Constraints **evolve** with each annotation round. New entries get added, stale ones get merged or removed.
3. Version your constraint files alongside generation batches

See: [`docs/03-constraint-system-design.md`](./docs/03-constraint-system-design.md)

---

## Phase 4: Synthetic Case Generation

**Goal:** Use an LLM, augmented by whichever constraint systems you selected in Phase 3, to generate synthetic cases that mimic the depth and realism of seed cases.

**Architecture:**
The generation pipeline adapts based on which constraint systems are active:

1. **Taxonomy injection:** Load taxonomy JSON files and inject them as structured context. The LLM is instructed to select values only from the taxonomy.
2. **RAG retrieval:** Query the vector store for seed cases similar to the target scenario. Inject 2-3 as few-shot examples. Use metadata filters (complexity, outcome type) and semantic search.
3. **Knowledge graph / triple injection:** Extract entity-relationship triples from seed cases and inject them as reasoning templates. The LLM is instructed to generate new triples following the same structure and logical patterns.
4. **Prompt assembly:** Combine active constraint layers with the system prompt, target variables, and output schema.
5. **Validation:** Parse LLM output against a Pydantic schema. Retry on failure.
6. **Batch generation:** Generate 20-30 cases per round, randomizing target variables to ensure diversity.

**Key Principles:**
- Use **structured output** (JSON mode / Pydantic validation) to guarantee format consistency
- Include a **"Banned Tropes"** list in the system prompt -- patterns that previous rounds revealed as unrealistic or repetitive
- Enforce **diversity** through explicit subject/friction randomization and quotas
- The **combination of constraint systems** is the key differentiator. Taxonomies alone produce valid-but-flat cases. RAG alone produces rich-but-unconstrained cases. Knowledge graphs alone produce logically-consistent-but-formulaic cases. Together, they produce cases that are valid, rich, AND logically sound.

See: [`docs/04-synthetic-generation.md`](./docs/04-synthetic-generation.md)

---

## Phase 5: Annotation Platform & Expert Review

**Goal:** Build a lightweight annotation UI where domain experts evaluate synthetic cases for authenticity.

**Platform Design:**
1. **Role-based access** -- Admins upload/manage cases; annotators (domain experts) evaluate them
2. **Multi-format evaluation** -- Each case is evaluated across multiple dimensions (your formats). Don't just ask "is this realistic?" -- break it into specific, scoreable components:
   - **Timeline/Event realism** -- Are the barriers and delays realistic?
   - **Action/Decision quality** -- Are the expert actions tactically viable?
   - **Boundary compliance** -- Do the actions respect role boundaries?
3. **Overall authenticity score** (1-5 scale) plus free-text reasoning
4. **Auto-save** -- Don't lose expert time. Save on every interaction.
5. **Improvement suggestions** -- Always ask "What one change would make this more realistic?"

**Storage:**
- Store cases and evaluations in a database (e.g., Supabase/PostgreSQL) with RLS policies
- Version your schema tables (v1, v2, v3...) to preserve evaluation data across schema changes

See: [`docs/05-annotation-platform.md`](./docs/05-annotation-platform.md)

---

## Phase 6: Feedback Loop & Iteration

**Goal:** Use annotation results to improve the next generation round.

**Process:**
1. **Quantitative analysis** -- Aggregate authenticity scores. Which cases scored lowest? Which evaluation dimensions had the most disagreement?
2. **Qualitative analysis** -- Read free-text reasoning and improvement suggestions. Look for recurring themes.
3. **Identify schema gaps** -- If annotators consistently say "this field is missing" or "this doesn't capture X," evolve the schema.
4. **Update constraint systems** -- Add new taxonomy entries, triple schemas, or RAG configurations surfaced by expert feedback.
5. **Refine prompts** -- Add banned tropes, adjust system prompt constraints, modify format rules.
6. **Re-generate and re-annotate** -- Run a new batch with the improved pipeline.

**Iteration Cadence:**
- Plan for **3-5 rounds** minimum before the flywheel produces consistently high-authenticity data
- Each round should produce a versioned backup of both the synthetic cases and the schema

See: [`docs/06-feedback-loop.md`](./docs/06-feedback-loop.md)

---

## Process Assessment & Lessons Learned

Based on this project's experience across 5 schema versions and 5 annotation rounds:

### What Worked Well

1. **Expert-first approach** -- Starting with a single deep-dive interview before expanding to a panel ensured we understood the domain before designing anything.
2. **Structured seed case collection** -- The 12-question, 3-section app gave experts a consistent framework for submitting cases without overwhelming them.
3. **Multi-technique constraint system** -- Using taxonomies (categorical constraints), RAG (narrative grounding), and knowledge graph triples (reasoning chain structure) together produced synthetic cases that were valid, detailed, AND logically consistent.
4. **RAG for few-shot retrieval** -- ChromaDB made it easy to retrieve relevant seed cases based on target friction, ensuring synthetic cases matched the detail level of real cases.
5. **Versioned schema evolution** -- Preserving V1-V5 tables meant we never lost evaluation data, even as the schema changed dramatically.
6. **Auto-save in the annotation app** -- Domain experts are busy. Losing their work would have killed participation.
7. **Banned tropes list** -- Explicitly telling the LLM what NOT to generate (based on prior round feedback) was one of the most effective prompt engineering techniques.

### What Could Be Improved

1. **Formalize the feedback analysis step** -- The transition from "read comments and make changes" to "systematic analysis with thresholds" should happen earlier. Define upfront: "If >30% of cases score below 3 on authenticity, we trigger a schema revision."
2. **Inter-annotator agreement tracking** -- Multiple experts annotating the same case reveals where the taxonomy is ambiguous. This was done implicitly (unique constraint on case_id + navigator_id) but the analysis pipeline wasn't built.
3. **Constraint artifact versioning** -- Taxonomy files, triple schemas, and RAG configurations evolved but weren't versioned alongside the schema. Future projects should version-lock all constraint artifacts to generation batches.
4. **Seed case expansion** -- 15 seed cases from 4 experts was a solid start, but the RAG retrieval was limited by this small corpus. A mechanism to promote high-scoring synthetic cases back into the seed pool would strengthen the flywheel.
5. **Prompt version control** -- The system prompt and format rules evolved across commits but weren't tracked as a discrete artifact. Consider a `prompts/` directory with versioned prompt files.
6. **Missing analytics dashboard** -- While the admin dashboard existed, a dedicated analytics view (score distributions, inter-rater reliability, improvement trends across rounds) would have made the feedback loop more data-driven.
7. **Case debrief sessions** -- After each annotation round, a group session where experts discuss edge cases and disagreements would surface richer insights than individual written feedback alone.

See: [`docs/07-assessment.md`](./docs/07-assessment.md)

---

## Quick-Start Checklist

When starting a new data annotation project, follow this checklist:

### Week 1-2: Intent Discovery
- [ ] Identify 1 lead domain expert for deep-dive interview
- [ ] Map the complete expert workflow (tasks, decisions, tools, stakeholders)
- [ ] Identify 3-5 panel experts with diverse experience
- [ ] Conduct panel interviews; extract candidate intents and friction points
- [ ] Document initial intent list and complexity drivers

### Week 2-3: Seed Case Design
- [ ] Design case submission instrument (app/form) with 3 sections
- [ ] Collect 10-20 seed cases from panel experts
- [ ] Transform into structured JSON with consistent schema
- [ ] Analyze seed cases for constraint signals (categorical patterns, narrative depth, causal chains)

### Week 3-4: Constraint System Design
- [ ] Analyze seed cases: identify categorical patterns (taxonomies), narrative depth (RAG), and causal chains (knowledge graph/triples)
- [ ] For each identified pattern, choose the appropriate constraint technique
- [ ] Build Friction/Barrier taxonomy with logical DNA rules (if applicable)
- [ ] Build Action taxonomy organized by workflow stages (if applicable)
- [ ] Build Outcome taxonomy with trigger conditions (if applicable)
- [ ] Define entity-relationship triple schema for reasoning traces (if applicable)
- [ ] Vectorize seed cases into ChromaDB or similar for RAG retrieval (if applicable)
- [ ] Review all constraint artifacts with at least 2 domain experts

### Week 4-5: Generation Pipeline
- [ ] Write system prompt defining expert role and constraints
- [ ] Build prompt assembly integrating active constraint systems (taxonomies, RAG, knowledge graph)
- [ ] Define Pydantic output schema
- [ ] Generate first batch of 20-30 synthetic cases
- [ ] Validate all cases pass schema validation

### Week 5-6: Annotation Platform
- [ ] Build or deploy annotation UI with role-based access
- [ ] Upload synthetic cases to database
- [ ] Onboard expert annotators
- [ ] Run first annotation round

### Week 6+: Iterate
- [ ] Analyze scores and free-text feedback
- [ ] Update taxonomies, schema, and prompts
- [ ] Generate next batch
- [ ] Repeat until authenticity scores stabilize at >= 4/5

---

## Project Structure (Reference)

```
project/
  data/
    seed_cases/              # Expert-submitted real cases (JSON)
    taxonomies/              # Constraint files: taxonomies, triple schemas
    synthetic_batch_N/       # Generated cases per round
    synthetic_batch_N_vX_backup/  # Archived batches from prior rounds
  chroma_db/                 # Vector store for seed case retrieval
  app/                       # Annotation platform (Streamlit + Supabase)
    pages/
      login.py
      annotation.py
      pn_dashboard.py
      admin_dashboard.py
  docs/                      # Deep-dive documentation
  ingest_seeds.py            # Phase 3: Vectorize seed cases for RAG
  generate_synthetic.py      # Phase 4: Single-case generation
  generate_batch_25.py       # Phase 4: Batch generation
  upload_cases.py            # Upload generated cases to annotation DB
  supabase_schema.sql        # Database schema (versioned tables)
  PLAYBOOK.md                # This file
```
