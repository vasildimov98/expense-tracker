# P1 notes: Develop generative AI apps in Azure

## Module 1: Plan and prepare to develop AI solutions on Azure

**Takeaway:** building an AI solution is more than calling a model endpoint. It means choosing the right capability, service, workflow and safeguards. Foundry is the practical center of a project, but it does not replace sound engineering judgement.

### AI capabilities

- **Generative AI and agents:** generate responses from natural language (chat with prompts and responses).
- **NLP:** extract information from large amounts of text (statistics, classification).
- **Speech:** recognize and produce speech live, even with background noise.
- **Computer vision:** interpret images, video and live camera feeds.
- **Information extraction:** pull what matters out of large documents.

### NLP vs generative AI

- **NLP** is the long-standing field of making computers process human language. **Generative AI** is built on **LLMs**, which evolved from NLP.
- **LLM:** a very large neural network trained on huge amounts of text to predict what comes next. It is the model, not the chat assistant (ChatGPT, Gemini, Claude), which is an application built around a model. In Foundry you call the model endpoint from code.
- Classic NLP and task-specific models (classification, sentiment, summarization) are usually cheaper, faster and more predictable than an LLM, for example for classifying a million emails.
- **Exam link:** choose the right tool for the task. The answer is not always "use the LLM".

### Microsoft Foundry

- Recommended platform for scalable AI solutions on Azure. Used through the **portal** (UI) or the **SDK** (code).
- **Project:** everything (connections, data, code, AI tools) is managed in a project.
  - Each project belongs to a single Foundry **resource** (provides compute, storage, tools). One resource can have several projects, one of them the default.
  - The project home page gives the client app the **API key**, **project endpoint** and **Azure OpenAI endpoint**.
- **What a project manages**
  - **Models:** a catalog of models, accessed through the Azure OpenAI endpoint and SDK.
  - **Agents:** an LLM + instructions + tools, as an autonomous entity. Developed and deployed with Foundry Agent Service.
  - **Tools:** built-in (web search, code interpreter) or custom/third-party via **MCP**. **Foundry Tools** cover common tasks (see below).
  - **Knowledge:** agents connect to knowledge stores to give context to prompts. **Foundry IQ** is one central, MCP-based knowledge connection for many sources (the RAG idea).
- Most AI work starts in a project: find, compare, deploy and test models; create and test agents; connect MCP tools and knowledge; manage access; find endpoints and keys.

**Agent vs model**
- **Model:** input in, output out. No goal, no memory between calls, cannot act. Example: bank description in, "Groceries" out.
- **Agent:** model + **instructions** + **tools**. It decides what to do, calls tools and uses the results. Example: "How much did I spend on groceries last month?" leads it to call `get_spending_by_category`.
- In Foundry: **prompt agent** (declarative, Foundry runs it) or **hosted agent** (your own code, run by Foundry).

**MCP (Model Context Protocol):** an open standard for connecting agents to tools and data ("USB-C for AI tools"). A tool provider runs an **MCP server** that lists its tools. The agent (**MCP client**) discovers and calls them. One tool works with any MCP-capable agent.

**New Foundry vs classic** (checked 2026-10-20). Older tutorials use the classic names, so translate them:

| Classic | New |
|---|---|
| Azure AI Studio / Azure AI Foundry | Microsoft Foundry |
| Azure AI Services | Foundry Tools |
| Hub-based project (hub + Azure OpenAI + AI Services) | Foundry project under a single Foundry resource |
| Assistants API (threads, messages, runs) | Responses API / Agents v2 (conversations, items, responses) |
| Monthly `api-version` parameters | Stable v1 routes (`/openai/v1/`) |
| Many packages and 5+ endpoints | One project client (`azure-ai-projects` 2.x) and one project endpoint |

The study guide targets the new architecture (Foundry projects, agents, Foundry Tools).

### Foundry Tools

