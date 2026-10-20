# AI-103 study plan (Azure AI Apps and Agents Developer Associate)

Blueprint: the official study guide, https://aka.ms/AI103-StudyGuide (skills as of April 16, 2026; page updated 2026-10-15).
Course material: the four Microsoft Learn paths in `study/learn-paths.md` (titles, times and links). "P1 m3" means Path 1, module 3.
Exam: 120 minutes, pass mark 700, proctored. Retake after 24 hours. Free yearly renewal.

## What the four paths cover, against the study guide

| Study guide domain | Covered by | Not covered (self-study from the guide + Learn/docs search) |
|---|---|---|
| Plan and manage (25-30%) | P1 m1 (plan and prepare), m2 (select, deploy, evaluate models), m6 (responsible AI) | Quotas, scaling and cost; security (managed identity, keyless, private networking, RBAC); monitoring (drift, safety events, index health); CI/CD; auditing and agent governance. Days 6-9. |
| Generative AI and agents (30-35%) | P1 m3-m5; all of P2 (tools, MCP, Foundry IQ RAG, workflows, multi-agent) | Tracing, token analytics and evaluations in practice. Day 28. |
| Computer vision (10-15%) | P4 m1-m6 | Visual responsible AI (indirect prompt injection in images). Day 35. |
| Text analysis (10-15%) | P3 all (text, speech, translation) | None known. |
| Information extraction (10-15%) | P4 m4-m8 (Content Understanding, Document Intelligence, AI Search knowledge mining) | Vector, hybrid and semantic search in practice, indexers and skillsets. Days 40-41. |

## Rules

1. **One Day = about 2 hours (90-135 min).** Module times are Microsoft's own and include the exercise units. If you have less, tell me and I re-split the Days. Days are numbered, not dated.
2. **One topic per Day.** Exception: a 20-minute "quiz me" warm-up or tail is allowed on any Day.
3. **Read the Microsoft Learn pages yourself.** The exam is written from them. This chat is your study partner (quizzes, explanations, mapping to your code), not the curriculum.
4. **Unfamiliar terms are learned in place.** Keep a running `study/glossary.md`. Only add a term if it is still unclear after the module that teaches it.
5. **Python is just-in-time.** The Python course is paused. If you hit a Python thing you don't understand: one line in `study/python-jit.md`, read the page below for **at most 30 minutes**, then go back.
6. **Azure access gate.** Reading never needs Azure. Every "Do (Azure)" task and every module Exercise unit does. Until access arrives: do the reading, tick the Day as `[~]`, and put each lab in `study/lab-queue.md`. The first Day after access arrives is only for A1 (below), then the queue, oldest first. Nothing later starts until the queue is empty.
7. **A1 (first thing once you have Azure):** a budget alert set to a small amount, one Foundry project in a new resource group, a screenshot of the alert. Delete each lab's resources the same Day you finish it.
8. **Work Azure account:** follow your employer's policy and use only made-up data. Register for the exam itself with a **personal Microsoft account**, not a work one (Microsoft's own advice on the exam page).
9. **Day done = its Output exists.** Tell me "Day N done" plus the Output and I tick it here.
10. **Exam relevance:** P2 m5 (Microsoft 365 integration) is not in the study guide bullets, so you only skim it (15 min).

### Python just-in-time triggers
| When you meet | Read this (max 30 min) |
|---|---|
| `with` in SDK code | Python docs: "The with statement" and `contextlib` intro |
| `@something` above a function | Python docs glossary: "decorator", then one short tutorial of your choice |
| `async def` / `await` | Python docs: `asyncio` "Coroutines and Tasks" |
| `for chunk in response:` (streaming) | Python docs: "Iterators" and "Generators" in the tutorial |
| `class A(B):` | Python tutorial: "Inheritance" |
| `DefaultAzureCredential` / environment variables | Python docs: `os.environ`, then the Azure Identity README |

## Progress

Current Day: **Day 2** (Day 1 done 2026-10-20). Azure access pending: labs are queued in `study/lab-queue.md`. Mark `[x]` done, `[~]` reading done but a lab is queued.

---

## Phase 0: Orientation (Day 1)

- [x] **Day 1.** Read (no Azure needed): the study guide's "Skills at a glance" and the skills list once (30 min); then open each of the four paths on Learn and read only the intro and module list (30 min). Create empty `study/glossary.md`, `study/lab-queue.md`, `study/notes-p1.md`. **Output:** the three files exist.

## Phase 1: P1 Develop generative AI apps (Days 2-5)

