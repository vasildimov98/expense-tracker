# P2 notes: Develop AI agents on Azure

## Module 1: Develop AI agents with Microsoft Foundry and Visual Studio Code

**Goal:** build, configure, extend, test and deploy agents with Foundry Agent Service, in the Foundry portal or in VS Code (Foundry Toolkit extension).

### AI agents

- **AI agent:** a software service that uses generative AI to understand and perform tasks for users or other programs. Unlike rule-based apps, it understands context, makes decisions and takes actions toward a goal. Unlike a plain chat model, which only generates text, it can act.
- **Why useful:** automation of routine tasks, better decision-making, scalability without proportional staff, 24/7 availability.
- **Use cases:** personal productivity (Microsoft 365 Copilot), research, sales (lead qualification), customer service (for example refund requests), developer agents (GitHub Copilot).

### Security risks of agents

Agents access data and act on their own, so design for security from the start.

| Risk | Idea |
|---|---|
| Data leakage and privacy exposure | Agent includes confidential data in a customer-facing answer |
| Prompt injection | Malicious input overrides the agent's behavior (leaks credentials, unauthorized actions) |
| Unauthorized access, privilege escalation | Weak access control lets an agent do admin-level actions in a connected system |
| Data poisoning | Corrupted training or context data leads to biased or unsafe decisions |
| Supply chain vulnerabilities | Compromised external API, plugin or model endpoint |
| Over-reliance on autonomous actions | Unconstrained agent sends payments or publishes unverified content |
| Inadequate auditability and logging | Misuse cannot be traced or detected early |
| Model inversion and output leakage | Repeated queries extract private training or fine-tuning data |

**Mitigations (security by design):**
- **RBAC** and **least privilege**.
- Prompt filtering and validation layers.
- **Human-in-the-loop** approval or sandboxing for sensitive operations.
- Full logging and traceability of agent actions.
- Regular audits of third-party dependencies.
- Continuous retraining and validation to detect drift or poisoning.

### Foundry Agent Service

- **Fully managed** service to build, deploy and scale agents without managing compute and storage. Build in the portal or in code (under 50 lines).
- **Agent types:**
  - **Declarative agents** (defined by configuration, not code):
    - **Prompt-based agent:** one agent = model + instructions + tools + prompts. The most common type, and the focus of this module.
    - **Workflow agent:** multi-agent orchestration defined in **YAML**.
  - **Hosted agents:** containerized agents **created and deployed in code**, hosted by the platform. Full control over logic, the platform manages infrastructure.

**Key features**

| Feature | Meaning |
|---|---|
| Automatic tool calling | The service runs the whole lifecycle: run the model, invoke tools, return results |
| Securely managed state | Conversation state is managed through the **Responses API** (no manual state handling) |
| Tool catalog | Built-in and community tools (code execution, file search, web search, Azure and external APIs) |
| Model selection | Pick a model for your performance and cost needs |
| Enterprise-grade security | Secure data handling, **keyless authentication**, built-in content safety filters |
| Customizable storage | Platform-managed, or bring your own Azure Blob storage |
| Observability and tracing | Built-in monitoring to track behavior and debug |

### Development approaches

| | Foundry portal | VS Code (Foundry Toolkit extension) |
|---|---|---|
| Style | Web UI, no code | Code editor, visual Agent Designer + direct YAML |
| Use when | Quick prototyping, visual configuration, centralized management, stakeholder collaboration, dashboards (token usage, latency, evaluations) | Developer-centric workflow, agent config in **Git** next to app code, fast iteration, code-first YAML editing, local/offline design |

Both support the full workflow. Many teams use the portal for exploring and the extension for detailed development.

**Extension sections**
- **Resources:** deployed models, declarative agents, hosted agents, connections, vector stores (for File Search).
- **Tools:** Model Catalog, Model Playground, Agent Playgrounds (remote or local), Local Visualizer, Deploy Hosted Agents.
- **Help and Feedback.**

**Workflow (same in both):** connect to the project > create the agent (name, purpose) > configure instructions > add tools > test in a playground > iterate > deploy > integrate into the app.

**Required resources:** a **Foundry project** and a **model deployment** (for example GPT-4.1). Creating a project provisions the infrastructure automatically.

**Optional services:** Azure AI Search (Foundry IQ, File Search), Azure Storage (files), Azure Key Vault (secrets), Azure Functions (custom tools).

### Building an agent in the portal

1. https://ai.azure.com, select the project.
2. **Build > Agents > Create.**
3. Enter **name, description, model** (a deployed one, or deploy a new one).
4. Configure **instructions** (the foundation of behavior), plus **Temperature** and **Top P**.
5. Test in the **Playground** tab (it keeps the conversation history during the session).
6. Add tools, then save/deploy. After deployment, call the agent through the Foundry SDK or REST.

**Tool catalog (Build > Tools)** has three categories:

| Category | Contents |
|---|---|
| **Configured** | Built-in, ready to use: Code Interpreter, File Search |
| **Catalog** | Added from a registry: Bing Web Search, Azure AI Search, SharePoint, MCP servers |
| **Custom** | Your own tools via **OpenAPI** specs or custom implementations |

### Setting up VS Code

- Install **Foundry Toolkit for VS Code** from the Marketplace (search "Foundry Toolkit").
- Connect: **Azure icon > sign in > subscription > Foundry section > right-click project > Open in Foundry Extension.**
- **Deploy a model** from Resources > Model deployments > **+**: choose model, deployment name, model version, capacity.
- Agents created in the portal appear automatically in Resources. Changes made in VS Code can be saved back to Foundry.
- Managing many agents: browse by project, compare YAML side by side, duplicate, archive.

### Configuring agents (declarative prompt-based)

Hosted agents are configured in code and workflow agents use a different YAML schema. This applies to prompt-based agents.

**Agent Designer properties:**
- **Name**, **description**, **model** (dropdown shows only models already deployed in the project), **system instructions**.
- **Agent ID:** generated automatically, used when calling the agent through APIs.
- **Temperature:** low (0.1-0.3) = consistent and focused, high (0.7-1.0) = creative. Business agents with structured tasks: 0.3-0.7.
- **Top P:** limits the vocabulary choices, default 1.0. Lower it for more constrained output.
- Designer and YAML stay **synchronized**.

**YAML structure** (sections: metadata, model, instructions, tools):

```yaml
version: 1.0.0
name: healthcare-assistant
description: ...
id: 'agent-abc123xyz'
metadata: {authors: [...], tags: [...]}
model:
  id: 'gpt-4.1'
  options: {temperature: 0.5, top_p: 1}
instructions: |
  You're a ... (responsibilities, guidelines)
tools: []
```

**YAML benefits:** version control, bulk updates, reusable templates, code review, automation by script. The extension validates syntax in real time.

**Best practices:** version control the YAML, descriptive names and tags, comment complex instructions, **test after every change**, start simple then iterate, one focused purpose per agent.

