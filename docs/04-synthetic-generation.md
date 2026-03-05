# Phase 4: Synthetic Case Generation

## Purpose

Generate synthetic cases that are realistic enough for domain experts to evaluate as "authentic." The generation pipeline adapts based on which constraint systems were selected in Phase 3 -- taxonomies, RAG, knowledge graph/triples, or any combination of the three.

---

## Architecture

The generation pipeline has a modular design. Each constraint technique is an independent layer that can be activated or deactivated:

```
+------------------+    +------------------+    +------------------+
|   Taxonomies     |    |   RAG / Vector   |    | Knowledge Graph  |
|   (JSON files)   |    |   (ChromaDB)     |    | (Triple schemas) |
+--------+---------+    +--------+---------+    +--------+---------+
         |                       |                       |
         v                       v                       v
    Category             Few-Shot Examples        Reasoning Templates
    Constraints          (2-3 similar cases)      (Triple structures)
         |                       |                       |
         +-----------+-----------+-----------+-----------+
                     |
                     v
            +--------+---------+
            | Prompt Assembly  |
            | (System + User)  |
            +--------+---------+
                     |
                     v
            +--------+---------+
            | LLM Generation   |
            +--------+---------+
                     |
                     v
            +--------+---------+
            | Pydantic         |
            | Validation       |
            +--------+---------+
                     |
                     v
            +--------+---------+
            | JSON Output      |
            +--------+---------+
```

---

## Prompt Design

The prompt is assembled from modular layers. Not all layers are required -- use only the ones that match your active constraint systems.

### Layer 1: System Prompt (Role + Constraints) -- Always Required

Defines who the LLM is pretending to be, the workflow it must follow, and hard constraints.

**Template:**
```
You are a [ROLE] operating in [CONTEXT].
Your goal is to [PRIMARY OBJECTIVE].

=== WORKFLOW STAGES ===
[Stage descriptions -- from Action Taxonomy if available, or from interview notes]

=== ROLE BOUNDARIES ===
[What this role CANNOT do]

=== BANNED ACTIONS ===
[Specific actions that violate role boundaries]

FOG OF WAR: The [ROLE] always acts on INCOMPLETE information.
At least one critical detail must be unknown, delayed, or contradictory.

BANNED TROPES: [Patterns from prior rounds that were unrealistic]
```

The **Fog of War** directive prevents the LLM from generating "perfect information" cases. The **Banned Tropes** list grows with each annotation round.

### Layer 2: Taxonomy Injection -- When Taxonomies Are Active

```
=== STATIC TAXONOMIES ===

--- Friction Taxonomy (defines allowable delays) ---
[friction_taxonomy.json content]

--- Action Taxonomy (defines expert actions by stage) ---
[action_taxonomy.json content]

--- Outcome Taxonomy (defines state transition triggers) ---
[outcome_taxonomy.json content]
```

The LLM is instructed to select values **only** from the taxonomy. This prevents hallucinated domain-specific details.

### Layer 3: RAG-Retrieved Examples -- When RAG Is Active

```
=== FEW-SHOT REFERENCE CASES ===
Here are 2 real-world seed cases. Mimic their level of detail,
operational complexity, and formatting exactly:
[Retrieved seed case JSONs]
```

The retrieval query is constructed from the target scenario:
```python
query_text = f"Bureaucratic delay with {target_friction} and clinical barriers"
examples = retrieve_few_shot_examples(collection, complexity_gte=4, query_text=query_text, n=2)
```

### Layer 4: Knowledge Graph / Triple Templates -- When Triples Are Active

```
=== REASONING STRUCTURE ===
Each case must contain reasoning triples following this pattern:

Situation -> Action -> Intent -> Result

Valid intent categories: [Educate, Escalate, Verify]

The action_taken must be performed by the [ROLE], NOT by [OTHER_ROLE].
The intent must map to one of the valid categories above.

=== ENTITY RELATIONSHIPS ===
[ROLE] escalates_to [OTHER_ROLE] when [CONDITION]
[ROLE] never [BANNED_ACTION]
[STATE_A] transitions_to [STATE_B] when [TRIGGER]
```

This layer tells the LLM the **structure** of expert reasoning, not just the content. It ensures generated triples follow valid causal chains and respect entity relationships.

### Layer 5: Task Instruction + Output Schema -- Always Required

```
=== TASK ===
Generate 1 NEW synthetic case with:
- Subject: [target profile]
- Main Friction: [selected friction]

Output ONLY valid JSON conforming to this schema:
[Pydantic model JSON schema]

=== FORMAT RULES ===
[Numbered rules for each output format]
```

---

## How the Pipeline Adapts by Technique

| Active Techniques | Prompt Contains | Strengths | Watch For |
|---|---|---|---|
| **Taxonomy only** | Category constraints + output schema | Fast, consistent valid values | Cases may feel flat or generic |
| **RAG only** | Few-shot examples + output schema | Rich, varied narratives | May violate domain rules the LLM wasn't told about |
| **Triples only** | Reasoning templates + entity relationships | Logically consistent chains | May feel formulaic or mechanical |
| **Taxonomy + RAG** | Categories + few-shot examples | Valid AND rich | Triples may lack causal consistency |
| **Taxonomy + Triples** | Categories + reasoning structure | Valid AND logically sound | Narratives may lack depth |
| **RAG + Triples** | Examples + reasoning structure | Rich AND logically sound | May generate values outside valid categories |
| **All three** | Full constraint stack | Valid, rich, AND logically sound | Prompt length -- may need to prioritize |