Ready-made services for common tasks. They are cheaper than relying on models and agents for everything.

- **Azure Language:** extract and summarize text.
- **Azure Speech:** speech to text, text to speech.
- **Azure Translator:** translation.
- **Azure Document Intelligence:** extract fields from complex documents.
- **Azure Content Understanding:** extract data from forms, documents, images, video and audio.

### Developer tools

IDEs (Visual Studio, VS Code) plus the **Microsoft Foundry Toolkit** extension, which lets you work from code to a Foundry project and back. Copilot can boost productivity.

### Responsible AI

AI is probabilistic and depends on its training data. Never trust the output blindly. Consider the impact on users and society from the start.

**Six principles (FRPITA):**

| Principle | Idea |
|---|---|
| **Fairness** | Treat all people fairly. Check that training data represents everyone and evaluate subgroups throughout. (Loan approval must not disadvantage groups.) |
| **Reliability and safety** | Test rigorously, apply sensible confidence thresholds. (Autonomous vehicles, prescriptions.) |
| **Privacy and security** | Protect personal data in training and in production. |
| **Inclusiveness** | Empower everyone. Involve diverse people in design and testing. |
| **Transparency** | Users should understand the purpose, how it works and its limits, and how their data is used. |
| **Accountability** | People are responsible for AI systems. Work within a governance framework. |

---

## Module 2: Select, deploy, and evaluate Microsoft Foundry models

**Goal:** use the Foundry portal to compare, deploy and test models against quality and safety requirements, then evaluate them.

### Model catalog

- 1900+ models. Billed by Azure directly, or by trusted third parties with their own billing and subscriptions (Marketplace).
- Each **model card** shows provider, capabilities, benchmarks, responsible AI notes and deployment options.
- **Filters:** collection, capabilities (reasoning, tool calling, multimodal), source/provider, inference task, fine-tuning method, industry.
- **LLM vs SLM**
  - **LLM** (GPT-5, Mistral Large, Llama 3 70B): deep reasoning, complex generation, large context. Needs more compute.
  - **SLM** (Phi-4, Llama 3 8B): cheaper and faster for common NLP tasks. Can run on low-end hardware or edge devices.

**Model types**

| Type | Use |
|---|---|
| Chat completion | Conversation and content generation (most models) |
| Reasoning | Math, coding, science, strategy. Breaks problems down and shows its reasoning |
| Embedding (`text-embedding-3-large/small`) | Text to numbers. Semantic search, recommendations, **RAG** |
| Image generation (GPT-image-1) | Images from text |
| Video generation (Sora 2) | Video from text |
| Image analysis (GPT-4.1) | Multimodal input (text + images), text output |
| Text to speech (GPT-4o-tts), speech to text (GPT-4o-transcribe) | Audio conversion |
| Regional / domain-specific | Language, region or industry (medical, legal) models that often beat general ones in their domain |

### Selecting models with benchmarks

You usually have to **trade off** quality, safety, cost and performance. Compare candidates with:
- the **Model leaderboard** in the catalog (ranked by quality, safety, estimated cost, throughput), or
- the **Benchmarks tab** on a model card (one model vs similar ones).

**Quality:** accuracy, coherence and relevance, measured on public datasets (for example GPQA, MMLU-Pro, MATH, HumanEval+, IFEval). Dataset names are not worth memorizing.

**Safety** (important for user-facing and regulated apps)

| Metric | Benchmark | Reading |
|---|---|---|
| Harmful behavior | HarmBench, **Attack Success Rate (ASR)** | **Lower** = safer |
| Toxic content detection | ToxiGen, F1 score | **Higher** = better detection |
| Sensitive domain knowledge | WMDP (biosecurity, cyber, chemical) | **Higher** = more knowledge of dangerous capabilities (not "better") |

HarmBench covers standard harmful behavior, contextually harmful behavior (misinformation, harassment) and copyright violations.

