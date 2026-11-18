# Hints (three levels per stop: read ONE level, then try again)

Level 1 = the idea. Level 2 = the API to use. Level 3 = near-code (a skeleton with the key lines; no full solution).

---

## T01 - `llm/critique.py`: the guideline context and the critique chain

**Level 1.** The model needs the retrieved rules in its prompt, short and numbered (it answers with a NUMBER: a 1.5B
model copies the issue name when you ask it for an id). A chain is a recipe: prompt, then model that returns a typed object.

**Level 2.** `format_guidelines`: build one string with `"\n".join(...)`; cut the text with `text.split()[:words]`.
`build_critique_chain`: `ChatPromptTemplate.from_messages([("system", ...), ("human", ...)])` and
`chat.with_structured_output(Critique)`; join them with the `|` operator. The two prompt strings are in `llm/prompts.py`.

**Level 3.**
```python
# format_guidelines
if not rules:
    return "(none)"
return "\n".join(f"{n}. {rule['title']} (for {rule['issue']}): <first `words` words of rule['text']>" for n, rule in enumerate(rules, 1))

# build_critique_chain
prompt = ChatPromptTemplate.from_messages([("system", CRITIQUE_SYSTEM), ("human", CRITIQUE_HUMAN)])
return prompt | <chat with structured output Critique>
```
Check: `pytest -k t01` (fake model, no download).

---

## T02 - `knowledge/guideline_search.py`: retrieve per issue type

**Level 1.** One search PER issue type, each in its own guideline section with its own query text (from the config);
keep the best chunks; a rule must appear once even if two chunks or two issue types find it.

**Level 2.** `retrieval.for_issue(issue)` gives `(section, query)`. `store.retriever(k=..., where={"section": section})` is a
LangChain retriever: `.invoke(query)` returns `Document`s whose `metadata` has `rule_id`, `section`, `title`, `chunk_id`,
`score`; `page_content` is the chunk text. Keep a `set` of rule ids already seen.

**Level 3.**
```python
rules, seen = [], set()
for issue in issues:
    section, query = retrieval.for_issue(issue)
    for document in store.retriever(k=retrieval.per_issue_k, where={"section": section}).invoke(query):
        rule_id = document.metadata["rule_id"]
        if rule_id in seen:
            continue
        seen.add(rule_id)
        rules.append({... "rule_id", "section", "title", "chunk_id", "text": document.page_content, "score", "issue": issue})
return rules
```
Try it for real: `python main.py search "use active voice" --where section=conversational`.

---

## T03 - `graph/state.py`: the two reducers

**Level 1.** In LangGraph a node returns only what is NEW. For a key that grows (attempts, log) the state needs a reducer:
a function `(old, new) -> combined`. `attempts` is special: its rounds must rise (1, 2, 3); a repeated round means a node ran twice.

**Level 2.** The state class already says `Annotated[list[...], add_attempts]`. You write the two functions. `add_attempts`:
read the last round of `left` (0 if empty), loop over `right`, raise `ValueError` when `attempt["round"] <= last`, update `last`.

**Level 3.**
```python
def add_attempts(left, right):
    last = left[-1]["round"] if left else 0
    for attempt in right:
        if <attempt round is not after last>:
            raise ValueError(f"attempt round {attempt['round']} is not after round {last}")
        last = attempt["round"]
    return left + right

def add_log(left, right):
    return left + right
```

---

## T04 - `graph/routes.py` and `graph/nodes/check.py`

**Level 1.** `after_check` is a conditional edge: a function from the state to the NAME of the next node. Three outcomes:
the check passed; it failed and there are rounds left; it failed and there are none. `build_feedback` turns the failed checks into
short exact lines for the model: the facts first (the most important), then the quotes of what is still wrong.

**Level 2.** `state["passed"]`, `state["rounds"]`, `max_rounds`. Node names: `editor_review`, `write`, `pick_best`. For the
feedback: `found` is a dict `issue type -> list of quotes` (from `find_issues`); take `[:3]` of each list; `simple[term]` is the
simple word for a complex term (`simple = {row["complex"]: row["simple"] ...}` is built for you). The line formats are in
the tests (`pytest -k t04`): copy the exact start of each line.