### Managing Prompt Length

When using all three techniques, the prompt can get long. Prioritize:
1. System prompt constraints (always include)
2. Output schema (always include)
3. Taxonomy entries (compact -- enumerate valid values)
4. Triple templates (compact -- show the structure, not exhaustive examples)
5. RAG examples (largest -- limit to 2 examples, or summarize to key fields)

---

## Diversity Enforcement

To prevent the LLM from generating N copies of the same case:

1. **Subject randomization** -- Maintain a list of diverse profiles and randomly assign them to generation runs.
2. **Friction/scenario randomization** -- Randomly select friction types, ensuring coverage across the taxonomy.
3. **Category quotas** -- Reserve a percentage of cases for specific categories (e.g., ~30% patient/family-driven frictions).
4. **Unique combo enforcement** -- Build all (subject, friction) pairs, shuffle, and select N unique combinations.

```python
def _build_unique_combos(subjects, frictions, n=25,
                          priority_frictions=None, priority_slots=8):
    import itertools, random
    priority_set = set(priority_frictions or [])
    pc_combos = list(itertools.product(subjects, [f for f in frictions if f in priority_set]))
    other_combos = list(itertools.product(subjects, [f for f in frictions if f not in priority_set]))
    random.shuffle(pc_combos)
    random.shuffle(other_combos)
    combined = pc_combos[:priority_slots] + other_combos[:n - priority_slots]
    random.shuffle(combined)
    return combined[:n]
```

---

## Validation

Every generated case must pass Pydantic validation before being saved. The schema should enforce:
- Required fields present
- Correct data types
- Valid enum values (e.g., outcome must be one of the allowed states)
- Structural constraints (e.g., RL scenario must have exactly 3 options: one Passive, one Proactive, one Overstep)
- Triple structure (e.g., intent_category must be one of the valid categories)

**Retry strategy:** If validation fails, retry up to 3 times. If the error is a rate limit (429), wait with exponential backoff.

---

## Configuration

| Parameter | Recommended | Why |
|---|---|---|
| Temperature | 0.7-0.9 | High enough for creative variation, low enough for coherence |
| Response format | JSON mode | Prevents markdown fences, commentary, etc. |
| Few-shot examples | 2-3 (if RAG active) | More than 3 wastes context window |
| Batch size | 20-30 per round | Enough for statistical analysis of annotation scores |
| Complexity filter | >= 4 (of 5) for RAG | Retrieve the most detailed seed cases |

---

## Healthcare Project Example

This project used **all three constraint techniques**:

**Taxonomies:** Friction (22 entries), Action (3 stages, 12 categories), Outcome (5 states) -- injected as JSON context.

**RAG:** 15 seed cases in ChromaDB. 2 retrieved per run via semantic search + complexity filter.

**Knowledge Graph / Triples:**
- `reasoning_trace_triples` with intent categories (Educate / Escalate / Verify)
- `judgment_policy` with rank_1 (best practices) and rank_0 (boundary failures)
- `timeline_deltas` encoding state transitions with causal context
- Entity relationships encoded in the system prompt (PN escalates_to SW; PN never suggests HHAs)

**Generation Evolution:**
- **V1:** Taxonomy + RAG only. Cases were valid but actions felt generic.
- **V3:** Added intent categories to triples (Educate/Escalate/Verify). Actions improved.
- **V4:** Added entity-relationship constraints (SW Boundary, Banned Actions). Boundary scenarios became more nuanced.
- **V5:** Full 3-technique stack with 3-Stage Lifecycle Checklist, LTC Filter, and state transition outcomes. Highest authenticity scores achieved.

Key prompt evolution moments:
- Adding "Fog of War" (system prompt) eliminated perfect-information cases
- Adding "Banned Tropes" (system prompt) eliminated overused patterns
- Adding intent categories (triple constraint) made reasoning chains evaluable
- Adding entity relationships (triple constraint) made overstep scenarios tempting and subtle

---

## Common Pitfalls

1. **No structured output enforcement** -- Without Pydantic validation, the LLM returns inconsistent schemas across runs.
2. **System prompt too long** -- If it exceeds ~2000 tokens, the LLM starts ignoring rules at the end. Prioritize by importance.
3. **Not banning tropes** -- The LLM will overuse dramatic patterns. Explicitly ban anything annotators flag as unrealistic.
4. **Same seed cases every time** -- Without RAG filtering, the LLM sees the same examples. Filter by complexity and use semantic search.
5. **Using only one technique when multiple are warranted** -- Taxonomy-only produces flat cases; RAG-only produces unconstrained cases; triples-only produces formulaic cases. Combine as needed.
6. **No backups** -- Always archive each batch before generating the next.
7. **Forgetting to version prompts** -- The system prompt is a first-class artifact. Store it in `prompts/vN_system_prompt.txt`.

---

## Deliverables

- [ ] System prompt (versioned in `prompts/` directory)
- [ ] Pydantic output schema
- [ ] Generation script with modular constraint injection (taxonomy, RAG, triples)
- [ ] Batch generation script with diversity enforcement
- [ ] First batch of 20-30 validated synthetic cases
- [ ] Backup of each generation batch
