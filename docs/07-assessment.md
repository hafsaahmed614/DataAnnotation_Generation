# Process Assessment

A candid evaluation of what this project did well, what could be improved, and concrete recommendations for future data annotation projects.

---

## What This Project Got Right

### 1. Expert-First, Schema-Second

The decision to start with a single deep-dive interview, expand to a panel of 4 navigators, and THEN build an app for case submission was the correct sequencing. Too many data projects start by designing the schema and then asking experts to fit their knowledge into it. This project did the reverse: understand the domain first, then design a schema that captures it.

### 2. Structured Seed Case Collection

The 12-question, 3-section app gave experts a consistent framework without being so rigid that it lost nuance. The reasoning trace triples (situation -> action -> intent -> result) were particularly well-designed -- they capture the decision-making logic that's hardest to synthesize from scratch.

### 3. Taxonomy as LLM Constraint

Injecting taxonomies directly into the LLM prompt prevented the most common failure mode of synthetic data: hallucinated domain-specific details. The "logical DNA rules" in the Friction Taxonomy were especially effective -- they gave the LLM a causal mechanism, not just a label.

### 4. Iterative Schema Evolution (V1-V5)

The willingness to overhaul the schema 5 times, while preserving all prior evaluation data in versioned tables, showed good engineering discipline. Each version addressed real feedback:
- V3: Diversity enforcement
- V4: "Support, Suggest, Escalate" mentality shift
- V5: 3-Stage Lifecycle alignment with the Atlantis software

### 5. Banned Tropes List

This was one of the most effective prompt engineering techniques. By explicitly telling the LLM what NOT to generate (based on annotator feedback), the team eliminated the 5 most common unrealistic patterns in a single iteration.

### 6. Auto-Save in the Annotation App

This is a detail that's easy to overlook and catastrophic to get wrong. The auto-save on every Streamlit widget interaction meant zero data loss, even when experts closed their browser mid-evaluation.

### 7. Multi-Format Evaluation

Rather than a single "is this realistic?" question, the 3-format evaluation (Timeline, Tactical Triples, RL Boundary Scenarios) forced annotators to engage with specific dimensions of each case. This produced much more actionable feedback than a single holistic score would have.

---

## What Could Be Improved

### 1. Formalize the Feedback Analysis Step

**Problem:** The transition from "read annotator comments and decide what to change" was ad hoc. There were no predefined thresholds for when to trigger a major schema revision vs. minor prompt tuning.

**Recommendation:** Before Round 1, define decision rules:
- If median authenticity < 3: major overhaul required
- If >30% of bottlenecks marked unrealistic: revise Friction Taxonomy
- If average tactical viability < 3: revise Action Taxonomy or situation generation
- If category agreement < 60%: revise boundary definitions

### 2. Track Inter-Annotator Agreement

**Problem:** The database schema supports multiple annotators per case (UNIQUE on case_id + navigator_id), but no analysis pipeline was built to measure agreement. When two experts disagree on whether a bottleneck is realistic, that's a signal the taxonomy is ambiguous -- but this signal was never systematically captured.

**Recommendation:** After each round, compute:
- Cohen's Kappa for categorical fields (bottleneck realism, RL categories)
- Pearson/Spearman correlation for scalar fields (tactical viability, overall authenticity)
- Flag cases with high disagreement for expert debrief sessions

### 3. Version Taxonomies Alongside Batches

**Problem:** Taxonomy files were edited in place. If you look at `friction_taxonomy.json` today, you see the V5 version, but there's no record of what it looked like during V1-V4 generation.

**Recommendation:** Store taxonomies in versioned directories:
```
data/taxonomies/v1/
data/taxonomies/v2/
data/taxonomies/current -> v5/
```

### 4. Version Prompts as Artifacts

**Problem:** The system prompt evolved across git commits but wasn't treated as a first-class artifact. To reconstruct the V3 system prompt, you'd need to `git checkout` the right commit.

**Recommendation:** Store prompts in a `prompts/` directory with version labels:
```
prompts/v1_system_prompt.txt
prompts/v5_system_prompt.txt
prompts/v5_format_rules.txt
```

### 5. Build an Analytics Dashboard

**Problem:** The admin dashboard showed case status and completion, but there was no visualization of score distributions, trends across rounds, or inter-rater statistics.

**Recommendation:** Add a dedicated analytics page that shows:
- Authenticity score histogram per round
- Improvement trend (average score by round)
- Per-format score breakdowns
- Inter-annotator agreement metrics
- Most common improvement suggestions (word cloud or categorized list)

### 6. Seed Case Expansion Loop

**Problem:** The seed pool stayed fixed at 15 cases throughout all 5 rounds. The RAG retrieval was limited by this small corpus, and the LLM saw the same few-shot examples repeatedly.

**Recommendation:** After each round, promote synthetic cases that scored >= 4 on overall authenticity (with expert sign-off) back into the seed pool. This is the true flywheel mechanism.

### 7. Expert Debrief Sessions

**Problem:** Feedback was collected asynchronously through the annotation app. There was no structured session where experts discussed edge cases and disagreements as a group.

**Recommendation:** After each annotation round, schedule a 30-minute group session:
- Show score distributions
- Discuss the lowest-scoring cases
- Ask "What's missing from these cases?"
- Surface expert disagreements and resolve them (update taxonomies accordingly)

### 8. Case Difficulty Calibration

**Problem:** All synthetic cases were generated targeting high complexity (complexity_gte=4 for RAG retrieval). This meant the generated cases skewed complex, which may have biased annotator fatigue.

**Recommendation:** Include a mix of complexity levels in each batch:
- ~20% simple cases (complexity 1-2) -- calibration / baseline
- ~50% medium cases (complexity 3-4)
- ~30% high complexity (complexity 5)

Simple cases serve as controls and give annotators confidence-building wins between harder evaluations.

---

## Process Maturity Model

Where this project landed and where future projects should aim:

| Dimension | This Project (V5) | Target for Next Project |
|---|---|---|
| Intent Discovery | Strong (single deep dive + panel) | Add structured debrief sessions |
| Seed Cases | 15 cases / 4 experts | 20-30 cases + synthetic promotion loop |
| Taxonomies | Evolved but unversioned | Versioned with expert sign-off per round |
| Generation | Mature (RAG + Pydantic + diversity) | Add prompt versioning |
| Annotation Platform | Functional (Streamlit + Supabase) | Add analytics dashboard |
| Feedback Loop | Ad hoc + semi-structured | Formalized with decision thresholds |
| Inter-Annotator Analysis | Schema supports it, not implemented | Automated per-round reports |

---

## Estimated Effort per Phase (for Planning)

These are rough guides, not promises:

| Phase | First Project | Subsequent Projects |
|---|---|---|
| Intent Discovery | 1-2 weeks | 1 week (template exists) |
| Seed Case Design | 1-2 weeks | 3-5 days (instrument reusable) |
| Taxonomy Construction | 1 week | 3-5 days (pattern established) |
| Generation Pipeline | 1-2 weeks | 2-3 days (scripts reusable) |
| Annotation Platform | 1-2 weeks | 1-3 days (app template exists) |
| Per Annotation Round | 1 week (collection + analysis) | Same |
| Total (3 rounds) | 8-12 weeks | 4-6 weeks |