### Extending agents with tools

**Tool-calling lifecycle (automatic):** user message > agent decides which tools are needed > invokes tools with parameters > tools return results > agent builds the natural-language response > reply to user.

**Common tools**

| Tool | What it does |
|---|---|
| **Code Interpreter** | Writes and runs **Python** in a sandbox: math, data analysis, charts, file processing |
| **File Search** | **RAG** over documents you uploaded to a **vector store** (PDF, .docx, .txt, .md). Indexed automatically for semantic search |
| **Bing Web Search** | Real-time internet information, with automatic **citations** |
| **Azure AI Search** | Retrieval from your **existing enterprise-scale search indexes** (File Search = documents uploaded directly to the agent) |
| **OpenAPI tools** | External APIs described by an **OpenAPI 3.0** spec. Foundry maps parameters and parses responses |

Other tools: Browser Automation, Computer Use, Image Generation, SharePoint, Microsoft Fabric, Deep Research, **Agent-to-Agent**, Custom Code Interpreter, **Memory** (information across sessions).

**Adding tools:** in the Agent Designer (Tools > Add Tool / **+**; some tools prompt for assets, for example File Search asks for a vector store) or in YAML:

```yaml
tools:
  - type: code_interpreter
  - type: bing_grounding
    bing_grounding: {connection_id: "..."}
  - type: file_search
    file_search: {vector_store_ids: ["vectorstore-123"]}
```

Some tools need extra parameters (connection IDs, vector store references).

**MCP servers** (from the Catalog): standard way to add custom tools, reusable across agents.
- **Remote:** hosted externally, most common in production.
- **Local:** runs on your machine, for development and testing.
- **Custom:** your own implementation.
- Benefits: standard protocol, reusable components, community tools, simpler integration.

**Tool best practices:**
- Start with **built-in tools** before custom ones (tested, maintained).
- Match tools to requirements. Every tool adds **latency**.
- Tell the agent in the instructions **when and when not** to use each tool.
- Keep File Search documents current.
- Test tool invocation and error scenarios in the playground.
- **Toolboxes** (enterprise, many agents): bundle tools behind **one managed MCP endpoint** with central authentication, versioning and governance. A tool update reaches all agents **without redeployment**.

### Testing, deploying and publishing

**Test in the playground (portal or VS Code):** happy path, edge cases (ambiguous or incomplete input), boundary testing (out-of-scope requests respect the instructions), multi-turn context, tool invocation. Record results to catch regressions.

**Deploy to the project** (saves the configuration to the Foundry project):
- **Portal:** open the agent > verify > **Save** > confirm version and settings.
- **VS Code:** **Save to Foundry**. For hosted agents: Build menu > **Deploy to Microsoft Foundry**, with a method:
  - **Code (ZIP Code Deploy):** packages source, no container image.
  - **Container (BYOI):** pre-built image from Azure Container Registry.

**Every agent automatically gets:**
- **Stable endpoint:** the URL stays constant across versions.
- **Entra agent identity:** its own identity and RBAC scope, **separate from the project identity**.
- **Authentication policy:** Microsoft Entra ID only. Callers need the **Foundry User** role on the agent resource. **API keys are not supported.**
- Also an agent blueprint.

**Important:** permissions do not transfer from the project identity. Assign RBAC roles to the **agent identity** for every resource it uses, or tool calls that worked in development fail with authorization errors after publishing. A `403 Forbidden` on the endpoint: check the Foundry User role.

**Publishing** = distributing to external consumers. One step from the portal to **Microsoft Teams** and **Microsoft 365 Copilot**, no rebuild.

**Endpoint (Responses API protocol):**
`https://<resource>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/openai/responses`

Verify: get a token with `az account get-access-token --resource https://ai.azure.com`, then POST `{"input": "Say hello"}` with a Bearer header.

**Updating:** save the new configuration in the portal. The endpoint routes traffic to the new version automatically, with the same URL.

**Integration code:** in VS Code select the deployed agent in My Resources > **View Code** > choose folder. It generates code to authenticate, connect, send messages and process responses.

**Integration patterns:** web apps, API-driven workflows (backend services on events or schedules), chatbots (map sessions to conversations), background automation.

**Production considerations**

| Area | Practice |
|---|---|
| Monitoring | Response times, tool success rates, errors, token use via **Application Insights** |
| Security | Managed identities, least privilege, data retention policies |
| Cost | Monitor tokens, response length limits, rate limiting |
| Error handling | Retry with **exponential backoff** for transient failures and rate limits, validate inputs |
| Conversation management | Agent endpoints support only the **stateless** Responses API, so **store the history in your client** |

**Note the contrast:** the service manages conversation state while you build and test, but a published agent endpoint is stateless and the client keeps the history.

### Knowledge check answers

- Main benefit over standard APIs: **it handles tool calling, state management and infrastructure automatically**.
- Conversation state: **through the Responses API, which manages the context automatically**.
- NOT a recommended security practice: **giving agents unrestricted access to all enterprise data**.
- Agent needs a tool: **it invokes the tool automatically, processes the results and includes them in its response**.

### Module 1 takeaway

Agent = model + instructions + tools, managed by Foundry Agent Service. Prompt-based (declarative), workflow (YAML) and hosted (code) agents. Build in the portal or VS Code, extend with the tool catalog and MCP, test in playgrounds, deploy, then publish to a stable Entra-secured endpoint. Remember to give the agent identity its own RBAC roles.

---

## Module 2: Integrate custom tools into your agent

**Goal:** give an agent your own code or a third-party API when the built-in tools (knowledge, code generation) are not enough.

### Why custom tools

- Tools make custom functionality **available** to the agent. The agent decides whether to use them, based on the user prompt.
- Benefits: **productivity** (automate repetitive tasks), **accuracy** (precise, consistent output, less human error), **tailored solutions** for specific business needs.
- **Flow:** user asks about ski resort weather > agent sees it has a weather API tool and calls it > tool returns the report > agent answers the user.
- **Typical uses:** customer support (CRM: order history, refunds, shipping status), inventory management, appointment scheduling, IT helpdesk (tickets, knowledge base), e-learning (LMS).

### The four custom tool options

| Option | What it is | Use when |
|---|---|---|
| **Function calling** | You describe your own function to the agent. The agent returns which function to call and with which arguments. Any supported programming language | The logic is **local code in your app** |
| **Azure Functions** | Serverless, event-driven code with **triggers** (when it runs) and **bindings** (connections to input/output data) | You already have an Azure Function, or need event-driven processing (HTTP request, queue message) |
| **OpenAPI 3.0 tool** | Connects the agent to an external HTTP API described by an OpenAPI 3.0 spec | A web service already has an OpenAPI spec |
| **Azure Logic Apps** | Low-code/no-code workflows connecting apps, data and services | You want a workflow without code |

### Function calling