**Cost** (serverless API and Azure OpenAI models)
- Price per 1M **input** tokens and per 1M **output** tokens.
- **Estimated cost** blends both at a **3:1 input:output** ratio. Lower = cheaper.

**Performance**
- **Latency:** mean, P50 (median), P90, P95, P99, and **time to first token (TTFT)** for streaming.
- **Throughput:** generated tokens/s (GTPS), total tokens/s (TTPS), time between tokens.
- The leaderboard uses **mean TTFT (lower is better)** and **mean GTPS (higher is better)**.
- Real-time apps need low latency and high throughput. Batch jobs can favor cost instead.

**Comparing**
- **Trade-off charts:** two metrics at once (quality vs cost, throughput or safety). Top-right is best on both. A slightly less accurate but much cheaper or faster model can be the better pick.
- **Side-by-side:** compare 2-3 models on benchmarks, details (context window, training data, languages), supported endpoints and features (function calling, structured output, vision).

### Deploying models to endpoints

**Deployment types** = scope x billing:

| Scope | Standard (pay per token) | Provisioned (reserved PTU) | Batch (async) |
|---|---|---|---|
| **Global** (any region) | Highest quota, best for general workloads | Predictable high throughput | **50% discount**, jobs finish within 24 hours |
| **Data Zone** (US, EU, APAC) | Data stays in the zone (compliance) | Reserved PTUs in the zone | Batch jobs in the zone |
| **Regional** (single region) | Regional data residency, low volume | Reserved PTUs in one region | n/a |

- **Developer:** any region, pay per token, for **fine-tuned model evaluation only**.
- Each model lists which types it supports. **Use Global Standard whenever possible.**

**Deploying (portal)**
1. Discover > Models, open the model card, select **Deploy** (default or custom settings).
2. Partner/community models need an **Azure Marketplace subscription** (accept terms). Models sold directly by Azure (for example GPT-4o-mini) do not.
3. Settings:
   - **Deployment name:** defaults to the model name. Your code passes it in the `model` parameter to route requests.
   - **Deployment type:** chosen automatically from model and environment.
   - **Managed compute only:** VM SKU (needs Azure ML compute quota) and instance count.
4. After deploying you land in the playground. Check that the status is **Succeeded**.

**Managing:** Build > Models. The details page shows configuration and status, endpoint URL, keys/tokens, monitoring and usage, and lets you adjust or delete the deployment.

