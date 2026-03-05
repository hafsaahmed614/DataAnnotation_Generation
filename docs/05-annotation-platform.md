# Phase 5: Annotation Platform & Expert Review

## Purpose

The annotation platform is where domain experts evaluate synthetic cases for authenticity. It must be simple enough that busy experts can use it without training, robust enough that their work is never lost, and structured enough that the feedback is quantitatively analyzable.

---

## Platform Requirements

### Must-Have
- **Role-based access** -- Admin (upload/manage cases) vs. Annotator (evaluate cases)
- **Multi-format evaluation** -- Break evaluation into specific, scoreable dimensions rather than a single "is this realistic?" question
- **Auto-save** -- Save on every widget interaction. Experts are busy and will not tolerate lost work
- **Resume capability** -- Experts should be able to start an evaluation, leave, and come back later
- **Overall authenticity score** with free-text reasoning
- **Improvement suggestion field** -- "What one change would make this more realistic?"
- **Unique case-annotator constraint** -- Each expert evaluates each case at most once

### Nice-to-Have
- Progress tracking (cases completed / total)
- Admin analytics dashboard (score distributions, completion rates)
- Export functionality (CSV/JSON of all evaluations)
- Inter-annotator agreement visualization

---

## Evaluation Format Design

The key insight from this project: **don't just ask "is this realistic?"** Break the evaluation into dimensions that map to the output schema:

### Format 1: Timeline / Event Evaluation
For each event in the state log, the annotator evaluates:
- Is the **clinical impact** correct? (Improves / Worsens / Unchanged / Unclear)
- Is the **environmental impact** correct?
- Is the **service adoption impact** correct?
- Is the **delay estimate (EDD delta)** reasonable?
- Is the **bottleneck** realistic? (True / False)

This produces **per-event** evaluation data, not just per-case.

### Format 2: Action / Decision Evaluation
For each reasoning triple (situation -> action -> intent), the annotator scores:
- **Tactical viability** (1-5 scale): Would this action work in the real world?

### Format 3: Boundary Evaluation
For each RL scenario option, the annotator categorizes:
- Is this action **Passive**, **Proactive**, or **Overstep**?
- Compare against the AI's intended category to measure alignment

### Final Assessment
- **Overall field authenticity** (1-5 scale)
- **Reasoning** (free text): Why did you give this score?
- **Improvement suggestion** (free text): What would make this more realistic?

---

## Database Schema Design

### Versioning Strategy

**Critical lesson from this project:** Version your schema tables. When the output schema evolves (and it will), you don't want to lose prior evaluation data.

```
synthetic_cases       -- V1 cases + evaluations
synthetic_cases_v3    -- V2/V3 cases + evaluations
synthetic_cases_v4    -- V4 cases + evaluations
synthetic_cases_v5    -- V5 cases + evaluations (current)
```

Each version includes:
- `synthetic_cases_vN` -- The cases themselves (narrative + JSONB format fields)
- `evaluation_sessions_vN` -- One row per (case, annotator) pair
- `eval_format_1_timeline_vN` -- Per-event evaluations
- `eval_format_2_tactics_vN` -- Per-triple evaluations
- `eval_format_3_boundaries_vN` -- Per-option evaluations

### Row-Level Security

If using Supabase or similar:
- Admins get full access to all tables
- Annotators can read cases (SELECT) but can only manage their own evaluation sessions
- Use a service client for save operations to bypass RLS when needed (the auto-save pattern requires this)

---

## Technology Choices

This project used:
- **Streamlit** -- For rapid prototyping of the annotation UI
- **Supabase (PostgreSQL)** -- For case storage and evaluation data, with built-in auth and RLS
- **Python** -- For the upload and generation scripts

**Streamlit Pros:**
- Fastest path from zero to working annotation app
- Built-in widgets (sliders, selectboxes, radio buttons, text areas) map perfectly to evaluation forms
- Deployable to Streamlit Cloud for easy expert access

**Streamlit Cons:**
- Re-runs the entire page on every interaction (hence the auto-save pattern)
- Limited layout control
- Not ideal for large annotator teams (>10 concurrent users)

**Alternatives for larger projects:**
- **Gradio** -- Similar rapid prototyping with more layout options
- **Label Studio** -- Purpose-built annotation platform with team features
- **Custom web app** (Next.js/React + Supabase) -- Full control, but longer development time

---

## Upload Pipeline

After generating synthetic cases, upload them to the annotation database:

```python
# upload_cases.py pattern
for case_file in sorted(glob("data/synthetic_batch_25/case_*.json")):
    data = json.load(open(case_file))
    row = {
        "batch_id": "batch_v5",
        "label": f"Case {i+1:02d}",
        "narrative_summary": data["narrative_summary"],
        "format_1_state_log": data["format_1_state_log"],
        "format_2_triples": data["format_2_triples"],
        "format_3_rl_scenario": data["format_3_rl_scenario"],
        # V5 checklist fields...
    }
    supabase.table("synthetic_cases_v5").insert(row).execute()
```

---

## Common Pitfalls

1. **No auto-save** -- If an expert spends 20 minutes evaluating a case and loses their work, they won't come back.
2. **Too many fields per case** -- If evaluation takes >15 minutes per case, fatigue degrades quality. Aim for 5-10 minutes.
3. **No free-text fields** -- Quantitative scores tell you "what" but not "why." The improvement suggestion field was the single most valuable feedback source in this project.
4. **Shared tables across schema versions** -- Adding columns to an existing table risks breaking saved evaluations. Version your tables.
5. **No unique constraint on (case, annotator)** -- Without this, experts can accidentally submit duplicate evaluations.

---

## Deliverables

- [ ] Annotation app with role-based access
- [ ] Multi-format evaluation forms matching the output schema
- [ ] Database schema with versioned tables and RLS policies
- [ ] Upload script for synthetic cases
- [ ] Expert onboarding instructions
