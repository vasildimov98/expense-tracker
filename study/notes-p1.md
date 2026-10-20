# P1 notes: Develop generative AI apps in Azure

## Module 1: Plan and prepare to develop AI solutions on Azure

### Introduction and "What is AI?"

- Before starting development, consider which tools, services and frameworks are available, and which best practices and principles to follow. Plan before you act.
- Building an AI solution is more than calling an AI model endpoint. You also have to think about the models, AI services, prompts, code, tools and the platform that brings them all together.
- "AI" covers a wide range of software capabilities:
  - **Generative AI and agents:** generate responses from natural language. Mostly used like a chat, with prompts and responses.
  - **Natural language processing (NLP):** extracts information from large amounts of text, for example statistical analysis of documents or classifying tasks.
  - **Speech:** AI can now recognize speech and talk with the user live through audio. It also handles background noise and similar problems much better.
  - **Computer vision:** AI can accept, interpret and process images, videos and even a live camera feed. For example, it can see what is in your grocery cart automatically, so each item no longer needs a barcode scan.
  - **Information extraction:** AI is very good at pulling information out of large documents and removing the noise, so you can focus on what is important.

### NLP vs generative AI (cleared up in discussion)

- **NLP** is the long-standing field of making computers understand and process human language, using statistical and semantic models. It is a field, not one program.
- **Generative AI** is based on large language models (LLMs). LLMs evolved from NLP.
- **LLM:** a very large neural network trained on huge amounts of text to predict what comes next. That training is what lets it generate original responses and perform many NLP tasks.
- **LLM vs a chat assistant (ChatGPT, Gemini, Claude):** the LLM is the model. The chat assistant is an application built around it (chat window, hidden instructions, safety rules, sometimes tools). In Azure/Foundry you call the model endpoint from code instead of using a chat window.
- **Why classic NLP is still useful (course text):** some text-analysis jobs benefit from statistical NLP techniques built on term-frequency algorithms, and from task-specific models for text classification, sentiment analysis and summarization. They are usually cheaper, faster and more predictable than an LLM, for example when classifying a million emails by sentiment.
- **Exam link:** choosing the right tool for the task is a recurring theme, and the answer is not always "use the LLM".

### Microsoft Foundry

**What it is:** a platform for AI development on Azure. For a simple AI solution you could skip it, but it gives you built-in shared space for management and project organization, and it is the recommended way to build scalable AI solutions.

**Two ways to use it:** the Microsoft Foundry portal (UI) and the SDK (to build AI solutions in code).

**Project:** everything to do with resource connections, data, code and AI tools is managed inside a project.
- Each project belongs to a single Microsoft Foundry resource in Azure. The resource provides compute, data storage, AI tools and other services.
- One resource can support one or more projects, and one of them is the default project.
- The project home page shows what a client app needs: the **API key**, the **project endpoint** and the **Azure OpenAI endpoint**.

**What developers manage in a project**
- **Models:** access to a catalog of models through the Azure OpenAI endpoint and SDK. You connect to and interact with the models through that endpoint.
- **Agents:** a named AI configuration that combines an LLM, instructions and tools into an autonomous AI entity that can automate tasks and collaborate with users and other agents. You develop and deploy them with Foundry Agent Service.
- **Tools:** the tools an agent uses. They can be built-in (web search, code interpreter) or custom and third-party tools connected through the Model Context Protocol (MCP). The project also gives you Foundry Tools for common tasks: text analysis, speech recognition and synthesis, translation and content understanding. These are hosted in the Foundry resource linked to your project.
- **Knowledge:** agents can use tools to connect to knowledge stores and use the data in them to give context to prompts. Foundry IQ gives a project one central, MCP-based knowledge connection for many sources. My understanding: I can give my agent my own knowledge so it works with the specific context of my solution. (Confirmed in discussion: yes, that is the idea. See "Foundry IQ" below.)

**Most AI development starts in a Foundry project, where you can**
- find, compare, deploy and test models;
- create and test agents;
- create MCP connections to tools and Foundry IQ knowledge sources;
- explore and test Microsoft Foundry tools;
- manage resource configuration and user access;
- find the endpoints and keys client applications need.

### Explained in discussion

**Agent vs model**
- A **model** takes input and returns output. It has no goal, no memory between calls, and no ability to act on its own. Example: you send a bank description and the model answers "Groceries".
- An **agent** is a model plus **instructions** (its role and rules) plus **tools** (things it can call). It can decide what to do, call tools, and use the results. Example: "How much did I spend on groceries last month?" The agent decides to call your `get_spending_by_category` function, reads the result, and answers.
- Short version: the model is the brain, the agent is the brain with a job description and tools. In Foundry, you can build a **prompt agent** (declarative: instructions, model and tools set in the portal or SDK, and Foundry runs it) or a **hosted agent** (your own code, packaged and run by Foundry).