- [ ] **Day 2.** P1 m1 (Plan and prepare, 1 hr) and m2 (Select, deploy, evaluate models, 1 hr 3 min). **Output:** `notes-p1.md` with 5 bullets per module in your own words.
- [ ] **Day 3.** P1 m3 (Chat app with Foundry, 53 min) and m4 (Apps that use tools, 1 hr). **Output:** notes. Tell me how long Days 2 and 3 really took and I recalibrate.
- [ ] **Day 4.** P1 m5 (Optimize model performance: prompt engineering, RAG, fine-tuning, 2 hr 11 min). **Output:** notes: when to use prompt engineering vs RAG vs fine-tuning, in 5 lines.
- [ ] **Day 5.** P1 m6 (Responsible generative AI, 45 min). **Do (Azure):** `scratch/hello_foundry.py` (git-ignored) calls your deployed model once, key in an environment variable (JIT triggers apply, 45 min). **Output:** it prints a reply; then "quiz me on P1" (10 questions, **pass 8 of 10**; under 8, redo the weakest module).

## Phase 2: The part of "Plan and manage" the paths do not cover (Days 6-9)
Study guide bullets, then Learn/docs search. Portal and concepts, no Python.

- [ ] **Day 6.** Quotas, scaling, rate limits and cost for model and agent workloads. **Do (Azure):** find the quota page for your subscription and note your tokens-per-minute limit. **Output:** `study/notes-d1.md`: what happens at a limit and your two options.
- [ ] **Day 7.** Security: managed identity, keyless credentials, private networking, role policies. **Do (Azure):** assign yourself an RBAC role on the Foundry resource and test access without a key. **Output:** notes: key vs managed identity vs private endpoint in 5 lines.
- [ ] **Day 8.** Monitoring (model performance, drift, safety events, grounding quality, search index health) and CI/CD for Foundry projects. **Output:** notes: a table of what to monitor and with which tool.
- [ ] **Day 9.** Responsible AI operations: safety filters, evaluators, trace logging, provenance, approval workflows, agent oversight and tool-access controls. **Do (Azure):** create a content filter configuration and test it with a harmless borderline prompt. **Output:** notes; then "quiz me on Plan and manage" (**pass 8 of 10**), then take the official **practice assessment** for the first time (check whether it can be taken by domain; if not, the full one) and record the score per domain in `study/scores.md`.

## Phase 3: Finish the tracker's milestone 2 (Days 10-15)
Plans: `plans/step-06-bank-csv-import.md`, then the step 7 plan I write for you.

- [ ] **Day 10.** Step 6, Stories 1-2. **Output:** commits.
- [ ] **Day 11.** Step 6, Stories 3-4. **Output:** commits.
- [ ] **Day 12.** Step 6, Stories 5-6, then review with me. **Output:** "step 6 is done" from me.
- [ ] **Day 13.** Step 7: monthly summaries and top categories. **Output:** commits.
- [ ] **Day 14.** Step 7: filters and simple pytest tests. **Output:** commits.
- [ ] **Day 15.** Step 7 review. **Output:** "step 7 is done" from me, tag `v2`.

## Phase 4: P2 Develop AI agents, and the tracker's smart steps (Days 16-30)

- [ ] **Day 16.** P2 m1 (Agents with Foundry and VS Code, 1 hr 35 min). **Output:** `study/notes-p2.md`.
- [ ] **Day 17.** P2 m2 (Custom tools, 53 min) and m3 (MCP tools, 51 min). **Output:** notes.
- [ ] **Day 18.** P2 m4 (Foundry IQ knowledge-enhanced agents, 1 hr 11 min), plus a 15-minute skim of m5 (Microsoft 365 integration; read the summary and knowledge check only). **Output:** notes.
- [ ] **Day 19.** P2 m6 (Agent-driven workflows, 1 hr 4 min) and m7 (Microsoft Agent Framework, 55 min). **Output:** notes.
- [ ] **Day 20.** P2 m8 (Multi-agent orchestration, 1 hr 13 min) and m9 (A2A, 56 min). **Output:** notes.
- [ ] **Day 21.** "Quiz me on P2" (20 min warm-up, **pass 8 of 10**). Then tracker step 8: rule-based categorization from a JSON config (plan by me). **Output:** commits.
- [ ] **Day 22.** Step 8 review. **Output:** "step 8 is done" from me.
- [ ] **Day 23.** Tracker step 9, first half: send only unmatched transactions to the model, fallback "Uncategorized", **made-up data only**, structured JSON output. **Output:** commits.
- [ ] **Day 24.** Step 9, second half: switch the calls to keyless auth with `DefaultAzureCredential`. **Output:** commits; no key in code or Git.
- [ ] **Day 25.** Step 9 review, tag `v3`. **Output:** "step 9 is done" from me.
- [ ] **Day 26.** Tracker step 10, first half: tool functions over your report functions. **Output:** commits.
- [ ] **Day 27.** Step 10, second half: the agent answers "how much did I spend on groceries last month?". **Output:** commits.
- [ ] **Day 28.** Observability and evaluation: study guide bullets on tracing, token analytics, latency, safety signals, evaluations, error analysis. **Do (Azure):** turn on tracing for the agent and read one trace. **Output:** `study/notes-d2.md` plus a trace screenshot.
- [ ] **Day 29.** Step 10 review, tag `v4`. **Output:** "step 10 is done" from me.
- [ ] **Day 30.** "Quiz me on generative AI and agents" (**pass 8 of 10**). Weak topics get a re-read of the matching module.