1. Write the function (clear name, documented parameters).
2. Register it as a `FunctionTool`: `name`, `description`, `parameters` (JSON schema with `properties` and `required`), `strict=True`.
3. Create the agent with `project_client.agents.create_version(name=..., definition=PromptAgentDefinition(model, instructions, tools=[function_tool]))`.

The agent calls the function when the prompt needs its information. Your app still runs the function (see P1 m4: `function_call` > run > `function_call_output`).

### Azure Functions

- Develop and deploy the function first, then add an `AzureFunctionTool` to the agent definition.
- The example uses a **Storage Queue**: an **input binding** queue (agent sends the request), an **output binding** queue (function returns the result), plus a function name, description and parameters.

### OpenAPI tool

- Needs a JSON spec file: `servers` (base URL), `paths`, parameters, responses, and an `operationId`.
- Register as `OpenApiTool(openapi=OpenApiFunctionDefinition(name, spec, description, auth=...))`.
- **Supported authentication (3):** **anonymous**, **API key**, **managed identity**.
- Foundry handles parameter mapping and response parsing.

### Key idea: declarative

You do **not** write code that calls the tool. The agent decides from the prompt. **Meaningful function names and well-documented parameters** let it work out when and how to call them.

### Knowledge check answers

- Custom tools: **callable functions that an agent can use to extend its capabilities**.
- Integrate an OpenAPI 3.0 web service: **add it as an OpenAPI specification tool in the agent definition**.
- Local function in your app code: **function calling**.

### Module 2 takeaway

Pick the custom tool by where the logic lives: local code = function calling, existing event-driven Azure code = Azure Functions, existing REST API with a spec = OpenAPI tool, low-code workflow = Logic Apps. The agent chooses when to call them.

---

## Module 3: Integrate MCP tools with Azure AI agents

**Goal:** connect an agent to tools hosted on an MCP server, either through your own MCP client or through Foundry's built-in `MCPTool`.

### Why MCP and dynamic tool discovery

- Registering, updating and maintaining many tools by hand gets complex. With **dynamic tool discovery** the agent asks a central **MCP server** (a live catalog) for its tools at runtime, so no tool is hardcoded in the agent.
- **Advantages of MCP:**
  - **Dynamic tool discovery:** the agent receives the tool list with descriptions. "Integrate once", no manual code per API or per API change.
  - **Interoperability across LLMs:** switch or evaluate models without reworking integrations.
  - **Standardized security:** one consistent authentication method, not separate keys per API.
- **Benefits:** tools can be added, updated or removed centrally **without redeploying the agent**. Agents always get the latest tool version. Scalability, modularity (agents delegate), maintainability, flexibility.
- Best where tools change quickly or many teams own different APIs.

### Pipeline: MCP server, MCP client, agent

| Part | Role |
|---|---|
| **MCP server** | Registry that hosts the tools. Functions are exposed with the **`@mcp.tool`** decorator. Created with `FastMCP("server-name")`, which builds tool definitions from **Python type hints and docstrings** and serves them over HTTP |
| **MCP client** | Bridge between the server and the agent service. Opens a client session to the server |
| **Agent** | Calls the tools like native functions |

### Option 1: your own MCP client (manual)

1. The server hosts tools decorated with `@mcp.tool`.
2. The client opens a **client session** to the server.
3. **`session.list_tools()`** discovers the available tools.
4. Each tool is wrapped in an **async function** that calls **`session.call_tool(tool_name, tool_args)`**.
5. The functions are bundled into a **`FunctionTool`**.
6. The `FunctionTool` is registered in the agent's toolset.

- **Why async:** the agent can invoke tools without blocking.
- The agent still needs the wrappers: this is a function-calling setup fed by the MCP catalog.

### Option 2: remote MCP server with `MCPTool` (Foundry built-in)

- Foundry Agent Service supports **remote MCP servers** directly. You **don't** create a client session, wrap functions or call `session.call_tool`. Tools are **invoked automatically** during the agent run.
- **Needs:** a remote MCP server endpoint (for example `https://api.githubcopilot.com/mcp/`) and a Foundry agent configured with the MCP tool.
- Several servers = several `MCPTool` objects on the agent.

**`MCPTool` parameters**

| Parameter | Meaning |
|---|---|
| `server_label` | Unique identifier of the server (for example GitHub) |
| `server_url` | The MCP server URL |
| `allowed_tools` (optional) | List of the specific tools the agent may use |
| `require_approval` (optional) | Whether calls need human approval |

- **Custom headers** (`update_headers`): pass API keys, OAuth tokens or other headers the server requires.
- **`require_approval` values:** **`always`** (a developer approves every call, **the default**) and **`never`**.

**Approval flow**

1. The model tries to call a tool that needs approval.
2. The agent response contains an **`mcp_approval_request`** (which tool is called, so you can decide).
3. You send a follow-up with an **`mcp_approval_response`** containing the **`approval_request_id`** and an **`approve`** boolean.

**Steps:** create `MCPTool` (label, url) > `update_headers` if needed > set `require_approval` > create the agent with the tool in its list > invoke a prompt.

### Own client vs `MCPTool`

| | Own MCP client | `MCPTool` |
|---|---|---|
| Client session, wrappers, `FunctionTool` | You write them | Not needed |
| Tool invocation | Your wrapper calls `session.call_tool` | Automatic during the run |
| Server | Any server your client reaches | **Remote** MCP server |
| Approval control | Your own code | `require_approval`, `mcp_approval_request/response` |

### Knowledge check answers

- MCP server role: **hosts tool definitions and makes them available for discovery by the client**.
- Client retrieves tools: **`session.list_tools()`**.
- Why wrap tools in async functions: **so the agent can call tools without blocking**.

### Module 3 takeaway

MCP moves tool management out of the agent into a server. The agent discovers tools at runtime, so tools change without redeploying it. For Foundry, prefer `MCPTool` with a remote server: automatic invocation, `allowed_tools` to limit what it can use, and `require_approval` (default `always`) as the human-in-the-loop control.

---

## Module 4: Build knowledge-enhanced AI agents with Foundry IQ

**Goal:** give agents access to organizational knowledge through a shared platform instead of rebuilding a RAG pipeline for every agent.

### Why RAG for agents

Simple agents have limits:

| Limitation | Impact |
|---|---|
| Knowledge cutoff dates | No recent information (new features, updated policies) |
| No private data | Generic answers, missing company procedures |
| Lack of context | Ignores your security requirements or approval workflows |
| Fabricated responses | Confident but wrong, a compliance and security risk |
| Scalability | Every team rebuilds the same RAG infrastructure |

**RAG:** **Retrieve** relevant content from knowledge bases > **Augment** the user's question with it > **Generate** the answer from training data plus retrieved content.
- Gains: **real-time updates** without retraining, **source transparency** (which documents informed the answer), **factual grounding**.

### Foundry IQ

