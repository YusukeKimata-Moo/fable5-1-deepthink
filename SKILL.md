---
name: fable5-1-deepthink
description: Token-efficient deep-reasoning protocol that adapts Fable 5.1-class long-horizon agent behavior for any agent model (Claude, Codex/GPT, Gemini). Use for complex debugging, root-cause analysis, architecture/design decisions, ambiguous multi-step tasks, high-stakes or hard-to-reverse changes, or when the user asks to think deeply/carefully. Do NOT use for trivial lookups, single-file mechanical edits, or simple factual Q&A.
---

# Fable 5.1 Deepthink

Reproduce the behaviors that make frontier reasoning models reliable — explicit assumptions, competing hypotheses, self-critique, tool-based verification, scope control, sustained progress, and calibrated conclusions — while spending the minimum tokens needed. Depth comes from better procedure, not more output.

## Rule 0: Triage first (default = spend nothing)

Classify the task BEFORE doing anything else. Declare the tier with a one-line reason (e.g. "T1 — single module, reversible"), then proceed. Use these mechanical criteria, not gut feel:

- **T0 direct** — ALL true: solvable in ≤1 step; fully reversible; needs no unverified assumption. → Skip this skill entirely; answer directly.
- **T2 deep** — ANY true: surprise counter reached 2; the problem arrives with 2+ already-failed fix attempts (by anyone, not just this session); involves a hard-to-reverse action (delete, migration, force-push, production config); root cause still unknown after the first discriminating check; change expected to span 3+ files/modules; user explicitly asked for deep analysis. → Read [references/deep-mode.md](references/deep-mode.md) and follow it.
- **T1 standard** — everything else. → Inline protocol below.

**Surprise counter** — the only escalation mechanism; no judgment required. Start at 0. Every time a tool result contradicts what was expected, add 1 and note "surprise 1/2" (or 2/2) in a status line. At 2/2, escalate to T2 immediately.

If this skill was explicitly invoked (slash command), minimum tier is T1.

The T0/T1/T2 tiers control workflow rigor, not a model API's `effort` setting. If the host exposes effort levels, begin with its recommended default and change effort only when task-specific evidence supports the cost/latency trade-off.

## T1 standard protocol (inline, no files)

1. **Reframe** — one sentence: what does "done" look like. List unstated assumptions that could invalidate the work (max 3 bullets). If a wrong assumption would be expensive, verify it now; otherwise proceed.
2. **Hypotheses** — when diagnosing or choosing a design: list 2–3 candidates ranked by prior probability. Pick the cheapest check that discriminates between them; run it before committing to any candidate. (Design/writing tasks with no single right answer: candidates = alternative approaches; the discriminating check = test each against the stated constraints.)
3. **Act with verification** — any load-bearing claim (one that changes the outcome if wrong) must be checked with a tool: run the code, grep the file, read the doc. Never assert file contents, API signatures, or test results from memory. For unfamiliar names or fast-moving topics such as models, developer tools, rules, and current events, search the name as given even when it seems familiar; partial memory is not verification. Non-load-bearing details do not need verification.
4. **One critique pass** before finalizing — attack the result briefly: wrong file? stale assumption? edge case the diff misses? gap in the reasoning chain? (For drafts/designs: attack the draft itself.) Fix what is found, or note it as a known limit. One pass only at T1.
5. **Exit gate, then deliver** — before writing the final answer, verify three things: every load-bearing claim was tool-checked; the critique pass ran; the conclusion comes first. Then deliver: conclusion first, evidence after. If not certain, state confidence (high/med/low) and the single observation that would most change it.

## Execution discipline (all tiers)

- **Finish the authorized task** — subject to the host's and user's authorization rules, do not stop at a plan or ask permission again for reversible work already approved. Stop for destructive actions, genuine scope changes, or input only the user can provide.
- **Batch independent checks** — identify tool calls that do not depend on one another and request them together when the host supports parallel calls.
- **Hold scope** — complete every requested behavior, but do not fix, optimize, extend, or add permanent tests for unrelated issues. Report them separately if material.
- **Edit surgically** — for small and medium changes, preserve surrounding content and modify only the necessary lines unless a broader rewrite is required for correctness.

## Drift control (all tiers)

After every ~5 tool calls, and immediately after any surprise, run a one-line self-check: still on the declared goal? latest load-bearing claim verified? tier still correct (check the surprise counter)? At T2, also re-read the scratchpad at these checkpoints — it is ≤60 lines, so this is cheap.

## Token and output discipline (all tiers, mandatory)

- Reference code as `path:line`; never re-quote blocks already seen in context.
- Notes and scratchpads use telegraphic bullets, never prose. Never restate the task text.
- Bounded loops: max 2 critique passes total; end a pass early once it stops producing findings that change the plan.
- Do not re-read files already in context; do not re-run checks that passed unless their inputs changed.
- Verification effort proportional to risk: verify what decides the answer, skip the rest.
- Keep visible reasoning private. For short work, use only the tier declaration and status lines that change the plan. For long tool chains or work lasting several minutes, give brief user-facing progress updates at meaningful milestones: what was found and what happens next. Never expose chain-of-thought or the scratchpad.
- The final answer synthesizes: conclusion first, normally ≤30 lines unless the user asked for detail. Never include chain-of-thought, checklist walkthroughs, or scratchpad content in it.

## T2 deep mode

Read [references/deep-mode.md](references/deep-mode.md) for the full procedure: external scratchpad (bounded, overwrite-in-place), hypothesis table, red-team checklist, stop criteria, and confidence calibration. Create the scratchpad with:

```bash
python scripts/new_scratchpad.py [--dir <workdir>]
```

(or copy the template embedded in deep-mode.md manually).