**Level 3.**
```python
def after_check(state, *, max_rounds):
    if state["passed"]:
        return "editor_review"
    return <"write" while rounds < max_rounds, else "pick_best">

# build_feedback
lines = []
if missing:
    lines.append("FACTS MISSING, copy them exactly: " + "; ".join(missing))
for sentence in found["long_sentence"][:3]:
    lines.append(f"Sentence too long ({n} words, limit {editor.sentence_limit}): \"{sentence[:80]}\"")
for term in found["complex_words"][:3]:
    lines.append(f"Complex word \"{term}\": write \"{simple[term]}\"")
lines += [f"Passive voice \"{hit}\": say who does it" for hit in found["passive"][:3]]
...the same for shall (write "must"), hidden verbs, negatives; then the length line if the ratio is outside
   [min_length_ratio, max_length_ratio]: f"Length is {ratio} of the original: keep it between {...} and {...}"
```
The tests pin the start of the FACTS, Sentence, Complex, Passive and Length lines; the other lines are yours.

---

## T05 - `graph/nodes/editor_review.py`: the interrupt

**Level 1.** The node has two halves. First it STOPS the graph and shows the editor what he needs; the graph saves its state and
the process may end. When the editor decides (maybe in another process, tomorrow), the node runs AGAIN from its first line and this
time `interrupt` returns the decision. So everything before `interrupt` must be harmless to repeat (no outside effect, no model call).

**Level 2.** `review_payload(state, deps=deps)` is given: pass its result to `interrupt(...)`. The value `interrupt` returns is
the dict `{"action": ..., "text": ..., "note": ...}`. Return an update dict with `decision`, `rewrite`, `status`, `reason`, `log`.
Use `missing_facts(state["facts"], text)` for the fact check. Rules: approve with a missing fact stays `needs_editor`; edit is
accepted (facts missing in the edit go in the reason); reject keeps the note; any other action raises `ValueError`.

**Level 3.**
```python
decision = interrupt(review_payload(state, deps=deps))
action = decision["action"]
text = state["rewrite"]
if action == "approve":
    missing = missing_facts(state["facts"], text)
    status = "needs_editor" if missing else "approved"
    reason = ...
elif action == "edit":
    text = decision["text"]
    ...
elif action == "reject":
    ...
else:
    raise ValueError(...)
return {"decision": decision, "rewrite": text, "status": status, "reason": reason, "log": [...]}
```
The tests pin these exact texts: approve -> `"approved by the editor"`; approve with a lost fact -> `f"approve refused, facts missing: {missing}"`
(status `needs_editor`); edit -> `f"edited by the editor; facts missing in the edit: {missing}"` (or `"edited by the editor"` when nothing is missing);
reject -> the note, or `"rejected by the editor"` when there is none; any other action -> `ValueError` whose message contains `approve, edit or reject`.
Try it: `python main.py --fake ask D07 --thread a1`, then in ANOTHER command `python main.py --fake resume --thread a1 --action approve`.

---

## T06 - `evaluation/evaluators.py`

**Level 1.** An evaluator is a plain function that scores one case. `facts_kept` is the hard one: ONE lost fact = a failed edit,
so it is 1.0 or 0.0. `issue_score_improved` says how much of the score the edit removed.

**Level 2.** Signature: `(inputs, outputs, reference_outputs)`. `outputs` is the contract; `reference_outputs["facts"]` the
facts. `missing_facts(facts, rewrite)` is in `plainedit.checks.facts`. Return `{"score": float, "comment": str}`.
Scores: `(before - after) / before`, never below 0; if `before` is 0 the only good result is staying at 0.

**Level 3.**
```python
missing = missing_facts(reference_outputs["facts"], outputs["rewrite"])
return {"score": <0.0 if anything is missing, else 1.0>, "comment": ...}

before = outputs["metrics_before"]["issue_score"]
after  = outputs["metrics_after"]["issue_score"]
score  = <1.0 or 0.0 when before == 0, else max(0.0, (before - after) / before)>
return {"score": round(score, 3), "comment": f"{before} -> {after}"}
```

