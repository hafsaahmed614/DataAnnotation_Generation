# Phase 3: Constraint System Design

## Purpose

Constraint systems are what prevent the LLM from hallucinating domain-inaccurate details. Rather than prescribing a single approach, this phase involves **mining your seed cases** to determine which combination of three techniques best fits your intent and data:

1. **Taxonomies** -- Categorical, enumerable constraints
2. **RAG (Retrieval-Augmented Generation)** -- Semantic retrieval of relevant examples
3. **Knowledge Graphs / Triples** -- Structured entity-relationship reasoning chains

These are not mutually exclusive. Most projects benefit from combining two or all three. The seed cases tell you which to prioritize.

---

## Mining Seed Cases for Constraint Signals

Before building anything, analyze your seed cases systematically. For each seed case, ask:

### Signal 1: Categorical Patterns --> Taxonomies

Look for fields where values repeat across cases and could be enumerated:
- Do cases share common **barrier/friction types** that you could list exhaustively?
- Are there discrete **action categories** that experts choose from?
- Are there a finite number of **outcome states**?
- Do any fields have implicit "valid values" that experts wouldn't violate?

**If yes:** Build a taxonomy for that dimension.

### Signal 2: Narrative Richness --> RAG

Look for variation in narrative depth and style:
- Do some seed cases have significantly more detail than others?
- Does the "feel" of a case (tone, clinical specificity, operational chaos) matter as much as the structure?
- Would showing the LLM 2-3 similar cases help it match the right level of complexity?

**If yes:** Vectorize seed cases and use RAG retrieval to inject relevant few-shot examples.

### Signal 3: Causal Chains & Entity Relationships --> Knowledge Graph / Triples