- A **managed knowledge platform** for agents, **built on Azure AI Search**, shared by many agents. Replaces building a RAG system per agent.
- **Knowledge bases are organized by business domain** (Product Documentation, HR Policies), **not by storage location**. One knowledge base can combine SharePoint, Blob Storage, OneLake and an existing search index. The agent sees one unified source.
- **When you add a data source** it does: discovery (scan for documents) > processing (**chunking and embedding**) > indexing > monitoring (changes trigger **automatic reindexing**).
- **Built-in retrieval intelligence** (no custom code):
  1. Analyzes the question.
  2. Selects a strategy: simple factual questions use keyword search, complex ones combine semantic search with **query expansion**.
  3. Ranks by relevance, so fewer tokens are needed.
  4. Provides **citations**.
- **Shared advantage:** several agents can use one knowledge base (Product Documentation serves the support agent and the developer agent, HR Policies only the employee assistant). Improve a knowledge base once and every connected agent benefits immediately.
- **Connected through MCP:** the knowledge base is an MCP server, so the agent uses it as an `MCPTool` (see Module 3):

```python
knowledge_tool = MCPTool(
    server_label="product-docs",
    server_url=f"{search_endpoint}/knowledgebases/product-documentation/mcp",
)
```

then `tools=[knowledge_tool]` in `PromptAgentDefinition`.

### Data sources for a knowledge base (six)

| Source | Access | Best for |
|---|---|---|
| **Azure AI Search index** | Indexed | You already have an index. Gives semantic ranking, custom scoring profiles, faceted navigation, multi-language |
| **Azure Blob Storage** | Direct | Files in blob containers (PDF, .docx, .txt, .md, HTML). No index to build and maintain. Organize containers by topic or access level |
| **Web** | Real-time | Current public information via **Bing**. Less control over sources, so use indexed sources where accuracy and verification matter. Combine it as a supplement to internal sources |
| **SharePoint (Remote)** | Real-time | Simplest path. Queries SharePoint live, **no index to maintain**, always current, **respects SharePoint permissions**. Limited advanced search |
| **SharePoint (Indexed)** | Indexed | Faster, full Azure AI Search capabilities (custom analyzers, enrichment pipelines, combining with other sources). Needs index updates, freshness depends on the schedule, permissions configured during indexing |
| **OneLake** | Direct | Unstructured data in a **Microsoft Fabric** lakehouse (BI reports, data documentation, research outputs) |

**Decision guide:** SharePoint + simple and current = Remote. SharePoint + advanced search = Indexed. Files in Azure = Blob. Fabric data = OneLake. Existing index = AI Search index. Public current info = Web. **Multiple sources can be combined in one knowledge base.**

### Configuring retrieval (instructions)

**Problem:** with vague instructions ("Answer HR questions using the knowledge base") the agent may answer from training data (generic), search without citing (unverifiable), or search, cite and ground (the only acceptable one).

**Good retrieval instructions specify three things:**
1. **When to retrieve:** always search the knowledge base, never answer from training data.
2. **How to cite:** the exact citation format, for example `【doc_id:search_id†source_name】`.
3. **What to do when unsure:** a fallback message when the knowledge base has no answer.

**Test with different query types** (create a conversation, then `responses.create(conversation=..., extra_body={"agent": {"name": ..., "type": "agent_reference"}})`):

| Query type | Expected behavior |
|---|---|
| Straightforward factual | Direct retrieval with citations |
| Needs synthesis | Several documents retrieved, one answer with multiple citations |
| Outside the knowledge base | Graceful fallback ("I don't have that information...") |
| Ambiguous | Clarifying question, or a focused search on the most relevant topic |

**Good response = four traits:** **grounding** (from the knowledge base), **citation** (every claim has a source), **relevance**, **completeness**. If not met, refine the instructions and iterate.

**Instructions by agent type**
- **Customer-facing support:** high accuracy, never guess. Fallback is "connect to a specialist". Official product information only.
- **Internal research assistant:** search all relevant knowledge bases, synthesize across sources, cite all, state confidence.
- **Specialized domain expert (for example compliance):** strict scope, cite document **and section**, refer legal interpretation to the team, note the policy's effective date.
- **Pattern:** define scope, specify retrieval requirements, set citation standards, handle edge cases explicitly.

### Production monitoring

Real users ask differently than your tests. Track:
- **Citation frequency:** are sources cited consistently?
- **Fallback frequency:** how often "I don't know"? (Gaps in the knowledge base content.)
- **Query types:** what categories are most common?
- **Retrieval accuracy:** do the retrieved documents contain the answer?

Use this to refine instructions, content and search configuration.

### Data quality techniques (from the summary)

- **Scoring profiles:** boost specific fields or attributes.
- **Semantic ranking:** AI models rank by meaning, not only keywords.
- **Custom analyzers:** handle HTML, product codes, technical terminology.

### Knowledge check answers

- Main advantage of RAG over simple agents: **it grounds responses in current organizational information and provides source transparency**. (Not: it replaces the LLM, or it retrains the model when documents change.)
- Real-time SharePoint access with Microsoft 365 governance: **SharePoint Remote**.
- Purpose of scoring profiles: **boost specific fields or attributes so more important results surface first**. (Not encryption, not chunking and embedding.)
- Why specify retrieval behavior in instructions: **without it, agents may answer from training data, give unverifiable answers or not cite sources**. (Instructions do not set the ranking algorithm and do not update knowledge base content.)

### Module 4 takeaway

Foundry IQ = shared, MCP-connected knowledge bases over Azure AI Search, organized by business domain and fed by Blob, SharePoint (remote or indexed), OneLake, web or an existing index. Retrieval behavior is controlled by instructions (always retrieve, cite in a fixed format, fall back safely), then tested by query type and monitored in production.

---

## Module 5: Integrate Microsoft Foundry agents with Microsoft 365 (skim only)

Not in the study guide bullets, so only the summary and knowledge check were read.

### Key points

- **Direct publishing from the Foundry portal** puts an agent into **Microsoft Teams** and **Microsoft 365 Copilot**. It automatically provisions **Azure Bot Service** and creates the **Microsoft Entra ID** registrations.
- **Publish scopes:**

| Scope | Use |
|---|---|
| **Shared** | Testing with a few people |
| **Organization** | Broad distribution. Needs **admin approval** before it is available to all users |

- **Agent identity:** a published agent gets a **new identity**, so tool permissions are **not transferred**. Reassign RBAC roles to it (same warning as in Module 1).
- **Work IQ:** a **CLI and MCP server** that connects agents to Microsoft 365 data through MCP.
- **Microsoft 365 Agents Toolkit:** the alternative to direct publishing for complex enterprise needs: **custom SSO, middleware logic, multi-environment deployment**.

### Knowledge check answers

