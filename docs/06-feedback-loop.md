# Phase 6: Feedback Loop & Iteration

## Purpose

The feedback loop is what makes this a flywheel rather than a one-shot process. Each annotation round produces quantitative scores and qualitative insights that directly improve the next generation round.

---

## The Iteration Cycle

```
Round N Annotations
        |
        v
Quantitative Analysis -----> Score distributions, per-format breakdowns
        |
        v
Qualitative Analysis ------> Free-text themes, expert disagreements
        |
        v
Action Items:
  - Update constraint systems (taxonomies, triple schemas, RAG config)
  - Evolve output schema (add/remove fields)
  - Refine prompts (add banned tropes, adjust constraints)
  - Expand seed cases (promote high-scoring synthetics)
        |
        v
Round N+1 Generation
```

---

## Quantitative Analysis

### Metrics to Track

1. **Overall authenticity score distribution** -- Histogram across all cases. Target: median >= 4 by Round 3-4.
2. **Per-format score breakdown:**
   - Format 1: % of events where bottleneck was marked "realistic" (target: >80%)
   - Format 2: Average tactical viability score (target: >= 3.5)
   - Format 3: % agreement between AI-intended category and annotator category (target: >70%)
3. **Per-case outliers** -- Which cases scored lowest? What do they have in common?
4. **Inter-annotator agreement** -- When multiple experts evaluate the same case, do they agree? Disagreement signals taxonomy ambiguity.
5. **Improvement trend** -- Are average scores increasing across rounds?

### Suggested Thresholds for Action

| Signal | Action |
|---|---|
| Median authenticity < 3 | Major schema/prompt overhaul needed |
| Median authenticity 3-4 | Targeted prompt refinements + taxonomy updates |
| Median authenticity >= 4 | Minor tuning; consider expanding to new friction types |
| >30% of events marked "unrealistic bottleneck" | Friction taxonomy needs revision |
| Average tactical viability < 3 | Action taxonomy or situation generation needs work |
| <60% category agreement on RL scenarios | Boundary definitions need clarification |

---

## Qualitative Analysis

### Reading Free-Text Feedback

The **improvement suggestion** field is the most actionable feedback source. Categorize suggestions into themes:

1. **Missing context** -- "This case doesn't mention X" -> Add X to the output schema
2. **Unrealistic pattern** -- "This would never happen because Y" -> Add to Banned Tropes
3. **Missing friction type** -- "We actually deal with Z a lot" -> Add to Friction Taxonomy
4. **Role boundary confusion** -- "A PN wouldn't do this" -> Clarify in Banned Actions list
5. **Schema mismatch** -- "This field doesn't capture what I'd actually document" -> Evolve schema

### Expert Debrief Sessions (Recommended)

After each round, schedule a 30-minute group session with annotators:
- Show them the score distribution
- Ask about cases they found most/least realistic
- Discuss disagreements between annotators
- Ask: "What's missing from these cases that you deal with every week?"

This was NOT done systematically in the original project and is a recommended addition.

---

## Schema Evolution Examples

This project's schema evolved across 5 major versions:

### V1 -> V2: Taxonomy Expansion
- **Trigger:** Cases felt repetitive; same 6 frictions recycled
- **Change:** Expanded friction list from 6 to 16 entries
- **Result:** More diverse cases, but actions still felt generic

### V2 -> V3: Diversity Enforcement
- **Trigger:** All cases had similar patient profiles
- **Change:** Added randomized patient list and unique combo enforcement
- **Result:** Better demographic diversity, but boundary scenarios were too obvious

### V3 -> V4: Mentality Overhaul ("Support, Suggest, Escalate")
- **Trigger:** Annotators said "the PN actions don't feel like how we think"
- **Change:** Restructured Format 2 intents from free-text to categorical (Educate/Escalate/Verify). Added boundary_planning_scratchpad.
- **Result:** Actions felt more grounded in real PN thinking

### V4 -> V5: 3-Stage Lifecycle Checklist
- **Trigger:** Cases were narratively rich but didn't follow the actual PN workflow stages
- **Change:** Added 8 new fields mapping to the 3-stage lifecycle (Atlantis Entry, Maintenance, Handoff). Added LTC Filter. Added case_outcome enum.
- **Result:** Highest authenticity scores; cases matched the actual software workflow

---

## Taxonomy Evolution Process

1. After each round, review all "improvement suggestion" responses
2. Group suggestions by theme
3. For each new friction/action identified, write the taxonomy entry with a logical DNA rule
4. For each "this never happens" comment, either remove the entry or add it to Banned Tropes
5. Have at least one expert review the updated taxonomy before the next round
6. Archive the old taxonomy version before overwriting

---

## Seed Case Expansion (The True Flywheel)

The most powerful flywheel mechanism (not yet implemented in this project):

1. After annotation, identify synthetic cases that scored >= 4 on overall authenticity
2. Have an expert review and optionally edit these cases
3. Promote the expert-validated synthetic cases into the seed case pool
4. Re-vectorize the expanded seed pool
5. Generate the next batch with richer few-shot examples

This creates a compounding effect: better seed cases -> better synthetic cases -> better-scoring cases -> more seed cases.

---

## Common Pitfalls

1. **Skipping the analysis** -- Generating the next batch without systematically reviewing scores and feedback wastes the annotation investment.
2. **Changing too much at once** -- If you change the schema, taxonomies, AND prompts simultaneously, you can't attribute improvement to any specific change. Change one major thing per round.
3. **Not versioning backups** -- Always archive the previous batch before generating a new one. This project correctly maintained `v1_backup` through `v4_backup`.
4. **Ignoring inter-annotator disagreement** -- If two experts disagree on whether a bottleneck is realistic, the taxonomy may be ambiguous. Investigate rather than averaging the scores.
5. **Stopping too early** -- The flywheel takes 3-5 rounds to produce consistently high-authenticity data. Don't declare victory after Round 1.

---

## Deliverables

- [ ] Score analysis report per round (distributions, outliers, trends)
- [ ] Free-text feedback categorization
- [ ] Updated taxonomy files (versioned)
- [ ] Updated prompts with new banned tropes and constraints
- [ ] Archived backups of each generation batch
- [ ] (Optional) Expert debrief session notes