Look for structured reasoning patterns:
- Do cases contain **situation -> action -> intent -> result** chains?
- Are there **stakeholder relationships** (who reports to whom, who can authorize what)?
- Are there **state transitions** (subject moves from state A to state B when trigger X occurs)?
- Are there **dependency chains** (action B can't happen until action A completes)?

**If yes:** Extract entity-relationship triples and use them as reasoning templates.

---

## Technique 1: Taxonomies

### When to Use

Taxonomies work best when the domain has categorical knowledge that can be enumerated. They answer: "What are the valid values for this field?"

### Structure

Each taxonomy entry should contain:

```json
{
  "category": "Top-level grouping",
  "signal_name": "Specific item name",
  "expected_impact": "Quantified consequence",
  "logical_dna_rule": "WHY this item exists -- the causal mechanism"
}
```

The **logical DNA rule** is the most important field. It tells the LLM *why* this barrier causes a specific delay (or *why* this action achieves a specific goal), not just that it does. Without it, the LLM applies values arbitrarily.

### Common Taxonomy Types

| Taxonomy | What It Enumerates | Example Entry |
|---|---|---|
| **Friction / Barrier** | What goes wrong | `"Medicaid CHC Waiver" -> +30-45 Days because 3 contractor estimates required` |
| **Action** | What the expert can do (by stage) | `"Eligibility Verification" -> Confirm insurance type before introducing services` |
| **Outcome** | Possible end states | `"Service Conversion" -> Triggered by first visit within 24-48hrs of discharge` |

### Design Principles

1. **MECE** (Mutually Exclusive, Collectively Exhaustive) -- Each entry should be distinct; together they cover the full space
2. **Logical DNA rules over labels** -- A label like "Bureaucratic Delay" means nothing without the mechanism
3. **Stage-aligned actions** -- Organize actions by workflow stage so the LLM generates actions in the right order
4. **Evolved, not designed** -- The initial taxonomy is a hypothesis. Expect to add 3-5 entries after each annotation round.

---

## Technique 2: RAG (Retrieval-Augmented Generation)

### When to Use

RAG works best when you need the LLM to match the **tone, depth, and narrative richness** of real cases. It answers: "What does a good case look like for this type of scenario?"

### Architecture

```
Seed Cases --> Vectorize --> ChromaDB (or similar)
                                |
Target Scenario --> Query ------+
                                |
                         2-3 Similar Cases
                                |
                         Inject as Few-Shot
```

### What to Embed (the document string)

Concatenate the narrative/logical elements into a single searchable string:
- Barriers (clinical + environmental)
- Reasoning trace summaries (situation + intent)
- Chaos signals / unexpected events

### What to Store as Metadata (for filtering)

ChromaDB metadata only accepts strings, ints, or floats:
- `complexity_score`: int (for filtering by minimum complexity)
- `outcome`: str (for filtering by outcome type)
- Domain-specific qualifiers (e.g., `has_skilled_need`, `primary_friction`)
- `raw_json`: The full serialized seed case (for injection into the prompt)

### Retrieval Strategy

```python
results = collection.query(
    query_texts=["Bureaucratic delay with {target_friction}"],
    n_results=2,
    where={"complexity_score": {"$gte": 4}},
)
```

Use **semantic search** (query text) combined with **metadata filters** (complexity, outcome type) to retrieve the most relevant seed cases for the target scenario.

### Design Principles

1. **Embed the reasoning, not the demographics** -- Demographics are filterable metadata; reasoning traces carry the narrative signal
2. **Retrieve 2-3 examples, not all** -- More than 3 wastes context window; fewer risks insufficient grounding
3. **Filter by complexity** -- Retrieve the most detailed seed cases (complexity >= 4) to set a high bar for the LLM
4. **Seed pool expansion** -- Promote high-scoring synthetic cases back into the seed pool after expert review (the true flywheel mechanism)

---

## Technique 3: Knowledge Graph / Triples

### When to Use

Knowledge graphs work best when the domain has **complex causal reasoning**, **multi-stakeholder relationships**, or **state transitions** that the LLM needs to respect. They answer: "What is the logical structure of expert reasoning?"

### Triple Structures

**Reasoning Trace Triples** (Situation -> Action -> Intent -> Result):
```json
{
  "situation": "What the expert observed",
  "action_taken": "What the expert did",
  "intent": "Why they did it (maps to Action Taxonomy category)",
  "result": "What happened as a consequence"
}
```

This is the most common triple type. It captures the expert's decision-making chain in a format that the LLM can replicate with new situations.

**Entity-Relationship Triples** (Entity -> Relationship -> Entity):
```json
{
  "entity_a": "Patient Navigator",
  "relationship": "escalates_to",
  "entity_b": "Social Worker",
  "constraint": "Only when the issue involves agency selection or placement decisions"
}
```

These encode the stakeholder network and role boundaries. They prevent the LLM from generating actions where the wrong entity does the wrong thing.

**State Transition Triples** (State -> Trigger -> State):
```json
{
  "from_state": "Clinically Ready",
  "trigger": "Home modification completed",
  "to_state": "Service Conversion",
  "blocker": "Waiver approval delayed"
}
```

These encode the possible case trajectories and what causes transitions between states. Combined with the Outcome Taxonomy, they ensure the LLM generates logically consistent case arcs.

### Extracting Triples from Seed Cases

Mine your seed cases for triple patterns:

1. **Reasoning traces** -- Look for `reasoning_trace_triples` or similar fields where experts documented situation/action/intent/result chains
2. **Stakeholder interactions** -- Look for mentions of handoffs, escalations, or boundary-crossing between roles
3. **Timeline events** -- Look for `timeline_deltas` or state changes that show cause-and-effect relationships
4. **Judgment policies** -- Look for `rank_1_best_practices` and `rank_0_boundary_failures` that encode what-to-do and what-not-to-do

### Design Principles

1. **Triples enforce logical consistency** -- The LLM can generate a realistic narrative but violate causal logic. Triples prevent this.
2. **Intent categories should be enumerable** -- If reasoning triples have an `intent` field, define the valid intents (e.g., Educate, Escalate, Verify). This bridges triples to taxonomies.
3. **Use triples for RL-style evaluation** -- Reasoning triples naturally map to "was this the right action?" evaluation formats. The annotator scores whether the situation/action/intent chain is tactically viable.
4. **Triples evolve from free-text to categorical** -- In early rounds, intents may be free-text. By Round 3-4, you should have enough data to enumerate intent categories.

---

## Choosing Your Combination

| Seed Case Signal | Primary Technique | Supporting Technique(s) |
|---|---|---|
| Mostly categorical fields with clear valid values | Taxonomy | RAG for narrative grounding |
| Rich narratives with variable depth/complexity | RAG | Taxonomy for value constraints |
| Complex causal chains or multi-stakeholder workflows | Knowledge Graph / Triples | Taxonomy for categories, RAG for detail |
| All of the above (complex expert domains) | All three | -- |

### Healthcare Project Example

This project used **all three techniques**:

| Technique | How It Was Used |
|---|---|
| **Taxonomies** | Friction Taxonomy (6 -> 22 entries), Action Taxonomy (3 stages, 12 categories), Outcome Taxonomy (5 states). Injected as structured JSON context. |
| **RAG** | 15 seed cases vectorized in ChromaDB. 2 cases retrieved per generation run, filtered by complexity >= 4. |
| **Knowledge Graph / Triples** | `reasoning_trace_triples` (situation/action/intent/result) in every seed case. `judgment_policy` with rank_1 (best practices) and rank_0 (boundary failures). State transition logic encoded in `timeline_deltas`. |

The combination was critical:
- Taxonomies alone would have produced valid-but-flat cases
- RAG alone would have produced rich-but-unconstrained cases
- Triples alone would have produced logically-consistent-but-formulaic cases
- Together, they produced cases that were valid, rich, AND logically sound

---

## Versioning Strategy

All constraint artifacts should be versioned alongside generation batches:

```
data/
  constraints/
    v1/
      friction_taxonomy.json
      action_taxonomy.json
      outcome_taxonomy.json
      triple_schema.json
      rag_config.json          # retrieval parameters
    v2/
      ...
    current -> v5/
```

---

## Common Pitfalls

1. **Prescribing one technique before analyzing seed data** -- Don't assume you need taxonomies. Let the seed cases tell you what they need.
2. **No logical DNA rules** -- Whether in a taxonomy entry or a triple, the "why" is what makes the constraint useful.
3. **Treating techniques as mutually exclusive** -- The power is in combination. A taxonomy constrains valid values; RAG grounds narrative depth; triples enforce causal logic.
4. **Not evolving constraints** -- If Round 1 annotators say "this barrier doesn't exist" or "you're missing X," update all affected constraint artifacts before Round 2.
5. **Unversioned constraints** -- If you can't reconstruct the exact constraints used for a given batch, you can't reproduce or compare results across rounds.

---

## Deliverables

- [ ] Seed case analysis document: which constraint techniques are needed and why
- [ ] Taxonomy JSON files with logical DNA rules (if applicable)
- [ ] RAG vector store with ingestion script (if applicable)
- [ ] Knowledge graph triple schema and extracted triples (if applicable)
- [ ] Expert review sign-off on V1 constraint artifacts
- [ ] Version control strategy for constraint evolution