- Resource created when publishing to Teams: **Azure Bot Service**.
- Shared vs organization scope: **organization scope needs admin approval before the agent is available to all users**.
- Tool permissions after publishing: **the published agent gets a new identity and needs permissions reassigned**.
- Work IQ: **a CLI and MCP server that connects AI agents to Microsoft 365 data**.
- Use the Agents Toolkit instead of direct publishing: **when you need custom SSO, middleware logic or multi-environment deployment**.

---

## Module 6: Build agent-driven workflows using Microsoft Foundry

**Goal:** orchestrate several agents, control flow and human input in a visual workflow, then call it from code.

### What a workflow is

- A **visual, declarative** way to orchestrate AI actions: connected **nodes** form an execution path. The platform manages execution and state. Workflows are the **workflow agents** from Module 1 (YAML-defined multi-agent orchestration).
- Coordinates agents with different roles (classification, decision, resolution) in one process.
- Can **pause, ask a human, or escalate** when confidence is low or context is missing.
- Executes in a **conversational context**: you test it in the chat window and watch inputs move through nodes.

### Workflow patterns

| Pattern | How it works | Use when |
|---|---|---|
| **Sequential** | Fixed step-by-step path, each node passes its output to the next | Pipelines: validate, enrich, respond. Predictable, a good starting point |
| **Human-in-the-loop** | Pauses, asks a question, waits for a response, then resumes | Approvals, confirmations, missing context |
| **Group chat** | Control shifts dynamically between agents based on context, rules or intermediate results | Specialized agents collaborating on complex or multi-domain requests |

### Node types (visual designer)

Start from a blank canvas or a predefined pattern. **Workflows are not saved automatically**, so save regularly.

| Node | Purpose |
|---|---|
| **Invoke** (agent) | Calls an agent from the project or creates one. Returns free text or **structured output** (JSON) |
| **Flow** | **If/Else** (branch on a condition), **Go To** (jump to another node), **For Each** (loop over a list) |
| **Data transformation** | **Set Variable**, **Reset Variable**, **Parse value** (extract from structured output or convert formats) |
| **Basic chat** | Sends messages or asks the user a question, usually paired with a variable that captures the answer |
| **End** | Ends the workflow, optionally returning a result or status |

(The knowledge check calls the Invoke node an "agent node".) **Variables** are shared state across nodes.

### Adding agents

- Insert an **Invoke agent** node: reference an existing agent or create a new one in place. Its editor configures **tools, knowledge bases, memory and guardrails**.
- The workflow passes context (user input, variables) to the agent and gets a response back.
- Agents are **reusable across workflows** (for example one categorization agent in many workflows, with different resolution agents). Separation of concerns.
- **Structured output:** define a response format (**JSON schema**) in the **Parameters on the Details tab** of the Invoke editor. Predictable output is what drives routing and variable assignment.
- **Store the output in a variable** in the **Action settings** of the Invoke node, then use it in conditions, branches or as input to other agents.

### Power Fx

Low-code, Excel-like language: the "glue" for data, conditions and loops.

- **System variables:** workflow or conversation context (last message, user info). **Local variables:** data created during the run, referenced as `Local.Name`.
- **Conditions** in If/Else, **loops** in For-Each (process many tickets without duplicating nodes).

| Purpose | Example |
|---|---|
| Upper / lower case, length | `Upper(Local.Input)`, `Lower(...)`, `Len(...)` |
| Condition (true/false) | `Local.Confidence > 0.8` |
| If/Else value | `If(Local.Confidence > 0.8, "Proceed", "Escalate")` |
| Sum | `Sum([10, 20, 30])`, `Sum(Local.ItemList, Amount)` |
| Count items | `Count(Local.ItemList)` |
| Blank / empty check | `IsBlank(Local.Input)`, `IsEmpty(Local.ItemList)` |
| Apply to each item | `ForAll(Local.ItemList, Upper(Name))` |
| Join text | `Concatenate(Local.FirstName, " ", Local.LastName)` |

**Typical escalation:** an agent returns a confidence score as structured output, an If/Else node tests it with Power Fx, and low confidence goes to a human.

### Maintaining workflows

- **Two views, always in sync:** visual canvas (understanding, tracing, collaboration) and **YAML** (advanced configuration, source control).
- **Versioning:** every save creates a new **immutable version**. Review, compare, **roll back**.
- **Notes:** attach notes to nodes or sections to explain decisions and variables.
- **Best practices:** remove unused or redundant nodes, handle structured outputs consistently, document with notes, use version history to validate updates.

### Using a workflow in code

- Design in the portal (it generates the YAML). The saved workflow is invoked **by name**. You can also download the YAML into your codebase.
- Uses `AIProjectClient` and the OpenAI-compatible client, with the **same pattern as invoking an agent**:

```python
conversation = openai_client.conversations.create()
stream = openai_client.responses.create(
    conversation=conversation.id,
    extra_body={"agent": {"name": workflow_name, "type": "agent_reference"}},
    input="Users can't reset their password from the mobile app.",
    stream=True,
)
```

- `input` can be a question, a ticket description, a data payload or an empty string.
- **Streaming events:** `response.completed` (finished, final response) and `response.output_item.done` (an item such as a workflow action finished, `ItemType.WORKFLOW_ACTION` with `action_id` and `status`). Or skip streaming and wait for the final response.
- **Human-in-the-loop in code:** the workflow pauses, and your app **sends another message to the conversation** with the requested input to resume.
- **Uses:** web apps, APIs/microservices, batch processing, automated testing in CI/CD, custom UIs.

### Knowledge check answers

- Node type that invokes an AI agent: **the agent (Invoke) node**.
- Handle multiple tickets without duplicating nodes: **For-Each node**.
- Structured agent outputs: **they provide predictable data that can be stored in variables, evaluated with conditions and trigger workflow steps**.

### Module 6 takeaway

Workflow = nodes + variables + Power Fx, designed visually and stored as versioned YAML. Structured (JSON schema) agent output stored in a variable drives If/Else routing, For-Each handles many items, and human-in-the-loop pauses cover low confidence. In code, call the workflow by name as an `agent_reference` through the Responses API.

---

## Module 7: Develop an Azure AI agent with the Microsoft Agent Framework SDK

**Goal:** connect to a Foundry project, create Foundry agents with the Microsoft Agent Framework, and give them tool functions.

### What the Microsoft Agent Framework is

- The **next generation of both Semantic Kernel and AutoGen**, built by the same teams.
  - From **AutoGen:** simple agent abstractions.
  - From **Semantic Kernel:** enterprise features (session-based state management, type safety, middleware/execution filters, telemetry).
  - **New:** **graph-based workflows** for explicit multi-agent orchestration.
- Every agent derives from one **`Agent` base class**, so the interface is the same whatever model provider you use.

**Building blocks (composable, use alone or together)**