**Model Context Protocol (MCP)**
- An open standard for how AI agents connect to tools and data sources. It is often described as "USB-C for AI tools".
- A tool provider runs an **MCP server** that says "here are my tools, their names and what inputs they take". An agent (the **MCP client**) connects, asks which tools exist, and calls them. The same tool then works with any agent that supports MCP, instead of custom integration code for each one.
- Foundry IQ and the Azure Language and Speech MCP servers (later modules in P2 and P3) are examples.

**Foundry IQ:** a shared knowledge layer for a project. You connect your knowledge sources once, and agents reach them through one MCP-based connection. The agent retrieves relevant content and uses it to answer, which is the RAG idea (retrieval-augmented generation).

**New Foundry vs Foundry classic** (from Microsoft's "What is Microsoft Foundry?" page, checked 2026-10-20)

| | Classic (previous) | New (current) |
|---|---|---|
| Brand | Azure AI Studio / Azure AI Foundry | Microsoft Foundry |
| Services name | Azure AI Services | Foundry Tools |
| Portal | Foundry (classic) | Foundry |
| Project type | Hub-based project (hub + Azure OpenAI + Azure AI Services) | Foundry project under a single Foundry resource |
| Agent API | Assistants API (Agents v0.5/v1) | Responses API (Agents v2) |
| API versioning | Monthly `api-version` parameters | Stable v1 routes (`/openai/v1/`) |
| SDKs and endpoints | Several packages and 5+ endpoints | One project client (`azure-ai-projects` 2.x) and `OpenAI()` against one project endpoint |
| Terms | Threads, Messages, Runs, Assistants | Conversations, Items, Responses, Agent Versions |

- Hub-based projects still work and live in the classic portal, but Microsoft says new investment is focused on Foundry projects in the new portal. The module's note means: it teaches the new architecture, the portal is mid-transition, and some tasks may not yet exist in the new portal.
- **Exam angle (to verify):** the study guide talks about "Foundry projects", agents and Foundry Tools, so the new architecture is the one to learn. When you read older tutorials or videos, expect the classic names (Azure AI Studio, Assistants API, hub) and translate them with this table.

### Foundry Tools

Most modern AI solutions rely heavily on AI models and agents, but it is still useful to use ready-made functionality for common AI tasks:

- **Azure Language:** extract and summarize text.
- **Azure Speech:** speech to text and text to speech.
- **Azure Translator:** translation.
- **Azure Document Intelligence:** extract fields from complex documents.
- **Azure Content Understanding:** extract data from forms and documents, images, and video and audio streams.

These tools help you build cost-effective solutions without relying heavily on expensive models and agents.

### Developer tools and SDKs

- On Azure you can build AI applications in IDEs such as Visual Studio and Visual Studio Code.
- You can install extensions such as the Microsoft Foundry Toolkit, which lets you work with your code and Foundry at the same time, so you can build your AI solution from code to a Foundry project and back.
- You can also use Copilot to boost your productivity. *(This note ended with a colon. Add what the module says about it if you want to finish the thought.)*

### Responsible AI

- Responsible AI should be a developer skill, not just a policy.
- Always think about the impact your software can have on its users and on society, including how it will be used responsibly. This matters even more now that we embed AI in software.
- AI is probabilistic, and it depends on the data it was trained on. Never trust its output blindly. It can make life easier, but it can also cause harm.

**Microsoft's six principles for responsible AI**

| Principle | Idea | Example from the course |
|---|---|---|
| **Fairness** | AI systems should treat all people fairly, with no bias based on gender, ethnicity or similar factors. Tooling alone is not enough: consider fairness from the start, check that training data represents everyone affected, and evaluate performance for subgroups throughout development. | A loan-approval model must not favor or disadvantage groups of applicants. |
| **Reliability and safety** | AI systems should perform reliably and safely. Test and manage deployment rigorously, and allow for the probabilistic nature of models by applying sensible thresholds to confidence scores. | An autonomous vehicle, or a model that recommends prescriptions: unreliability can risk lives. |
| **Privacy and security** | AI systems should be secure and respect privacy. Models use large amounts of data that may contain personal details, and in production they keep receiving new data, so safeguard data and customer content. | Training data with personal details; new data used for predictions in production. |
| **Inclusiveness** | AI should empower everyone and engage people, regardless of ability, gender, sexual orientation, ethnicity or other factors. Include input from a diverse group of people in design, development and testing. | A design and test process that includes many different kinds of users. |
| **Transparency** | AI systems should be understandable. Tell users the system's purpose, how it works and its limitations, including factors affecting accuracy and confidence scores. If personal data is used, say how it is used, kept, and who can access it. | A facial recognition system that must explain how images of people are used and retained. |
| **Accountability** | People are accountable for AI systems. Developers are responsible for the models they train and validate and the logic built on their predictions. Work within a governance framework with clear responsible and legal standards. | Even a system that seems autonomous still has people responsible for it. |

**Memory aid:** Fairness, Reliability and safety, Privacy and security, Inclusiveness, Transparency, Accountability (FRPITA).

### Module 1 takeaway

The main takeaway of this module is that building an AI solution is not just getting access to an AI model. It is choosing the right capability, the right service, the right workflow and the right safeguards. Foundry is the practical center of gravity for a project, but none of that replaces sound engeneering judgement.
