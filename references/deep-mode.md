# T2 Deep Mode

Full protocol for ambiguous, high-stakes, or repeatedly-failed problems. Everything here extends the T1 protocol and token discipline in SKILL.md — those rules still apply.

The core mechanism: externalize durable decision state into a **bounded scratchpad file** instead of relying on one generation or a long conversation history. The scratchpad is working memory, not a log.

## Scratchpad rules (token-critical)

- One file per problem: `.deepthink/thinking.md` in the working directory (create via `scripts/new_scratchpad.py` or copy the template below).
- **Hard cap: 60 lines.** If over, compress — delete resolved items, merge duplicates.
- **Overwrite in place**, never append a history. Dead hypotheses shrink to one line under KILLED with the reason; do not keep their full reasoning.
- Telegraphic bullets and `path:line` pointers only. No prose, no code blocks (point to code, don't paste it).
- Update the file after each significant finding; re-read it before each major decision and immediately after any surprising result (cheap: it is ≤60 lines). Preserve the exact goal, user constraints, decisions, failed approaches and reasons, current state, and next action so context compaction cannot silently change the task.
- When solved, delete only the scratchpad created for this task and only if cleanup is authorized by the host/user rules; otherwise retain a compact completion state. Never delete a pre-existing scratchpad or include it verbatim in the final answer.

## Template

```markdown
# GOAL
- <one line: what "done" looks like, incl. constraints>

# FACTS (verified only — each with evidence pointer)
- <fact> [src: path:line | cmd output]

# ASSUMPTIONS (unverified — promote to FACTS or kill)
- <assumption> [risk if wrong: high/med/low]

# HYPOTHESES
| # | candidate | prior | cheapest discriminating check | status |
|---|-----------|-------|-------------------------------|--------|
| H1 | ... | high | ... | open/testing/confirmed |

# KILLED
- H_: <one-line reason>

# NEXT
- <single next action>

# RISKS / OPEN
- <unresolved concern>
```

## Procedure

1. **Frame** — fill GOAL, FACTS (only what is already verified), ASSUMPTIONS. Mark each assumption's risk. Verify high-risk assumptions before anything else.
2. **Generate hypotheses** — minimum 2, maximum 4. Force at least one non-obvious candidate ("what else could produce exactly these symptoms?"). Rank by prior. (Design/writing tasks: hypotheses = alternative approaches or drafts; discriminating check = test against stated constraints; red-team = attack the leading draft.)
3. **Discriminate cheaply** — order checks by (information gained ÷ token+time cost). Prefer checks that can kill multiple hypotheses at once. Run one check, update the table, re-rank. Loop.
4. **Converge** — a hypothesis is confirmed only when (a) a discriminating check passed AND (b) no open hypothesis explains the evidence equally well. Confirmation by elimination alone is weak — say so in the final confidence.
5. **Red-team pass** (see checklist below) — attack the confirmed result once, thoroughly. If a finding survives, loop back to step 3. Max 2 red-team passes total; after the second, ship with the residual risk stated.
6. **Deliver** — conclusion first; evidence as pointers; confidence + what would change it; residual risks from RISKS section. Apply the scratchpad cleanup rule above.

## Red-team checklist (run once, top to bottom, note only hits)

- **Premise**: is the reported symptom itself verified, or taken on faith?
- **Scope**: does the fix/conclusion hold for all inputs, or just the tested case? Boundary values, empty/null, concurrency, scale?
- **Alternative cause**: could a different mechanism produce identical evidence?
- **Staleness**: any FACT gathered before something changed (edit, rebuild, cache)?
- **Side effects**: what else reads/writes the thing being changed?
- **Reversal test**: if the conclusion were wrong, what would look different? Has that been checked?

## Stop criteria (prevents token spirals)

Stop the current investigation loop and report its limits when ANY of the following apply. These bounds do not waive required validation or make incomplete authorized work complete; continue independently actionable work, or identify the specific blocker.

- Two consecutive checks produced no change to HYPOTHESES status or NEXT.
- Both red-team passes are spent.
- The remaining uncertainty cannot be reduced without input only the user has (access, intent, hardware). Ask precisely for that input instead of continuing.
- Cost of the next-best check exceeds the cost of being wrong (state this trade-off in one line).

## Confidence calibration (use in final answer)

- **High** — discriminating check passed AND alternatives were checked and killed with evidence. Wrong <1 in 10.
- **Medium** — evidence fits, but ≥1 alternative was killed by plausibility, not evidence; or confirmation was by elimination. Wrong ~1 in 4.
- **Low** — best explanation among those considered; discriminating check unavailable. Say what check would settle it.

Never inflate: a Medium answer labeled Medium beats a Medium answer labeled High. State the single observation most likely to overturn the conclusion.