| Feature | Description |
|---|---|
| **Model clients** | One unified interface to many AI providers |
| **Agent session** | Native state management, persistent context across turns |
| **Context providers** | Plug-and-play memory that surfaces relevant information to agents |
| **Function tools** | Custom functions registered with the agent, **schema generated by the framework** |
| **MCP clients** | Built-in MCP support, dynamic tool discovery at runtime |
| **Middleware** | Hooks to intercept, log or modify agent actions before and after execution |
| **Workflow orchestration** | Graph-based: sequential, concurrent, group chat, **handoff** |

**Every agent supports:** function calling, multi-turn conversations (local or service-provided history), **structured outputs** (type-safe, schema-validated), streaming responses, service-provided tools (code execution, file search, web search, where the provider supports them).

### Providers and chat history

- **Foundry Agent Service is the recommended provider for production.** Its key differentiator is **service-side chat history**: the session persists across turns automatically, no manual state handling.
- Switching provider only changes the **client configuration**, not the agent logic.

| Provider | Service chat history |
|---|---|
| Foundry Agent Service | **Yes** |
| Azure OpenAI Responses | **Yes** |
| OpenAI Responses | **Yes** |
| Azure OpenAI Chat Completion | No |
| OpenAI Chat Completion | No |
| Anthropic Claude, Amazon Bedrock, GitHub Copilot, Ollama | No |

Pattern: **Responses = service history, Chat Completion = no service history** (same stateful vs stateless idea as P1 m3).

### Creating a Foundry agent (5 steps)

1. **Foundry project:** you need a project with a deployed model. Two inputs: **project endpoint** (URL) and **model deployment name**.
2. **Authentication:** Azure credentials, usually **`DefaultAzureCredential`** (Azure CLI in development, managed identity in production). No keys or connection strings in code.
3. **Initialize the Foundry chat client** (credential + endpoint + model). It is the bridge to the Agent Service and handles authentication, request routing and service-side session management.
4. **Create the agent:** **instructions** (system prompt: role, goals, constraints) and optional **tools**. The framework registers the tools and generates their schemas.
5. **Open a session and run the agent:** the session holds the conversation state. The run method processes the prompt, coordinates tool calls and returns the response.

**Class names in the knowledge check (older SDK naming):**

| Name | Role |
|---|---|
| **`AzureAIAgentClient`** | The client, the connection to the Foundry project |
| **`ChatAgent`** | The agent: instructions + tools |
| **`AgentThread`** | **Holds the conversation state and stores the messages.** The lesson text calls this the "session" |

### Multi-turn conversations

- One run call = one exchange (one user message, one response). The **session** gives memory across turns.
- **Foundry (service-side history):** history lives in the service, so a conversation continues across requests **even if your app restarts or scales out** to several instances.
- **Local history** (providers without service history): kept in memory in the session object, lost on restart. Fine for short-lived or stateless apps.

### Non-streaming vs streaming

| | Non-streaming | Streaming |
|---|---|---|
| Behavior | Run waits and returns the **complete response object** | Run returns a stream you **iterate asynchronously**, partial updates as generated |
| Use when | Simplest pattern, no incremental display needed | User-facing UIs where progressive output improves the experience |

Both expose a **`text`** property aggregating all text output.

### Tools

Without tools an agent only generates text. Two categories:

**1. Service-provided (hosted) tools:** enabled in the agent configuration, the provider executes them.

| Tool | What it does |
|---|---|
| Code Interpreter | Runs Python in a sandbox |
| File Search | Searches uploaded documents |
| Web Search | Up-to-date internet information |
| **Hosted MCP tools** | MCP servers invoked directly by the provider runtime |
| Azure AI Search | Queries a search index through a Foundry connection |
| **Foundry Toolboxes** | Named, **versioned** bundles of hosted tool configurations managed in a Foundry project |

Some tools (Azure AI Search, Bing Grounding, SharePoint) are in preview or experimental and may have limited support on other providers.

**2. Custom function tools:** any Python logic (internal APIs, databases, calculations). Pass the function **directly when creating the agent**. The framework inspects its signature and generates the schema. Two ways to describe it:

| Approach | How |
|---|---|
| **Type annotations** | `Annotated` type with a description on each parameter. The **docstring is the tool description** |
| **`@tool` decorator** | Set the tool's **name and description** as decorator arguments (full control). Optionally an explicit schema with a **Pydantic model** |

The framework runs the function when the model asks and returns the result to the model before the final answer.

- **Multiple tools:** pass a **list of functions**. The model picks the right one, **no routing code**, based on the descriptions.
- **Tool approval:** with approval mode on, the agent **pauses and asks for confirmation** before calling the function. For irreversible, expensive or sensitive actions. Set **per tool** with the **`approval_mode`** parameter of `@tool`.
- **Agent as a tool:** turn an inner agent into a function tool and give it to an outer agent that delegates to it (specialists plus a coordinator). Covered in the multi-agent module.

**Best practices for custom tools**
- Clear descriptions (what it does and when to use it): the model's choice depends entirely on them.
- Annotate every parameter.
- Return meaningful, structured data.
- Keep each tool focused on **one thing**.
- Handle errors by **returning an informative error message**, not raising an exception, so the model can respond helpfully.

### Knowledge check answers

- Steps to create a Foundry agent: **create an `AzureAIAgentClient`, define a `ChatAgent` with instructions and tools, and create an `AgentThread` for conversations**.
- Component that manages conversation state and stores messages: **`AgentThread`**.
- Add custom functionality: **create Python functions with proper type annotations and descriptions, then pass them to the `ChatAgent`'s `tools` parameter**.

### Module 7 takeaway

Agent Framework = Semantic Kernel + AutoGen, one `Agent` base class over many providers. With Foundry (the recommended provider) the session keeps history on the service side. Client holds the connection, agent holds instructions and tools, thread/session holds the conversation. Tools are hosted (Code Interpreter, File Search, Web Search, MCP, AI Search, Toolboxes) or your own Python functions described by annotations or `@tool`, with `approval_mode` for human approval.

---

## Module 8: Orchestrate a multi-agent solution using the Microsoft Agent Framework

**Goal:** know why and when to use several agents in one conversation, and choose between the five orchestration patterns.

### Why multi-agent

- A task can be larger than one agent handles well. Example: DevOps with four agents (Monitoring > Root Cause Analysis > Automated Deployment > Reporting).
- Benefits: distinct **skills/roles** per agent, **combined outputs** improve decisions and accuracy, coordinated steps that build on each other, **dynamic routing** by context or rules. Also scalability and redundancy.
- The framework is an open-source SDK. Core concepts: **agents**, **agent orchestration**, **chat clients** (provider abstraction through `BaseChatClient`), **tools** (custom functions plus Code Interpreter, File Search, Web Search), **conversation management** (`AgentSession`, message roles **USER, ASSISTANT, SYSTEM, TOOL**).
- It supports multi-agent collaboration **and** human-in-the-loop. One unified interface for all patterns, so you can switch pattern without rewriting agent logic.

### Workflows (the building blocks)

A **workflow** = structured sequence of steps with one or more agents plus other components. It gives control over execution, supports multi-agent orchestration and **checkpointing** (save and resume state).