**Playground** (test without code)
- Try simple questions, multi-step reasoning, specific formats and edge cases.
- **System message:** sets context, tone and instructions for all inputs.
- **Parameters:** temperature (creativity vs consistency), max tokens (response length), top-p (nucleus sampling).
- **Code tab:** ready-to-copy samples (Python, C#, JavaScript) for auth, endpoint and request format.

**Calling it from code** needs three things:
1. **Endpoint URL:** project endpoint (Foundry-specific features) or OpenAI v1 endpoint (broad OpenAI API compatibility).
2. **Authentication:** key/token, or **Microsoft Entra ID** (**recommended for production**).
3. **Deployment name:** goes in the `model` parameter.

### Evaluating models

**Why:** catch quality problems before production, improve user satisfaction, enable continuous improvement (re-evaluate after every prompt, feature or model change), and verify compliance and safety.

**Manual evaluation** (slow, but catches what metrics can't: tone, satisfaction, brand fit)
- **Interactive testing** in the playground. You can compare models **side by side** with synced system instructions and prompts.
- **Structured review:** a set of test cases rated by humans (usually 1-5) on relevance, informativeness, engagement, accuracy and safety.
- **User studies:** feedback from real or representative users reveals issues controlled tests miss.

**Automated evaluation** (scales, consistent, objective). Two kinds:

*AI-assisted:* you pick a GPT model as the **evaluator model**, which scores your model's responses.
- **Generation quality:**
  - **Groundedness:** based on the provided context, not speculation. *Groundedness Pro* gives a binary grounded/not grounded result.
  - **Relevance:** addresses the question.
  - **Coherence:** flows logically.
  - **Fluency:** linguistically correct and natural.
- **Risk and safety:** self-harm, hateful and unfair, violent, sexual, protected material (copyright), indirect attack (jailbreak).
  - Content harm results are a **defect rate**: the % of responses above a severity threshold (typically Medium).
  - Protected material and indirect attack: (true instances / total) x 100.

*NLP metrics:* pure math, **no evaluator model**, but they need **ground truth** (expected answers). Good when there is a definite correct answer, poor for open-ended generation.

| Metric | Use |
|---|---|
| **F1-score** | Shared words between output and ground truth, balancing precision and recall. Classification, information retrieval |
| **BLEU** | n-gram overlap with a reference. Machine translation |
| **METEOR** | Like BLEU but handles synonyms, stemming and paraphrasing |
| **ROUGE** | Favors recall. Summarization (cover the key points) |
| **GLEU** | BLEU variant for sentence-level evaluation |

**Running a full evaluation** (Evaluation page in the portal)
- **Evaluate a:** model (you give prompts, it generates outputs), agent (user-defined prompts), or dataset (outputs already in your data).
- **Test data:** upload a CSV or JSONL file, reuse an existing project dataset, or **generate a synthetic dataset** from a topic description (you set the resource, number of rows and a prompt).
- Configure metrics, field mappings and the system prompt, then start the job. It runs **asynchronously**, row by row.
- **Results:** aggregate scores plus per-prompt details.
- **Evaluator library:** Microsoft-curated evaluators (quality, safety, performance) with details and annotation prompts, plus your own **custom evaluators**, with version management.

**Iterating on results**
- **Low quality:** prompt engineering, a different model, **RAG** (ground answers in your data), fine-tuning. Each step adds complexity and often cost.
- **Safety concerns:** content filters (Azure AI Content Safety), prompt hardening (safety instructions in the system message), output validation before showing users.
- Set evaluation benchmarks **early**, then re-run after changes to catch regressions.

### Module 2 takeaway

Catalog > compare with benchmarks > deploy > test in the playground > evaluate (manual + automated) > iterate. Next steps named by the module: integrate via SDK/REST, RAG, Azure AI Content Safety, fine-tuning, monitoring with Azure Monitor and Application Insights, and iterating on user feedback.

**Deployment options in the module summary** (older wording, same idea): serverless API (pay per call), provisioned (steady high volume), managed compute (VM-based), batch (cheap, non-interactive).

---

## Module 3: Develop an AI chat app with Microsoft Foundry

**Goal:** choose the right endpoint, SDK, authentication and chat API for a generative AI chat app.

### Workflow

Test in the model playground (temperature etc.) > use **Generate code** in your language as a starting point > adjust the code > go back to the playground and repeat.

### Four choices

| Choice | Options |
|---|---|
| **Endpoint** | Project endpoint or Azure OpenAI endpoint (every project has both) |
| **SDK** | Foundry SDK (`azure-ai-projects`) or OpenAI SDK. Both give an OpenAI-compatible client |
| **Authentication** | **Microsoft Entra ID** for production (the app runs under an identity). API key or token in some scenarios |
| **Chat API** | **Responses** (recommended for new projects) or **ChatCompletions** (established, works across many models and platforms) |

### The two endpoints

| | Project endpoint | Azure OpenAI endpoint |
|---|---|---|
| Format | `https://{resource}.services.ai.azure.com/api/projects/<project>` | `https://{resource}.openai.azure.com/openai/v1` |
| Used with | Foundry SDK (`AIProjectClient`) | OpenAI SDK (`OpenAI` client with `base_url`) |
| Gives you | Project features (connections, agents, tracing, evaluations, datasets, indexes) and, through `get_openai_client()`, model inference | Model inference only, with the **broadest OpenAI API compatibility** |
| Pick it when | The app uses Foundry features, not only model calls | Existing OpenAI code should work with minimal changes, or you want to stay portable |

You can combine both in one app: Foundry SDK for project features, OpenAI SDK for inference. Both find the endpoint on the project's **Overview** page.

### Foundry SDK

- Install `azure-ai-projects` (it pulls in `openai` and `azure-identity`).
- Sign in first (for example `az login`), because `DefaultAzureCredential` uses your Azure session.

```python
project_client = AIProjectClient(credential=DefaultAzureCredential(), endpoint=project_endpoint)
openai_client = project_client.get_openai_client()   # OpenAI-compatible client for chat
```

- Use it for: Foundry Agent Service, tools and approvals, cloud evaluations, tracing/observability, Foundry direct models, project metadata, connections and governance. **Microsoft recommends it for apps with agents, evaluations or Foundry-specific features.**

### OpenAI SDK

- Install `openai azure-identity` (`azure-identity` only for Entra ID).
- Authentication options:
  - **Entra ID (recommended):** `get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")` passed as `api_key`.
  - **API key:** read from an environment variable and store it in **Azure Key Vault**. Never put it in code.
  - **Environment variables** `OPENAI_BASE_URL` and `OPENAI_API_KEY`: `OpenAI()` picks them up automatically.
- `AzureOpenAI` client: only when you need a specific Azure OpenAI API version (you give `azure_endpoint` and `api_version`). Otherwise use `OpenAI`.
- Use it for: full OpenAI API compatibility, portability between OpenAI and Azure OpenAI, Chat Completions/Responses/Images. It does **not** give you agents or evaluations.

### Responses API (recommended)

- **Stateful** (keeps context across turns), unifies Chat Completions and Assistants patterns, and works with Foundry direct models (Phi, DeepSeek) too.

```python
response = openai_client.responses.create(
    model="gpt-4.1",               # deployment name
    instructions="You are ...",    # system prompt
    input="What is ...?",
    temperature=0.8, max_output_tokens=200,
    previous_response_id=last_id,  # continues the conversation
)
response.output_text
```

- **Response object:** `output_text`, `id`, `status`, `usage` (token counts), `model`.
- **Parameters:** `temperature` (0-2), `max_output_tokens`, `top_p` (alternative to temperature).
- **Multi-turn:** pass `previous_response_id=<last response.id>`. Instructions are not carried over, so send them each turn. `responses.retrieve(id)` fetches an old response.
- **Manual chaining:** build the `input` list of messages yourself. Use it to choose what context is included, prune history to fit token limits, or store history in a database.
- **Context window:** every request re-sends instructions, current prompt, history, tool schemas, tool outputs and retrieved documents. **The SDK manages state but does not make tokens cheaper.**

### Responsive apps

- **Streaming:** `stream=True`. Handle events `response.output_text.delta` (text chunks) and `response.completed` (gives the response id for the next turn).
- **Async:** `AsyncOpenAI` + `await`. It only helps when requests overlap (`asyncio.gather`). A single awaited call is no faster than sync.

### ChatCompletions API

```python
completion = openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
)
completion.choices[0].message.content
```

- **Stateless:** you keep the `messages` list yourself, append each assistant reply and user message, and send the **whole history every turn**.
- Know it for code maintenance and cross-platform compatibility.

### Knowledge check answers

- Broadest OpenAI API support: **Azure OpenAI endpoint**.
- Python package for the Foundry SDK: **`azure-ai-projects`**.
- Responses API call: **`client.responses.create()`**.

---

## Module 4: Develop generative AI apps with tools

**Why tools:** a model only knows its training data. Tools let it access real-time information, take actions (send email, create records), ground answers in facts (less hallucination), connect to your systems, and chain multi-step workflows.

**Do not confuse** these tools (callable by a model in a prompt) with **Foundry Tools** (Azure AI APIs such as Language and Speech).

**Scope of this module:** the **client app** configures the tools in each request, so the logic lives in your app. This is the first step toward **agents**, where model + instructions + tools are persisted in a named agent.

### Using tools in the Responses API

- Pick a model with **tool calling** capability, deploy it, and pass a `tools=[...]` list to `responses.create()`.
- By default **the model decides** when and which tool to use. You can guide it with `instructions` or tool selection rules.

```python
response = client.responses.create(
    model=deployment, instructions="...", input="...",
    tools=[{"type": "web_search"}],     # one or more tool definitions
)
```

### The four tools

| Tool | What it does | Definition | Remember |
|---|---|---|---|
| **`code_interpreter`** | Model writes and runs **Python** in a sandbox | `{"type": "code_interpreter", "container": {"type": "auto"}}` | No external network access. Has pandas, numpy, matplotlib. Handles files (CSV, JSON, images). Sees errors and retries. Timeouts and memory limits. Models call it the "python tool", so say that in instructions. Adds tokens |
| **`web_search`** | Fetches current information from the web | `{"type": "web_search"}` | For data that changes (prices, news, policy). Results vary between runs and source quality varies. Adds latency and tokens |
| **`file_search`** | Semantic search over **your uploaded files** (private/domain knowledge) | `{"type": "file_search", "vector_store_ids": [id]}` | Needs a **vector store**: create it and upload files first. Edited files must be re-indexed. `include=["file_search_call.results"]` shows retrieved passages for debugging. This is **RAG** |
| **`function`** | Model requests a call to **your own function** | `{"type": "function", "name": ..., "description": ...}` (plus parameters) | The model does **not** run it. Your code does |

### Function calling flow (the exam favorite)

1. Define the function(s) in `tools`.
2. The model decides if a call is needed. If so, the response contains a **`function_call`** item (name, arguments, `call_id`).
3. **Your app runs the function** itself.
4. Append a **`function_call_output`** item (with the same `call_id` and the result) to the input.
5. Call `responses.create()` again. The model uses the result in its final answer.

Example: "Hello" gets a normal reply. "What time is it?" triggers a `get_time` call.

### Best practices that repeat across tools

- Be specific in prompts and instructions, and keep focus narrow.
- Always validate results. AI-generated code, web results and tool arguments can all be wrong. Keep a human check for high-stakes decisions.
- Function tools: small single-purpose functions, **validate arguments** (never trust them blindly), return clear errors, log calls, and require explicit authorization for high-impact actions.
- Watch cost and latency, because tools add tokens and time.
- Use clean, scoped document stores for `file_search` (for example separate HR and legal).

### Knowledge check answers

- Answer from your own uploaded policy documents: **`file_search`**.
- After a `function_call` item: **run the function in your code and send back a `function_call_output`**.
- `code_interpreter`: **runs Python in a sandboxed runtime**. It cannot browse the web.

### Module 4 takeaway

The same pattern applies to every tool: define it in the request, let the model decide when to use it, return tool output where needed (functions), and validate the result. Next step: persist model + instructions + tools as an **agent**.

---

## Module 5: Optimize generative AI model performance

**Problem:** a base model may not match your tone, your private data or your output format. Three complementary strategies, from cheap and quick to expensive and slow: **prompt engineering > RAG > fine-tuning**.

### 1. Prompt engineering

Cheapest, no infrastructure or training data, start here.

- **Prompt components:** system message, user message, assistant message (earlier replies), examples.
- **System message:** first in the conversation, highest-level instructions. It defines role, boundaries, tone and output format. It **influences but does not guarantee** compliance, so test it and layer it with content filtering and evaluation.
- **System message checklist:** start with the role, define boundaries, specify the output format, add a "when unsure" policy (ask a clarifying question).
- **Prompt patterns:**
  - **Persona:** "You're a seasoned marketing professional..."
  - **Format template:** state the exact fields you want back.
  - **Chain of thought:** ask for step-by-step reasoning, or split the task into sub-steps. For **non-reasoning models** only, because reasoning models (o-series) do it internally.
  - **Few-shot:** give example input/output pairs. One example is one-shot, none is **zero-shot**.
- **Delimiters** (`---`, Markdown headings, XML tags) separate instructions from content. **Recency bias:** text near the end of the prompt weighs more, so repeat the key instruction at the end if it is ignored.
- **Parameters:** **temperature** (low ~0.2 = factual and deterministic, high ~0.7 = creative) and **top_p** (only the most probable tokens that add up to that share). **Change one, not both.**
- **Limits:** it cannot give the model knowledge it lacks (your hotel catalog), and it cannot force consistent behavior.

### 2. RAG (Retrieval Augmented Generation)

Grounds the model in trusted data. Prompting changes *how* it answers, RAG changes *what it knows*. Without grounding, the model may invent plausible but false details.

- **Three steps:** **Retrieve** relevant data > **Augment** the prompt with it > **Generate** the answer.
- **Embedding:** text turned into a vector (list of numbers) by an embedding model. Similar meaning = vectors close together, even with different words. **Cosine similarity** measures closeness by angle (near 1 = very similar).
- **Azure AI Search** is the retrieval part:
  1. Add data (Blob Storage, Data Lake Gen2, OneLake, or upload).
  2. Create an index with an embedding model.
  3. Query: the question is embedded and matched to similar content.
- **Search types:** keyword (exact terms), semantic (meaning), vector (embeddings), **hybrid** (all combined, **recommended for generative AI**).
- **In code:** put the retrieved text into the system message or input of `responses.create()`.
- **Use RAG when:** the model needs private/domain data, the data changes often (no retraining needed), accuracy is critical, or the model's training cutoff is too early.
- Quality depends on the index and on how the data is chunked.

### 3. Fine-tuning

Further trains a pretrained model on a smaller task-specific dataset, which adjusts its internal **weights**. Goal: **consistent behavior** (style, tone, format), not new facts.

- Uses **LoRA (Low-Rank Adaptation)**: updates only a small set of parameters, so it is faster and cheaper than full retraining.
- **Use it for:** consistent brand voice, reliable structured output (JSON), shorter prompts (patterns baked in), **distillation** (large model teaches a smaller, cheaper one), better tool selection and parameters.
- **Types:**
  - **SFT (supervised):** labeled prompt+response pairs. Best for clear, well-defined tasks.
  - **RFT (reinforcement):** a grader rewards better responses step by step. For complex tasks and better reasoning.
  - **DPO (direct preference optimization):** preferred vs non-preferred response pairs. Lighter than reinforcement learning. Can follow SFT.
- **Training data:** **JSONL**, each line a conversation of system + user + assistant messages. Use the **same system message** in every example and again at deployment. At least hundreds of high-quality, representative examples.
- **Challenges:** training cost plus **hourly hosting** cost, data quality (overfitting, underfitting, bias), retraining when data or the base model changes, hyperparameter tuning (epochs, batch size, learning rate), **model drift** (too narrow, worse at general tasks).
- **Always evaluate a baseline first**, or you cannot tell whether fine-tuning helped.

### Comparing and combining

| | Time | Complexity | Cost | Best for |
|---|---|---|---|---|
| **Prompt engineering** | Low | Low | Per-token only | Tone, format, behavior, quick iteration |
| **RAG** | Medium | Medium | Search + storage + tokens | Accuracy, private or changing data |
| **Fine-tuning** | High | High | Training + hosting + tokens | Consistency, style, shorter prompts, distillation |

- **Optimize for context** (RAG) vs **optimize the model** (fine-tuning). Prompt engineering is the foundation under both.
- **Combinations:** prompt + RAG (most common: behavior + facts), prompt + fine-tuning (style + per-session instructions), RAG + fine-tuning (style + current data), all three (style + knowledge + guardrails).
- **Decision framework:** start with prompting > add RAG if accuracy needs data > add fine-tuning if consistency fails despite good prompts > combine as needed. Add complexity only when needed.

### Knowledge check answers

- System message: **defines role, behavior and output constraints**.
- RAG over prompting alone: **when the model needs domain-specific or current data**.
- Temperature: **randomness and creativity**.
- Fine-tuning optimizes: **consistency of behavior, style and output format**.
- Product catalog + brand voice: **RAG for the catalog, fine-tuning for the voice, prompt engineering for conversation-specific instructions**.

---

## Module 6: Implement a responsible generative AI solution

Generative AI can produce content that looks human-made, so it needs a practical process to identify, measure and mitigate risks. This builds on Microsoft's Responsible AI standard (the six principles from Module 1). The four stages match the functions of the **NIST AI Risk Management Framework**.

**Four stages: Map > Measure > Mitigate > Manage**

### 1. Map potential harms

1. **Identify** harms. They depend on the models, services, and any fine-tuning or grounding data. Typical ones: offensive or discriminatory content, factual inaccuracies, content that supports illegal or unethical behavior. Sources: the Azure OpenAI **transparency note**, model system cards, and the **Responsible AI Impact Assessment** guide and template.
2. **Prioritize** by **likelihood x impact**, considering intended use and misuse. This is partly subjective, so the team decides and may consult legal or policy experts. (Smart kitchen copilot: wrong cooking times are likely, a poison recipe is rare but severe.)
3. **Test and verify** with **red teaming**: testers deliberately try to produce harmful output. It extends normal security red teaming. This can also reveal new harms.
4. **Document and share** the verified harms with stakeholders, and keep the list updated.

### 2. Measure harms

Goal: a **baseline** you can compare against after each mitigation.

1. Prepare diverse prompts likely to trigger each documented harm.
2. Submit them and collect the output.
3. Apply **strict, pre-defined criteria** to categorize the output (harmful/not, or severity levels).

**Manual first** on a small set, to check that results are consistent and criteria are clear. **Then automate** at volume (for example with a classification model). Keep **periodic manual testing** to validate new scenarios and check the automation still works. Document and share the results.

### 3. Mitigate harms (four layers)

| Layer | Mitigations |
|---|---|
| **Model** | Choose a model suited to the task (a simpler model can carry less risk), fine-tune on your own data to keep responses scoped |
| **Safety system** | **Foundry guardrails**: content filters with 4 severity levels (safe, low, medium, high) across 4 categories (hate and fairness, sexual, violence, self-harm). Also **prompt shields** (detect attempts to subvert the system prompt) and task-adherence detection for agents |
| **System message and grounding** | System message sets behavior, prompt engineering with grounding data, **RAG** from trusted sources |
| **User experience** | UI that constrains input topics/types, input and output validation, transparent documentation of capabilities, limitations and remaining risks |

Retest after mitigations and compare against the baseline.

### 4. Manage the solution

**Pre-release reviews:** legal, privacy, security, accessibility.

**Release and operate:**
- **Phased delivery**: a restricted group first, to gather feedback before wider release.
- **Incident response plan** (with response-time estimates) and **rollback plan**.
- Ability to **immediately block** harmful responses, and to **block users, apps or IP addresses** that misuse the system.
- A way for users to **report** inaccurate, harmful or offensive content.
- **Telemetry** for satisfaction and gaps, compliant with privacy laws and policy.

### Knowledge check answers

- AI Impact Assessment: **document purpose, expected use and potential harms**.
- Safety-system-level mitigation in Foundry: **guardrails**.
- Phased delivery: **gather feedback and find issues before wider release**.

### Module 6 takeaway

Map harms, measure them, mitigate at several layers, and manage the release and operation. None of these stages replaces another.