---

## T07 - `observability/trace_config.py` and `my_work/notes.toml`

**Level 1.** A tag is how you FIND runs later ("all v2 runs"); metadata says which case and which backend. Both go into the run
config of the call; LangSmith turns them into filters, and the local trace keeps them.

**Level 2.** `run_config(tracing, tracer=..., run_name=..., metadata=..., extra_tags=(...))` is above you in the same file; `case_config`
is a labelled call to it. For the notes: `python main.py eval v1`, `python main.py eval v2`, `python main.py compare v1 v2`; then
`python main.py trace-show runtime/traces/eval-v2-<case>.json` (one file per case) and open the JSON of the case in an editor.

**Level 3.** `return run_config(tracing, tracer=tracer, run_name=<"edit-" + case>, metadata={...three keys...}, extra_tags=(version,))`.
To find the lost fact: in the JSON, the rows named `check` have `outputs.attempts[0].facts_missing` (round r) and
`outputs.feedback`; the next row named `write` has the same feedback in `inputs.feedback`. The cases where `compare` shows
`facts_kept` going from 0.00 to 1.00 are the best places to look. Write the exact first feedback line in `notes.toml`.

---

## T08 - `integrations/flow_compare.py` and the flow

**Level 1.** Build the slice in Langflow with the SAME collection, the SAME embedding model, the SAME model and the SAME prompt as
the code; then judge both with ONE rule so the comparison is fair: an answer is OK if it contains one of the expected words.

**Level 2.** The values to type into Langflow are in `flows/FLOW_SPEC.json` (written from the config: `python main.py flow-spec`).
Component settings are in section 5 of the README and in your Lesson 2.9 notes (OpenAI Embeddings -> Chroma DB -> Parser -> Prompt
Template -> OpenAI -> Chat Output). `compare_answers`: `zip(questions, code_answers, flow_answers, strict=True)`; `any(word.lower() in answer.lower() for word in question["expect_any"])`.

**Level 3.**
```python
rows = []
for question, code, flow in zip(questions, code_answers, flow_answers, strict=True):
    code_ok = any(...)
    flow_ok = any(...)
    verdict = <"both" | "code_only" | "flow_only" | "neither">
    rows.append({"id": question["id"], "code_ok": code_ok, "flow_ok": flow_ok, "verdict": verdict})
return rows
```
Flow checklist: name `plainedit-rag`; Chroma DB collection `plain-guidelines`, host 127.0.0.1, port 8001, number of results 3; Parser pattern
`[{chunk_id}] {text}`; model name `Qwen/Qwen2.5-1.5B-Instruct`, API base `http://127.0.0.1:8000/v1`, max tokens 300, temperature 0; then
export to `flows/plainedit_rag.json` and run `python main.py flow-show flows/plainedit_rag.json`.

**Langflow 1.12.6 (checked on a real run).** UI names: Chat Input, OpenAI Embeddings, Chroma DB (Persist Directory EMPTY: it talks to the server by host/port), Parser, Prompt Template, OpenAI, Chat Output. The model dropdowns list only OpenAI names: TYPE the local model name, set the base URL to the model server (`http://127.0.0.1:8000/v1`), API key `local`. Switch TikToken OFF on OpenAI Embeddings. `flow-ask` / `flow-compare` need `LANGFLOW_API_KEY` in the environment. Start model server, then `chroma run`, then `index` (server store), then Langflow. The 1.5B model rarely cites `[chunk_id]` in the flow; the flow also has no similarity threshold.

---

## T09 - `REPORT.md`

**Level 1.** The report answers: what worked, what failed (with case ids), what the numbers cannot tell, which tool for what.
**Level 2.** Copy numbers from `python main.py compare v1 v2` and from the traces; do not round up. A limit is a thing that
can still go wrong in production.
**Level 3.** Good errors to look for: a rewrite that passed `facts_kept` but still changed the meaning; a finding whose
quote is real but whose issue type is wrong; a notice that needed all rounds; a metric that fired on a sentence that was fine
(passive voice is a heuristic: "is interested" is not a passive).