**Executors:** the workers. Receive input messages, act, produce output. Can be an **AI agent or custom logic**.

**Edges:** how messages flow between executors.

| Edge | Behavior | Example |
|---|---|---|
| **Direct** | One executor to the next in sequence | Gather input > process booking |
| **Conditional** | Fires only if a condition is met | No rooms > suggest other dates |
| **Switch-case** | Routes to different executors by predefined conditions | VIP customers > premium executor |
| **Fan-out** | One message to **multiple** executors at once | Request to flight agent and hotel agent |
| **Fan-in** | **Combines** messages from several executors into one | Summary executor builds the itinerary |

**Events (observability and debugging):**

| Event | When |
|---|---|
| `WorkflowStartedEvent` | Execution begins |
| `WorkflowOutputEvent` | Workflow produces an output |
| `WorkflowErrorEvent` | An error occurs |
| `ExecutorInvokeEvent` | An executor starts a task |
| `ExecutorCompleteEvent` | An executor finishes |
| `RequestInfoEvent` | An external request is issued |

### The five patterns at a glance

| Pattern | Idea | Use for |
|---|---|---|
| **Concurrent** | Same task broadcast to many agents at once, results collected independently | Parallel analysis, independent subtasks, ensemble, voting |
| **Sequential** | Fixed pipeline, each output feeds the next | Step-by-step workflows, progressive refinement |
| **Handoff** | Control transfers between agents by context or rules, **one agent at a time** | Escalation, fallback, expert routing, customer support |
| **Group chat** | Shared conversation (optionally with a human), a **chat manager picks who speaks next** | Brainstorming, collaborative problem solving, consensus, maker-checker |
| **Magentic** | **Manager plans, delegates and adapts**, keeps a task ledger | Complex, open-ended problems where the solution path evolves |

**Unified flow (same for every pattern):**
1. **Define your agents** and describe their capabilities (**first step**).
2. Select and create the orchestration pattern (optionally add a manager agent).
3. Optionally configure callbacks or transforms for input/output handling.
4. Start a runtime to manage execution.
5. Invoke the orchestration with your task.
6. Retrieve results asynchronously (non-blocking).

**Common build steps (concurrent, sequential, group chat):** create a chat client (for example `AzureOpenAIChatClient`) > create agents with `create_agent` (name and instructions) > use the matching **Builder** with `participants()` then `build()` > run the workflow > read results from the events (`get_outputs()`, or `WorkflowOutputEvent` when streaming with `run_stream`).

### Concurrent orchestration

- All agents work on the **same task at the same time**, independently. They **don't share results with each other**. Results are usually combined, but each agent can also produce its own separate result (call tools, update data stores).
- Either call **all** registered agents every time, or **choose** which to run per task.
- **Use when:** tasks can run in parallel, different specialized views (technical, business, creative) on one problem. Examples: brainstorming, **ensemble reasoning**, voting/consensus (**quorum**), speed matters.
- **Avoid when:** agents must build on each other's work or need ordered shared context, strict sequence or repeatable results, **quota limits** make parallel runs impossible, agents can't safely change shared data at the same time, no way to resolve **conflicting results**, combining results is too complex or lowers quality.
- **Builder:** `ConcurrentBuilder`, run with `run`. The output holds each agent's response with **author name and content**.

### Sequential orchestration

- A **pipeline**: each agent's output is the next agent's input. The order is **fixed and decided beforehand**, agents don't decide what happens next.
- **Use when:** ordered steps where each depends on the previous, each stage adds something the next needs, gradual improvement (draft > review > polish), you can handle a failure in any step.
- **Avoid when:** stages can run independently in parallel, one agent can do it all, early stages may fail with no way to stop downstream processing, agents need dynamic collaboration, the workflow needs **iteration, backtracking or dynamic routing**.
- **Builder:** `SequentialBuilder`, run with `run_stream`, loop over events for `WorkflowOutputEvent`. The final result is the **complete conversation** showing each agent's contribution.

### Group chat orchestration

