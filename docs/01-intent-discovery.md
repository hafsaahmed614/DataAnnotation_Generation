# Phase 1: Intent Discovery

## Purpose

Intent discovery is the foundation of every data annotation project. Before designing schemas, taxonomies, or generation prompts, you need to understand what experts actually do, how they think, and what makes their work hard.

The "intent" of a project will evolve over time. The first round of interviews reveals the obvious intents; subsequent annotation rounds and expert feedback surface the hidden ones.

---

## Process

### Step 1: Single-Expert Deep Dive

Start with one domain expert who has extensive experience (ideally 10+ years). This is not a data collection session -- it's a discovery session.

**Interview Structure:**
1. **Workflow mapping** (30 min) -- Walk through a typical day. What tools do they use? Who do they interact with? What are their daily tasks?
2. **Decision inventory** (30 min) -- What decisions do they make? What information do they need for each decision? What happens when information is missing?
3. **Complexity spectrum** (20 min) -- What makes a case easy vs. hard? What are the factors that increase complexity?
4. **Failure modes** (20 min) -- What goes wrong? What are the common pitfalls? What does a bad outcome look like?
5. **Stakeholder map** (10 min) -- Who are the other players? What are the boundaries between roles?

**Output:** A raw workflow document that you can reference when designing everything else.

### Step 2: Panel Expansion

Expand to 3-5 experts. The goal is to surface **disagreements and edge cases** that a single expert can't reveal.

**Key Questions for Panel Interviews:**
- "When would you do X differently than what [Expert 1] described?"
- "What's a case where the standard process completely broke down?"
- "What's the hardest case you've ever handled, and why?"
- "What do new people in your role get wrong most often?"

**What to Listen For:**
- Different mental models for the same decision
- Regional or organizational variations in process
- Unstated assumptions that experts take for granted
- The difference between what the manual says and what actually happens

### Step 3: Intent Extraction

From the interviews, extract a list of **intents** -- the discrete decisions or actions that experts take.

**Format for Each Intent:**
```
Intent Name: [Short label]
Trigger: [What situation prompts this action?]
Information Needed: [What does the expert need to know?]
Possible Outcomes: [What can happen as a result?]
Boundary: [What is NOT part of this intent? What role handles the adjacent work?]
```

---

## Healthcare Project Example

In this project, the initial deep dive with one Patient Navigator (PN) revealed:
- The PN workflow has 3 stages: Intake, Maintenance, Discharge
- Key intents: Eligibility Verification, Stakeholder Alignment, Patient Education, Handoff Coordination
- Critical friction points: bureaucratic delays, insurance complications, provider availability, family dynamics
- Role boundaries: PNs cannot do Social Worker tasks (agency selection, F2F forms, clinical documentation)

Panel expansion to 4 PNs (Lyndsey, Mark, Melissa, Kristin) revealed:
- Regional variations (PA vs. OH vs. NY had different waiver processes)
- Disagreements on how aggressively to advocate vs. when to defer to the Social Worker
- Edge cases: AMA discharges, competitor loyalty, provider illness during discharge
- The concept of "unscripted chaos" -- real cases always have at least one unexpected element

---

## Common Pitfalls

1. **Interviewing too few experts** -- One expert gives you a single perspective. You need at least 3 to find the edges.
2. **Asking leading questions** -- "Do you find X frustrating?" vs. "Walk me through a case where things didn't go as planned."
3. **Over-scoping the initial intent list** -- Start narrow. You'll discover more intents through the annotation flywheel.
4. **Treating the intent list as static** -- Your initial list is a hypothesis. Annotation feedback is the experiment that validates or revises it.
5. **Skipping the workflow map** -- Without understanding the full context, you'll build taxonomies that don't match how experts actually work.

---

## Deliverables

- [ ] Workflow map document (tasks, tools, stakeholders, decision points)
- [ ] Interview notes from 3-5 experts
- [ ] Initial intent list with trigger/information/outcome/boundary for each
- [ ] Complexity drivers list (what makes cases hard)
- [ ] Friction/barrier inventory (what goes wrong)
