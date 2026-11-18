# REPORT - PlainEdit

Name: <TODO your name>    Date: <TODO>    Backend and model of your runs: <TODO e.g. local, Qwen/Qwen2.5-1.5B-Instruct>

Write what you really saw. Numbers come from your own `results/` files and traces. Short is fine; invented is not.

## 1. Results: v1 (one shot) against v2 (critique + rewrite + check loop)

Dev cases (12). Copy the `mean` line of `python main.py eval v1` and `eval v2`:

| metric | v1 | v2 |
|---|---|---|
| facts_kept | <TODO> | <TODO> |
| issue_score_improved | <TODO> | <TODO> |
| sentence_limit_ok | <TODO> | <TODO> |
| findings_grounded | <TODO> | <TODO> |
| planted_recall | <TODO> | <TODO> |
| traps_ok | <TODO> | <TODO> |
| mean seconds per case | <TODO> | <TODO> |
| model calls (all cases) | <TODO> | <TODO> |

From `python main.py compare v1 v2`: cases that got better: <TODO ids>. Cases that got WORSE or mixed: <TODO ids and why>.
Is v2 better than v1 on every metric? <TODO say no where it is not>.

## 2. Errors I found (at least 3, real, with case ids)

| # | case | what went wrong (model, code metric, or my code) | where I saw it (file / trace row) | what would fix it |
|---|---|---|---|---|
| 1 | <TODO> | <TODO> | <TODO> | <TODO> |
| 2 | <TODO> | <TODO> | <TODO> | <TODO> |
| 3 | <TODO> | <TODO> | <TODO> | <TODO> |

The loop at work (from my_work/notes.toml): in case <TODO> a fact was lost in round <TODO>; the feedback that restored it was: <TODO>.

## 3. Limits: what can still go wrong in production

- Passive voice is a heuristic (a form of "to be" + a word ending in -ed or an irregular participle). Give one false positive and one false negative you saw: <TODO>
- `facts_kept` checks the facts the editor listed or the code found. A fact that nobody listed can change and nothing notices: <TODO an example>
- A rewrite can keep every fact and still change the meaning, e.g. <TODO>
- The 1.5B model: <TODO what it could not do reliably, e.g. giving the right issue type for a finding>
- The instruction guard removes sentences that match patterns; a differently worded instruction would pass: <TODO>

## 4. Langflow slice against the code

What the flow answered as well as the code (`python main.py flow-compare`): <TODO>. Where they differed and why (same prompt, same model?): <TODO>.
What the flow cannot do here (no loop, no code check, no human pause): <TODO in your words>.

## 5. Tool choice

| job | tool I would use | why |
|---|---|---|
| answer a question about the guidelines | <TODO> | <TODO> |
| rewrite with a check and a limit on rounds | <TODO> | <TODO> |
| find out which version is better | <TODO> | <TODO> |
| let a colleague who does not code change the prompt | <TODO> | <TODO> |

## 6. What I would do next

<TODO one or two sentences>