- Agents (and optionally a **human**) in one shared conversation. A **central chat manager** decides which agent responds next and when to ask for human input. Agents usually **contribute to the conversation, they don't directly change running systems**.
- **Use when:** spontaneous or guided collaboration, **maker-checker loops**, real-time human oversight, a **transparent and auditable** conversation (single thread). Examples: brainstorming, debate and consensus, cross-disciplinary problems, quality control, content creation plus review.
- **Avoid when:** a simple delegation or linear pipeline is enough, speed matters (discussion overhead), you need a hierarchical or deterministic workflow, the manager **can't tell when the task is done**, too many agents (**keep to three or fewer**).
- **Maker-checker loop:** the **maker** proposes, the **checker** reviews and sends feedback, repeat until satisfactory. Turn-based, managed by the chat manager.
- **Builder:** `GroupChatBuilder` (the lesson's steps 3-6 are copy-pasted from concurrent, but here the manager picks the speaker each turn).
- **Custom manager:** extend **`GroupChatManager`** to control how results are filtered/summarized, how the next agent is selected, when to ask for user input, when to end.
- **Manager call order each round:**
  1. `should_request_user_input` (human input needed before the next agent?)
  2. `should_terminate` (for example max rounds reached)
  3. `filter_results` (if ending: summarize or process the final conversation)
  4. `select_next_agent` (if continuing: pick the next speaker)

### Handoff orchestration

- Agents **transfer control** to the agent with the right expertise, based on task context or user request. Fits when the best agent **isn't known upfront** or requirements become clear during processing. **One agent at a time**, full handoff (unlike parallel patterns).
- **Use when:** specialized knowledge or tools but number/order of agents can't be set in advance, expertise needs emerge dynamically, multi-domain problems with sequential specialists, you can define clear signals for when and to whom to transfer.
- **Avoid when:** agents and order are **known and fixed**, routing is simple and rule-based, poor routing would frustrate users, operations must run at the same time, **infinite handoff loops** or excessive bouncing are hard to avoid.
- **Implemented as a "control workflow"** (a classifier agent, then a switch-case routes to handlers):
  1. **Data models and chat client:** **Pydantic** models for structured JSON responses, simple data classes between steps, agents configured with **`response_format`** for structured output.
  2. **Executors:** input storage (saves input to shared state, forwards to the classifier), transformation (JSON response to typed routing object), one **handler** per classification outcome (with guard conditions).
  3. **Routing logic:** condition-checker factory functions, conditions used with **`Case`** objects in **switch-case edge groups**. **Always include a `Default` case** as fallback.
  4. **Assemble:** `WorkflowBuilder` connects executors with regular edges, adds the switch-case group (**first matching case wins**, else default), and a terminal executor yields the final output.

### Magentic orchestration

- General-purpose pattern for **complex, open-ended tasks**. A dedicated **Magentic manager** decides which agent acts next from the evolving context, progress and agent capabilities. It keeps shared context, tracks progress and adapts in real time.
- Builds a dynamic **task ledger** (goals, subgoals, execution plans). It focuses as much on building and **documenting the approach** as on the final answer.
- **Use when:** no predetermined solution path, input from several specialists is needed, a **documented plan for human review** is wanted, agents have tools that act on external systems, a dynamically built plan adds value before running.
- **Avoid when:** fixed or deterministic path, no need for a ledger/plan, a lighter pattern is enough, **speed is the priority** (it emphasizes planning over fast execution), frequent stalls or loops are expected.
- **Build:** define specialized agents (`ChatAgent`) > async **event callback** (orchestrator messages, streaming updates, agent messages, final result) > **`MagenticBuilder`** with participants, callback in streaming mode and the **standard manager** (uses a chat client for planning and progress tracking; parameters: **max round count, stall count, reset count**) > `run_stream` > loop over events for `WorkflowOutputEvent`.

### Choosing a pattern

| Situation | Pattern |
|---|---|
| Same task, several independent views, in parallel | Concurrent |
| Fixed ordered steps, each refines the last | Sequential |
| Best agent unknown upfront, route to an expert | Handoff |
| Discussion, debate, maker-checker, human oversight, audit trail | Group chat |
| Open-ended, plan must be built and documented | Magentic |

### Knowledge check answers

- First step in the unified orchestration workflow: **define your agents and describe their capabilities**.
- Brainstorming and collaborative problem solving: **Group Chat**.
- Dynamically transfers control between agents by context or rules: **Handoff**.

### Module 8 takeaway

Orchestration patterns share one interface (define agents, pick pattern, run, read results asynchronously). Concurrent = parallel and independent, sequential = fixed pipeline, handoff = one expert at a time with dynamic routing, group chat = manager-led discussion (maker-checker, human in the loop), Magentic = manager plans with a task ledger for open-ended problems. Workflows are built from executors and edges (direct, conditional, switch-case, fan-out, fan-in) and emit events for observability.

---

## Module 9: Discover Azure AI Agents with A2A

**Goal:** understand the Agent-to-Agent (A2A) protocol: how an agent describes itself, handles requests, is hosted and is called by a client.

### What A2A is

- A **standard protocol for agents to discover, communicate and collaborate** with each other, including remote or distributed agents and agents from different vendors or platforms. Agents share context, invoke each other's capabilities and exchange information securely.
- Example: a **routing agent** sends the request to a title agent, passes the title to an outline agent and returns the outline to the user.

**Advantages**

| Advantage | Meaning |
|---|---|
| Enhanced collaboration | Agents from different vendors and platforms work together across disconnected systems |
| **Flexible model selection** | **Each A2A agent chooses its own LLM** (optimized or fine-tuned per agent), unlike some MCP scenarios that rely on a single LLM connection |
| **Integrated authentication** | Authentication is built into the protocol |

### Agent Skill and Agent Card

**Agent Skill:** one capability the agent can perform (a building block).

| Element | Meaning |
|---|---|
| ID | Unique identifier |
| Name | Human-readable name |
| Description | What the skill does |
| Tags | Keywords for categorization and discovery |
| Examples | Sample prompts or use cases |
| Input/Output modes | Supported formats (text, JSON) |

**Agent Card:** the agent's **digital business card**, a structured document a routing agent or client retrieves to **discover** what the agent can do and how to talk to it. It holds **metadata, not credentials** (no API key).

| Element | Meaning |
|---|---|
| Identity | Name, description, version |
| **Endpoint URL** | Where the agent's A2A service is reached |
| Capabilities | Supported A2A features, such as **streaming** or **push notifications** |
| Default input/output modes | Main media types |
| **Skills** | List of skills other agents can invoke |
| Authentication support | Whether credentials are required |

Once the card is published, other agents and clients discover the agent automatically, requests are routed to the right skill, and responses come back in supported formats.

### Agent Executor

The bridge between the A2A protocol and the agent's own business logic. The **`AgentExecutor`** interface handles all incoming requests.

- **Responsibilities:** execute tasks for users or other agents, stream responses or send single messages, handle cancellation if supported.
- **Two operations:**

| Operation | What it does |
|---|---|
| **`execute`** | Processes the request and generates the response. Reads request details, sends results through the **event queue** (messages, task updates or artifacts) |
| **`cancel`** | Cancels an ongoing task. Simple agents may just say it is not supported |

- Uses **`RequestContext`** (what came in: user input, task context) and **`EventQueue`** (how results go back).
- **Flow (Hello World agent):** helper class holds the logic > executor receives the request and calls it > wraps the result as an event on the event queue > the routing mechanism returns it to the requester.

### Hosting an A2A server

Hosting makes the agent reachable over **HTTP**: it exposes the Agent Card, forwards requests to the executor and manages task lifecycles (streaming, stateful interactions).

| Component | Role |
|---|---|
| **Agent Card** | Capabilities, skills, modes. Served at the standard endpoint **`/.well-known/agent-card.json`**. Can have multiple versions or an **extended card for authenticated users** |
| **Request Handler** | Routes requests to the executor's `execute` or `cancel`. Manages the task lifecycle through a **Task Store** (tracks tasks, streaming data, resubscriptions). **Even simple agents need a task store** |
| **Server Application** | Web framework (**Starlette** in Python) plus an **ASGI server (Uvicorn)** that listens on a network interface and port |

**Setup:** define skills and Agent Card > create the request handler (executor + task store) > create the server application (card + handler) > start it with Uvicorn.

### Connecting a client

- The client needs the server's **base URL**, fetches the **Agent Card from the well-known endpoint**, is initialized with the card, then sends messages and interprets responses.
- **Request types:**

| | Non-streaming | Streaming |
|---|---|---|
| Behavior | Send a message, wait for the complete response | Receive responses incrementally while the agent works |
| Use when | Simple interactions, a single response | Long-running tasks, real-time updates |

- Requests usually carry a **`role`** (for example `user`) and the message content, and each request should have a **unique ID**.
- **Response types:** **direct messages** (immediate text or structured output) or **task-based responses** (a task object for an ongoing job, with follow-up calls to check status, get results or cancel). A client must handle both.

### Knowledge check answers

- Primary role of an A2A server: **it routes requests between clients and connected agents**. (Not: it runs the business logic, which is the executor's job.)
- Agent Executor: **processes incoming requests and generates responses or events**.
- Agent card: **provides metadata about the agent, such as its capabilities and available functions**.

### Module 9 takeaway

A2A = discovery plus communication between agents. An agent declares **skills**, publishes them in an **Agent Card** at `/.well-known/agent-card.json`, runs logic in an **Agent Executor** (`execute`/`cancel`, with `RequestContext` and `EventQueue`), and is served over HTTP by a **request handler + task store + Starlette/Uvicorn app**. A client reads the card, then sends streaming or non-streaming requests and handles message or task responses.
