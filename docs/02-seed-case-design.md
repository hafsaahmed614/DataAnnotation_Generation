# Phase 2: Seed Case Design

## Purpose

Seed cases are the DNA of your synthetic data. They are real-world cases submitted by domain experts, structured into a consistent JSON format, and vectorized for RAG retrieval. The quality of your synthetic data is bounded by the quality of your seed cases.

---

## Process

### Step 1: Design the Submission Instrument

Build a simple app or form where experts submit historical cases. The instrument should be structured enough to produce consistent JSON but open enough to capture the richness of real-world experience.

**Recommended 3-Section Structure:**

**Section 1: Demographics / Context**
- Subject profile (age, relevant characteristics, setting)
- Complexity score (self-assessed by the expert, 1-5 scale)
- Outcome (what ultimately happened)

**Section 2: The Case Narrative**
- What was the core challenge?
- What barriers arose? (clinical, environmental, administrative, etc.)
- What was the timeline? Where did delays happen and why?
- What decisions did the expert make? (situation -> action -> intent -> result)
- What unexpected events occurred? ("chaos signals")

**Section 3: Outcomes & Judgment**
- What were the best practices demonstrated? (Rank 1 actions)
- What were the mistakes or missed opportunities? (Rank 0 actions)
- What was the final outcome?

### Step 2: Collect Seed Cases

**Targets:**
- **10-20 cases** across 3-5 experts
- **Range of complexity** -- don't just collect hard cases. Simple cases establish the baseline.
- **Range of outcomes** -- include successes, failures, and neutral outcomes
- **Diverse experts** -- different regions, experience levels, and specializations

**Tips for Collection:**
- Schedule dedicated time with each expert (30-45 min per case)
- Let experts choose cases they remember vividly -- vivid memory correlates with rich detail
- Ask follow-up questions when answers are vague: "What specifically did you do when X happened?"
- Record the expert's name/ID with each case for provenance tracking

### Step 3: Transform into Structured JSON

Convert submissions into a consistent JSON schema. Key design decisions:

```json
{
  "case_header": {
    "case_id": "Case_1",
    "expert_id": "Expert_A",
    "complexity_score": 4,
    "demographics": { ... },
    "outcome": "Success / Failure / Neutral"
  },
  "domain_logic": {
    "readiness_criteria": "...",
    "barriers": ["..."],
    "qualified": true
  },
  "environmental_logic": {
    "external_barriers": "...",
    "bureaucratic_steps": ["..."]
  },
  "timeline_deltas": [
    {
      "trigger_event": "...",
      "days_added": 30,
      "context": "Why this delay happened"
    }
  ],
  "reasoning_trace_triples": [
    {
      "situation": "What the expert observed",
      "action_taken": "What the expert did",
      "intent": "Why they did it",
      "result": "What happened"
    }
  ],
  "judgment_policy": {
    "best_practices": [ ... ],
    "boundary_failures": [ ... ]
  },
  "chaos_signals": ["Unexpected events that made this case unique"]
}
```

**Key Fields:**
- **Reasoning trace triples** (situation/action/intent/result) are the most valuable data. They capture expert decision-making in a format that directly maps to training data.
- **Chaos signals** prevent the LLM from generating "textbook" cases. Real cases always have something unexpected.
- **Timeline deltas** with context explain *why* delays happened, not just that they did.

### Step 4: Mine Seed Cases for Constraint Signals

Before moving to Phase 3, analyze the completed seed cases to determine which constraint techniques are appropriate:

**Look for categorical patterns (-> Taxonomies):**
- Do barrier types repeat across cases? Can you enumerate them?
- Are there discrete action categories or outcome states?

**Look for narrative richness variation (-> RAG):**
- Do some cases have significantly more detail than others?
- Would showing the LLM similar cases help it match the right level of depth?

**Look for causal chains (-> Knowledge Graph / Triples):**
- Do cases contain situation -> action -> intent -> result chains?
- Are there stakeholder relationships or state transitions?

This analysis directly informs which constraint systems you build in Phase 3. See [`03-constraint-system-design.md`](./03-constraint-system-design.md) for details on each technique.

---

## Healthcare Project Example

This project collected **15 seed cases** from **4 Patient Navigators**:
- Lyndsey: 7 cases (complexity 2-5, diverse outcomes)
- Kristin: 3 cases (complexity 4-5, complex scenarios)
- Melissa: 3 cases (complexity 2-3, smooth transitions)
- Mark: 2 cases (complexity 4, failure scenarios)

The submission app asked ~12 questions in 3 sections covering patient demographics, the case narrative, and services discussed.

The JSON schema included specialized healthcare fields: `clinical_logic`, `environmental_logic`, `timeline_deltas`, `reasoning_trace_triples`, `judgment_policy`, and `unscripted_chaos_signals`.

---

## Common Pitfalls

1. **Shallow seed cases** -- If experts give one-line answers, your synthetic cases will be one-dimensional. Push for specifics.
2. **All high-complexity cases** -- You need simple cases too. The LLM needs to understand the range.
3. **No failure cases** -- If every seed case is a success story, the LLM won't know how to generate realistic failures.
4. **Missing "why" in timeline deltas** -- "+30 days" without context is useless. The LLM needs the logic behind the delay.
5. **Not analyzing for constraint signals** -- Seed cases contain patterns that tell you which constraint techniques to use. Skipping this analysis means you'll default to one approach when a combination would be stronger.

---

## Deliverables

- [ ] Case submission instrument (app/form)
- [ ] 10-20 structured seed case JSON files
- [ ] Seed case analysis: identified constraint signals (categorical patterns, narrative depth, causal chains)
- [ ] Decision on which constraint techniques to build in Phase 3