## Phase 5: Vision, text and information extraction (Days 31-44)

- [ ] **Day 31.** P4 m1 (Vision-enabled app, 43 min), m2 (Generate images, 33 min), m3 (Generate videos, 48 min). **Output:** `study/notes-p4.md`.
- [ ] **Day 32.** P4 m4 (Analyze images with Content Understanding, 43 min) and m5 (Multimodal analysis, 1 hr). **Output:** notes.
- [ ] **Day 33.** P4 m6 (Content Understanding client app, 1 hr) and m7 (Document Intelligence, 1 hr 11 min). **Output:** notes.
- [ ] **Day 34.** P4 m8 (Knowledge mining with Azure AI Search, 1 hr 8 min). **Output:** notes.
- [ ] **Day 35.** Study guide bullets on visual responsible AI (filters for unsafe images, indirect prompt injection in image text, visual policy rules). **Do (Azure):** send 3 made-up receipts to a Content Understanding analyzer, keep the JSON in `samples/receipts/`. **Output:** the JSON plus notes; then "quiz me on vision" (**pass 8 of 10**).
- [ ] **Day 36.** P3 m1 (Analyze text with Azure Language, 46 min) and m2 (Text analysis agent with the Language MCP server, 52 min). **Output:** `study/notes-p3.md`.
- [ ] **Day 37.** P3 m3 (Speech-capable generative AI app, 43 min) and m4 (Speech-enabled apps with Azure Speech, 53 min). **Output:** notes.
- [ ] **Day 38.** P3 m5 (Speech agent with the Speech MCP server, 52 min) and m6 (Voice Live agent, 52 min). **Output:** notes.
- [ ] **Day 39.** P3 m7 (Translate text and speech, 48 min). Then "quiz me on text analysis and speech" (**pass 8 of 10**). **Output:** notes.
- [ ] **Day 40.** Read: study guide "Information extraction" bullets and the Azure AI Search docs: indexers, skillsets, OCR in ingestion, vector, hybrid and semantic search. **Output:** `study/notes-d5.md`: one paragraph per search type and when to use it.
- [ ] **Day 41.** **Do (Azure):** an Azure AI Search index over your made-up statements; run vector, hybrid and semantic queries and compare the results. **Output:** the comparison in notes. Resource group deleted afterwards.
- [ ] **Day 42.** Optional tracker step: connect the agent to your search index (RAG). **Output:** commits, or "skipped" in the log.
- [ ] **Day 43.** "Quiz me on information extraction" (**pass 8 of 10**).
- [ ] **Day 44.** Re-read the study guide skills list and tick each bullet you can explain without notes. Unticked bullets become the Day 45 list. **Output:** `study/gaps.md`.

## Phase 6: Practice and exam (Days 45-50)

- [ ] **Day 45.** Study only the gaps in `gaps.md`. **Output:** notes.
- [ ] **Day 46.** Official practice assessment, second attempt (first was Day 9). **Output:** score per domain in `study/scores.md`.
- [ ] **Day 47.** Review every wrong answer, group by domain, read the matching Learn page for each. **Output:** list of causes.
- [ ] **Day 48.** Exam sandbox (https://aka.ms/examdemo) so the question types are familiar, then retake the practice assessment. **Output:** score.
- [ ] **Day 49.** Rule: **book the exam only if both practice scores are 80% or higher** (and no domain below 70%). Otherwise repeat Days 45-48 once. Check "Exam Replay" and the price on the certification page before paying. **Output:** exam booked, or a repeat decision.
- [ ] **Day 50.** Light review of `gaps.md`. No new material. Rest the day before the exam.

## Checkpoints to repeat in this chat
Say "quiz me on <topic>" and I ask 10 questions from the study guide bullets and the modules you did, mark them, and log the score here. Say "Day N done" plus the Output and I update the progress above.
