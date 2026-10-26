# P3 notes: Develop natural language solutions on Azure

## Module 1: Analyze text with Azure Language in Foundry Tools

**Goal:** use the Azure Language API (Python SDK `azure-ai-textanalytics`) to detect language, recognize named entities and extract or redact PII.

### Azure Language basics

| Capability | What it does |
|---|---|
| Language detection | Determines the language a text is written in |
| Named entity recognition (NER) | Finds references to people, locations, time periods, organizations and more |
| PII extraction | Identifies and redacts personal details |

- **Deprecated, kept only for existing apps:** sentiment analysis, summarization, key phrase extraction and other older tasks.
- **Resource:** a **Microsoft Foundry resource** in your subscription. Call its endpoint from REST (JSON requests) or from an SDK (Python, .NET, JavaScript follow the same pattern).
- **Endpoints:** project endpoint = resource endpoint + `/api/projects/{project_name}`. Project and resource keys are the same. Keys and endpoint are on the Foundry portal home page (resource: Operate > Admin tab).
- **Authentication:**
  - **Key:** `TextAnalyticsClient(endpoint, AzureKeyCredential(key))`.
  - **Microsoft Entra ID (recommended for production):** `TextAnalyticsClient(endpoint, DefaultAzureCredential())`, which uses the default identity of the environment the app runs in.

### Detect language (`client.detect_language`)

- Returns, per document, the primary language (`name`, `iso6391_name`) and a **confidence score from 0 to 1** (closer to 1 = more confident).
- Use cases: stores of text in unknown languages; a chat app that answers in the user's language.
- **Limits:** document under **5,120 characters**; at most **1,000 documents (IDs)** per request. Each document has a unique `id` and its text.
- **Edge cases:**
  - Mixed-language text returns the language with the largest share, with a lower score.
  - Unparseable text (for example encoding problems) returns `(unknown)` and score `0`.

### Extract entities (`client.recognize_entities`)

- Returns a list of entities per document, each with text and **category** (and subcategory): Person, Location, DateTime, Organization, Address, Email, URL, PersonType (for example "CEO").

### Extract PII (`client.recognize_pii_entities(documents, language="en")`)

- Detects names, addresses, phone numbers, email addresses, SSNs, credit card numbers, plus passwords, PIN codes and zip codes.
- Each entity has text, category and confidence score. Optional **confidence threshold** keeps only entities at or above it.
- **Redaction:** `doc.redacted_text` returns the text with PII replaced by asterisks (or a specified character). Use it to remove personal data before sharing feedback, medical or legal documents.
- Note: PII categories are not the same as NER categories. PII is for protecting data, NER is for extracting information.

**Possible lesson errors (flagged):**
- The detect-language unit says a sample JSON payload is shown, but only Python code is shown.
- In the redaction sample, the phone number `555-012-456` (11 characters) is masked with only 8 asterisks. The other masks match the length of the original text.

### Knowledge check

1. Extract key people, places and dates from news articles for indexing: **Azure Language named entity recognition** (not PII extraction, not a regex tool on a generative model).
2. Remove personal details from testimonials before publishing: **Azure Language to find and redact PII entities** (language detection or generating new reviews does not remove PII).

**Takeaway:** Azure Language gives you language detection (score 0-1, under 5,120 chars), NER (people, places, dates) and PII detection with redaction, all through one Foundry resource and `TextAnalyticsClient`, using a key or, better, `DefaultAzureCredential`.

## Module 2: Develop a text analysis agent with the Azure Language MCP server

**Goal:** expose Azure Language capabilities to a Foundry agent through the Model Context Protocol (MCP), test it in the playground and call it from a Python client. The Language MCP server is in **public preview**.

### MCP basics

- **MCP:** open protocol for how AI agents use external tools, data sources and services. Client-server architecture:

| Component | Role |
|---|---|
| Host | The app that runs the agent (Foundry or a custom app) |
| Client | Inside the host; manages connections to MCP servers |
| Server | Exposes tools, resources and prompts the agent can discover and call |

- **Dynamic tool discovery:** on connecting, the agent receives a catalog of tools with descriptions and queries it at runtime. Tools can be added, updated or removed on the server without changing the agent.

### Azure Language MCP server

| Tool capability | Description |
|---|---|
| Language detection | Which language the text is written in |
| Named entity recognition | People, places, organizations, dates, quantities |
| PII redaction | Detects and redacts names, addresses, phone numbers |
| Text Analytics for Health | Medical entities (diagnoses, medications, symptoms) from clinical text |

- Sentiment, summarization and key phrase extraction are deprecated (existing apps only).
- **Endpoint (remote):** `https://{foundry-resource-name}.cognitiveservices.azure.com/language/mcp?api-version=2025-11-15-preview`.
- A **local MCP server** you host yourself also exists (quickstart in the Azure Language samples repo).
- **Tool selection (no routing code needed):** user prompt > agent decides which task(s) > matches the tool descriptions > calls the tool through the MCP server with the input text > server runs the Azure Language capability > agent combines results into a natural-language answer. One prompt can trigger several tools in one turn, each call independent.

### Connect and use it

1. Foundry project + deployed model (for example gpt-4.1) + an agent with instructions.
2. Portal: **Tools** page > **Connect a tool** > **Azure Language in Foundry Tools**. Settings: Foundry resource name; authentication **key-based**; credential header `Ocp-Apim-Subscription-Key` = the Foundry project key (on the project home page). Then **Use in an agent**.
3. **Update the instructions** to tell the agent to use the tool (for example "Use the Azure Language tool to perform text analysis tasks").
4. **Test in the agent playground:**
   - First MCP tool use asks for **approval**: once, or "Always approve all ... tools".
   - The **Logs** pane shows each MCP tool call, its input and its result.

### Client application (Python)

1. `AIProjectClient(project endpoint, DefaultAzureCredential())` (`azure-ai-projects`, `azure-identity`).
2. `openai_client = project_client.get_openai_client()`.
3. `openai_client.responses.create(input=[{"role": "user", "content": prompt}], extra_body={"agent_reference": {"name": "Text-Analysis-Agent", "type": "agent_reference"}})`. The agent is referenced **by name in `agent_reference` inside `extra_body`**.
4. Read `response.output_text`; `response.model_dump_json()` shows which tools were called (for example `extract_named_entities_from_text`, `detect_language_from_text`) with arguments and results.

### Connect the MCP server in code

- `MCPTool(server_label="azure-language", server_url="https://{name}.cognitiveservices.azure.com/language/mcp?api-version=2025-11-15-preview", require_approval="always")` from `azure.ai.projects.models`; pass it when creating the agent.
- `allowed_tools` on `MCPTool` restricts which Language tools the agent may call.

**Possible lesson error (flagged):** the multi-task example ("entities and dates ... and whether it is positive or negative") needs entity recognition plus sentiment analysis, but the text says the agent calls `extract_named_entities_from_text` and `detect_language_from_text`. Language detection does not give sentiment, and sentiment is deprecated and not among the server's listed tools.

### Knowledge check (4/4, all correct)

1. Primary role of the server: **expose Azure Language capabilities as MCP tools for agents** (not training or deploying models).
2. How the agent picks a tool: **it matches the prompt to the tool descriptions received from the MCP server** (not developer routing logic, not server-side routing).
3. Referencing the agent in the Responses API: **agent name in `agent_reference` in `extra_body`** (not an API key header, not the endpoint as `model`).
4. Auth when connecting the server: **key-based, `Ocp-Apim-Subscription-Key`** (not OAuth with certificate, not anonymous).

**Takeaway:** MCP lets the agent discover Language tools at runtime and pick them from their descriptions; you connect the server (portal key-based, or `MCPTool` in code), approve tool use, and call the agent from Python by name via `agent_reference`.

## Module 3: Develop a speech-capable generative AI application

**Goal:** pick a speech-capable model in Microsoft Foundry and use it to transcribe speech to text and synthesize text to speech.

### Use cases

Documenting calls and meetings, captions for videos or presentations, audible interfaces for accessibility, hands-free assistants that read messages aloud.

### Choosing a model

- Find models with the filter and search in the Foundry model catalog (Foundry Models: models from multiple providers, each optimized for different use cases).
- Speech-capable models come from the **gpt-4o family**. Availability varies **by region**: check the regional availability table.

| Direction | Also called | Models |
|---|---|---|
| Audio in, text out | Transcription, speech-to-text | `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-transcribe-diarize` |
| Text in, audio out | Synthesis, text-to-speech | `gpt-4o-tts`, `gpt-4o-mini-tts` |

Memory aid: **transcribe = speech to text**, **tts = text to speech**. Plain `gpt-4o-mini` is a text model and is neither.

### Code pattern (both directions)

Use the **`AzureOpenAI` client** from the OpenAI SDK (`azure_endpoint`, `api_key`, `api_version`, here `2025-03-01-preview`), and pass your **model deployment name** as `model`.

| | Speech-to-text | Text-to-speech |
|---|---|---|
| Call | `client.audio.transcriptions.create(model, file, response_format="text")` | `client.audio.speech.with_streaming_response.create(model, voice, input, instructions)` |
| Input | Audio file opened in binary mode (`"rb"`) | Text in `input`; `voice` (for example `"alloy"`); `instructions` set the tone (for example "upbeat, excited") |
| Output | Transcript text | Audio streamed to a file with `response.stream_to_file(path)` |

### Knowledge check (2/2, all correct)

1. Model that generates text from speech: **`gpt-4o-mini-transcribe`** (not `gpt-4o-mini`, not `-tts`).
2. Model that synthesizes speech from text: **`gpt-4o-mini-tts`** (not `gpt-4o-mini`, not `-transcribe`).

**Takeaway:** in Foundry, `*-transcribe` models do speech-to-text and `*-tts` models do text-to-speech; both are called through the OpenAI SDK `AzureOpenAI` client with your deployment name.

## Module 4: Create speech-enabled apps with Azure Speech in Microsoft Foundry Tools

**Goal:** use the Azure Speech SDK to add speech recognition and speech synthesis to an app, choose audio format and voice, and use SSML for finer control.

### Azure Speech in Foundry Tools

| API | Purpose |
|---|---|
| Speech to text | Speech recognition: the app accepts spoken input |
| Text to speech | Speech synthesis: the app gives spoken output |
| Speech Translation | Translates spoken input into multiple languages |
| Voice Live | Builds AI agents that hold real-time conversations |

- This module covers recognition and synthesis only. Examples use Python (`azure-cognitiveservices-speech`); other SDKs follow the same pattern.
- **Resource:** a **Microsoft Foundry resource**. Authenticate with the resource **key** (REST with JSON, or an SDK).
- **`SpeechConfig`:** the first object you create; holds the connection details: **endpoint (or region) and key**. `SpeechConfig(subscription=KEY, endpoint=ENDPOINT)`. SDK versions before **1.48.2** needed the **region** instead of the endpoint; now either works.
- Endpoint and key are on the Foundry portal home page (resource: Operate > Admin). Resource endpoint = project endpoint without `/api/projects/{project_name}`.

### Speech to text

| Step | Object / method |
|---|---|
| 1. Connection details | `SpeechConfig` (endpoint or region, key) |
| 2. Input source (optional) | `AudioConfig`: default is the **system microphone**; or `AudioConfig(filename=...)` for an audio file |
| 3. Proxy client | `SpeechRecognizer(speech_config, audio_config)` |
| 4. Call the API | For example `recognize_once_async()` (`RecognizeOnceAsync`): one spoken utterance |
| 5. Process the result | `SpeechRecognitionResult` |

- **Result properties:** Duration, OffsetInTicks, Properties, **Reason**, ResultId, **Text**.
- **`Reason` values:**
  - `RecognizedSpeech`: success, `Text` holds the transcription.
  - `NoMatch`: audio parsed but no speech recognized.
  - `Canceled`: an error; check `CancellationReason` in `Properties`.

### Text to speech

| Step | Object / method |
|---|---|
| 1. Connection details | `SpeechConfig` |
| 2. Output device (optional) | `AudioOutputConfig`: default is the **system speaker** (`use_default_speaker=True`); or an audio file; or **null** to process the returned audio stream yourself |
| 3. Proxy client | `SpeechSynthesizer(speech_config, audio_config)` |
| 4. Call the API | `speak_text_async(text)` (`SpeakTextAsync`) |
| 5. Process the result | `SpeechSynthesisResult` |

- **Result properties:** AudioData, Properties, Reason, ResultId.
- **`Reason` values:** `SynthesizingAudioCompleted` = success (`AudioData` holds the audio, already sent to speaker or file depending on `AudioConfig`); `Canceled` = failure, read `cancellation_details` (`CancellationReason.Error` has `error_details`).

### Audio format and voices (set on `SpeechConfig`)

- **Output format:** choose by **file type, sample rate, bit depth**: `speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)`.
- **Voice:** `speech_config.speech_synthesis_voice_name = 'en-US-Brian:DragonHDLatestNeural'`. Voice names encode locale, person name and other details.

### Speech Synthesis Markup Language (SSML)

- XML syntax for more control than plain text. Send with `speak_ssml_async('<speak>...')`.

| SSML can | Example |
|---|---|
| Set a speaking style (neural voices) | "excited", "cheerful" (`mstts:express-as`) |
| Insert pauses or silence | `<break strength="weak"/>` |
| Specify phonemes | Pronounce "SQL" as "sequel" (`<phoneme>`) |
| Adjust prosody | Pitch, timbre, speaking rate |
| Apply say-as rules | Read a string as a date, time, phone number |
| Insert recorded audio | Standard recorded message, background noise |
| Use several voices | A dialog between two `<voice>` elements |

**Possible lesson errors (flagged):**
- The introduction ends with "Available SDK packages include:" and no list follows (probably lost when copying).
- The "Azure Speech in a Foundry resource" unit says the endpoint is used "to call the Azure Language APIs". It should say Azure Speech APIs.
- The text-to-speech unit introduction ends with a dangling colon and nothing after it (a missing screenshot or list).
- The SSML sample dialog calls the voice "Ariana", but the voice is `en-US-AriaNeural`.

### Knowledge check (3/3, all correct)

1. What you need from the Foundry resource for the Speech SDK: **the endpoint and key** (not two keys, not subscription ID and resource group).
2. Object that says the speech input is an audio file: **`AudioConfig`** (not `SpeechConfig`, not `SpeechRecognizer`).
3. Changing the synthesis voice: **set `speech_synthesis_voice_name` on `SpeechConfig`** (not the output format enum, not a filename in `AudioConfig`).

**Takeaway:** the Speech SDK pattern is `SpeechConfig` (endpoint + key, voice, output format) + `AudioConfig` (file or mic/speaker) + `SpeechRecognizer` or `SpeechSynthesizer`; check `Reason` on the result, and use SSML for style, pauses, pronunciation and multiple voices.

## Module 5: Develop a speech agent with the Azure Speech MCP server

**Goal:** expose Azure Speech (speech-to-text and text-to-speech) to a Foundry agent through MCP, test it in the playground and call it from a Python client.

### MCP recap (same as P3 m2)

- MCP = open protocol for agents to use external tools. **Host** (runs the agent) > **client** (manages server connections) > **server** (exposes tools, resources, prompts).
- **Dynamic tool discovery:** the agent gets a tool catalog with descriptions at runtime, and tools can change on the server without changing the agent. No routing code: the agent matches the prompt to the tool descriptions.

### Azure Speech MCP server

| Tool | What it does |
|---|---|
| Speech-to-text (Recognize) | Audio file to text. Formats: WAV, MP3, OGG, FLAC, MP4, M4A, AAC and others. Options: language, **phrase hints**, **profanity filtering**, simple or detailed output |
| Text-to-speech (Synthesize) | Text to an audio file with neural voices (for example `en-US-JennyNeural`, `en-GB-SoniaNeural`). Many languages and voices; WAV, MP3 and other formats |

- Flow: prompt > agent picks the task > matches a tool > calls it with the input (audio file URL or text) > server runs Azure Speech > returns transcribed text or a **link to an audio file** > agent answers in natural language.

### Storage requirements (new compared with the Language MCP server)

- It works with audio files, so it needs an **Azure Storage account with a blob container**.
  - **Text-to-speech:** generated audio is saved to the container; the response contains a link.
  - **Speech-to-text:** transcribes from a **publicly accessible URL**, or from a blob in the container via a **SAS URL**.
- You give the server a **SAS URL** for the container, which lets it read and write files there.

### Prerequisites

- Azure subscription.
- Foundry resource and project in a **supported region** (Contributor or Owner on the resource group). If the Speech MCP tool is missing from the catalog, check the region.
- Storage account with a blob container; your account needs **Storage Blob Data Contributor**.
- **SAS URL** for the container with **read, write, add, create and list** permissions.

### Security

- Authentication is **key-based**: the resource key plus the blob container SAS URL.
- Treat SAS URLs as **secrets**: shortest practical expiry, scoped to one container, never in source code, prompts or chat transcripts. Keep keys and SAS URLs in a secret store, rotate regularly, rotate immediately if exposed.

### Connect and use it

1. **Storage:** create the account, assign yourself Storage Blob Data Contributor, create a container, generate a SAS (Read, Add, Create, Write, List; shortest expiry), copy the SAS URL.
2. **Project and agent:** Foundry project, deployed model (for example gpt-4.1), agent with instructions such as "use the Azure AI Speech tool to transcribe and generate speech".
3. **Connect the tool:** agent > **Tools > Add > Add a new tool > Catalog > Azure Speech MCP Server**. Settings: Foundry resource name; `Ocp-Apim-Subscription-Key` (the project key); **`X-Blob-Container-Url`** (the SAS URL). Select Create.
4. **Playground:** first use asks for approval (or "Always approve all ... tools"). Text-to-speech prompt returns a link to the audio in the container. Speech-to-text prompt takes a public URL or a SAS URL to a blob.
5. **Options go in the prompt:**
   - **Voice:** for example `en-GB-SoniaNeural`.
   - **Language:** for example `es-ES`.
   - **Phrase hints:** domain terms for better accuracy.
   - **Profanity filtering:** `masked`, `removed` or `raw`.

### Client app and code

- **Client (Python):** same pattern as the Language MCP module: `AIProjectClient` (project endpoint + `DefaultAzureCredential`) > `get_openai_client()` > `responses.create(input=[...], extra_body={"agent_reference": {"name": "Speech-Agent", "type": "agent_reference"}})` > `response.output_text` (for text-to-speech it contains the audio link).
- **In code:** `MCPTool(server_label="azure-speech", server_url="https://{foundry-resource-name}.cognitiveservices.azure.com/speech/mcp", require_approval="always")` from `azure.ai.projects.models`, passed when creating the agent. No `api-version` in this URL, unlike the Language one.

**Possible lesson issues (flagged):**
- The portal field is labelled "Bearer (`Ocp-Apim-Subscription-Key`)" but the module and knowledge check describe it as the resource key, not a bearer token.
- The `MCPTool` code sample shows no place for the SAS URL (`X-Blob-Container-Url`); the module only shows it for the portal connection.

### Knowledge check (4/4, all correct)

1. Two core capabilities: **speech-to-text recognition and text-to-speech synthesis** (not translation or summarization, not NER or sentiment).
2. Why storage is needed: **to store input audio files and the audio files the tools generate** (not agent instructions, not tool definition caching).
3. Credentials for the connection: **a Foundry resource key and a SAS URL for a blob container** (not OAuth and managed identity, not a certificate and subscription ID).
4. Choosing a voice through the agent: **include the voice name in the natural language prompt** (not server settings, not an environment variable).

**Takeaway:** the Speech MCP server gives an agent speech-to-text and text-to-speech as tools, needs a blob container plus a SAS URL (a secret) alongside the resource key, and takes voice, language, phrase hints and profanity options from the prompt.

## Module 6: Develop an Azure Speech Voice Live Agent in Microsoft Foundry

**Goal:** use the Voice Live API (Azure Speech in Foundry Tools) for low-latency, real-time speech-to-speech voice agents, configure the session, handle events and use it with a Foundry agent.

### The Voice Live API

- **Low-latency, high-quality speech-to-speech** for voice agents; removes the need to orchestrate several components yourself. Optimized for **Foundry resources**.
- **WebSocket** connection, real-time and bidirectional. **JSON events** manage conversation, audio streams and responses:
  - **Client events** (client to server).
  - **Server events** (server to client).
- **Features:** speech recognition, text-to-speech, **avatar streaming (WebRTC)**, audio processing; formats such as **PCM16 and G.711**; voices from OpenAI or Azure custom voices; built-in **noise reduction and echo cancellation**.

### Authentication

| Method | Detail |
|---|---|
| **Microsoft Entra (keyless, recommended)** | Role **Cognitive Services User** on the user or managed identity. Token scope `https://ai.azure.com/.default` (or legacy `https://cognitiveservices.azure.com/.default`). Sent as `Authorization: Bearer <token>` on the WebSocket connection request |
| **API key** | `api-key` connection header on the prehandshake (**not available in a browser**), or `api-key` query string parameter (encrypted over https/wss) |

### WebSocket endpoints

| Connection | Endpoint |
|---|---|
| Project connection (agent) | `wss://<resource>.services.ai.azure.com/voice-live/realtime?api-version=2025-10-01` |
| Model connection (direct) | `wss://<resource>.cognitiveservices.azure.com/voice-live/realtime?api-version=2025-10-01` |

- Same endpoint for all models. The difference is the required **`model`** query parameter, or **`agent_id` and `project_id`** when using the Agent service.

### Events

| Client events | Server events |
|---|---|
| `session.update`: change session configuration | `session.updated`: confirms the change |
| `input_audio_buffer.append`: add audio to the buffer | `response.done`: response generation finished |
| `response.create`: generate a response via model inference | `conversation.item.created`: new conversation item added |

- Other server events seen in code: `input_audio_buffer.speech_started` / `speech_stopped`, `response.audio.delta` (audio chunk), `response.audio_transcript.done`, `error`.
- **`session.update` is usually the first event** a caller sends, and can be sent again to change settings dynamically. It sets voice type, modalities (text, audio), instructions, audio formats and sampling rate, **turn detection**, temperature, max output tokens.
- **Turn detection:** use **Azure semantic VAD** (`azure_semantic_vad`) for smarter conversational flow; settings include threshold, prefix padding and silence duration.
- **Audio buffer:** **append** (add bytes), **commit** (process for transcription or response), **clear** (remove).
- **Audio quality (`session.update`):** `input_audio_noise_reduction` = `azure_deep_noise_suppression`; `input_audio_echo_cancellation` = `server_echo_cancellation`. Noise reduction improves VAD accuracy and model performance.
- **Avatar:** WebRTC; `session.avatar.connect` carries the client's SDP offer; configure video resolution, bitrate, codec and animation outputs (blendshapes, visemes).

### Python client library (`azure-ai-voicelive`)

- Real-time speech-to-speech client over WebSocket. From **v1.0.0 it is async-only** (`async`/`await`); the sync API is deprecated.
- `async with connect(endpoint, credential, model) as connection:`; credential = `AzureKeyCredential` or (production) async `DefaultAzureCredential` from `azure.identity.aio`.
- Build a `RequestSession(modalities, instructions, input/output_audio_format, turn_detection=ServerVad(...))` and send it with `await conn.session.update(session=...)`. Loop `async for event in connection`.
- **Handling an interruption:** on `INPUT_AUDIO_BUFFER_SPEECH_STARTED`, stop playback and cancel the current response immediately. Otherwise the client keeps playing the last response and the agent "talks over" the user.

### Voice Live with a Foundry agent

**Why use an agent instead of connecting to a model:**
- Instructions and configuration live in the agent, not in the session code.
- Complex logic and flows can be updated without changing client code.
- Connect with the agent ID (name) and project; settings are handled internally.
- Agent logic is separate from voice implementation, which helps maintenance and scaling (several experiences or business logic variants).

**Create in the portal:** enable **Voice mode** in the agent playground, then in the Configuration pane set:

| Setting | Meaning |
|---|---|
| Language | Language spoken and understood |
| Advanced: VAD | Detect interruptions and end of speech |
| Advanced: audio enhancement | Reduce background noise, improve quality |
| Voice | The voice, plus tone and speaking rate |
| Interim response | Agent speaks while waiting for the model's response |
| Avatar | A visual avatar for the agent |

**Create in code:** Foundry SDK (`AIProjectClient`, `agents.create_version(agent_name, definition=PromptAgentDefinition(model, instructions), metadata=...)`). The Voice Live config (voice, `input_audio_transcription`, turn detection, noise reduction, echo cancellation) is JSON stored in the agent's **metadata** under `microsoft.voice-live.configuration`. Metadata values have a **512-character limit**, so a helper splits the JSON into chunks (`...configuration`, `...configuration.1`, ...).

**Client application pattern:** connect to the agent, configure audio input/output hardware, establish a Voice Live session, monitor audio for activity, process events. Recommended design:
- **Microsoft Entra ID** authentication to the agent in the project.
- A **`VoiceAssistant`** class: typed agent config (agent name, project name), starts and configures the session, processes voice events.
- An **`AudioProcessor`** class: microphone input and speaker output (the sample uses PyAudio; 24 kHz, 16-bit PCM, mono; microphone audio is base64-encoded and sent with `input_audio_buffer.append`; the playback queue is cleared on interruption).
- Connects with `agent_config={"agent_name", "project_name"}` and `api_version="2026-01-01-preview"`.

**Possible lesson errors (flagged):**
- The summary says you "developed a Python-based web application using Flask" and tested it. Nothing in the pasted units does that (probably from the skipped exercise).
- In the create-agent sample, `chunk_config` is called before it is defined, and `load_dotenv` is used without being imported.
- The first connect samples import `connect` from `azure.ai.voicelive`, while the later ones use `azure.ai.voicelive.aio` (the async one).
- The documented endpoints use `api-version=2025-10-01` but the agent client sample uses `2026-01-01-preview`.

### Knowledge check (4/4, all correct)

1. Authentication methods: **Microsoft Entra (keyless) and API key** (not OAuth/JWT, not Basic).
2. Avatar streaming protocol: **WebRTC** (not HTTP/2, not gRPC).
3. Configure and test a Voice Live agent in the portal: **enable Voice mode in the agent playground** (it is not REST/Python only; there is no separate Voice Live playground answer).
4. Stop playback when the user interrupts: **handle `ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED`** (not wait, not reset the session).

**Takeaway:** Voice Live is a WebSocket speech-to-speech API driven by JSON client/server events (`session.update` first), authenticated with Entra (recommended) or API key; for agents, enable voice mode (or store config in agent metadata) and in the client cancel playback when speech starts.

## Module 7: Translate text and speech with Microsoft Foundry Tools

**Goal:** build machine translation with Azure Translator (text) and Azure Speech (speech), both reached through a Foundry resource.

### Translation in Foundry

- LLMs can translate phrases or documents, but comprehensive multi-language translation generally needs specialized models. Foundry Tools provide two:

| Service | What it offers |
|---|---|
| **Azure Translator in Foundry Tools** | Text translation, many languages, **custom translation models** |
| **Azure Speech in Foundry Tools** | Speech-to-text and **speech-to-speech translation** into several languages at once |

- Both are reached through a **Foundry resource endpoint**, with REST APIs and SDKs.

### Azure Translator (text)

- **Over 90 languages.** It can:
  - Translate or **transliterate** text with the default translation model or an **LLM**.
  - Translate **documents** (synchronously or asynchronously) while keeping their structure.
  - Use **custom translation models** for domain-specific terms.
- **Foundry portal:** playgrounds for text translation and document translation. Compare the default model with LLMs and view sample code.
- **SDKs:** Python, .NET, Java, JavaScript (Text Translation client), or REST.
- **Endpoints:**
  - Global: `api.cognitive.microsofttranslator.com`.
  - Regional: `api-nam.`, `api-apc.`, `api-eur.cognitive.microsofttranslator.com`.
  - Foundry resource: `{foundry-resource-name}.cognitiveservices.azure.com/`.
- **Client:** `TextTranslationClient(credential=AzureKeyCredential(key), endpoint=...)` **or** `region=...`.

| Method | Purpose | Key parameters |
|---|---|---|
| `get_supported_languages(scope="translation")` | List available languages (name and ISO code) | `scope` |
| `translate(body, to_language, from_language)` | Translate text to one or more languages | `body` = list of `InputTextItem`; `to_language` = **list** of codes; `from_language` optional, **omit it to auto-detect** (result has `detected_language`) |
| `transliterate(body, language, from_script, to_script)` | Convert the same language to another **script** (no translation) | For example Japanese: `from_script="Jpan"`, `to_script="Latn"` gives "Kon'nichiwa" |

- **Translate vs transliterate:** translate changes the language ("你好" to "Hello"); transliterate changes the script ("спасибо" in Cyrillic to "spasibo" in Latin).

### Azure Speech translation

- The **Speech Translation API** translates spoken input and returns text or speech.
- Objects: **`SpeechTranslationConfig`** (connection by endpoint or region + key, **source and target languages**), **`AudioConfig`** (audio source), **`TranslationRecognizer`** (does the translation).

| Step | Detail |
|---|---|
| Connect | `SpeechTranslationConfig(subscription=KEY, endpoint=...)` or `region=...` |
| Languages | `speech_recognition_language = 'en-US'` (source); `add_target_language('fr')`, `add_target_language('ja')` (one or more targets) |
| Audio source | `AudioConfig(use_default_microphone=True)` (or a file) |
| Translate | `TranslationRecognizer(translation_config, audio_config).recognize_once_async().get()` |
| Result | `.text` = recognized source text; `.translations` = dictionary of language > translated text |

### Speech-to-speech: two approaches

| | Manual synthesis | Event-based synthesis |
|---|---|---|
| Idea | Translate to text, then synthesize each translation yourself | Capture synthesized audio from the recognizer's event |
| Steps | 1. `TranslationRecognizer` translates speech to text in the target languages. 2. For each translation, a `SpeechSynthesizer` makes audio | 1. Set the **voice** for the translated speech in the translation config (`voice_name`). 2. Handle the `TranslationRecognizer` **`Synthesizing` event**. 3. In the handler, get the translated audio bytes from the result (`GetAudio()`; `evt.result.audio` in Python) |
| Languages | **One or more** target languages | **1:1 only** (one source, one target); **not for multi-language translation** |
| Config | Separate `SpeechConfig` (voice name per language, for example `fr-FR-HenriNeural`) and `AudioOutputConfig` (speaker) | Voice in `SpeechTranslationConfig` |

**Possible lesson errors (flagged):**
- The text says "over 90 supported languages", but the sample output says "137 languages supported".
- The event-based steps say to set the voice in "the TranslationConfig" (the code uses `SpeechTranslationConfig`) and to call `GetAudio()` (the Python code reads `evt.result.audio`).
- The assessment option "get_supported_language" is missing the final "s" of the real method `get_supported_languages`.
- The summary ends with an empty documentation link bullet, and the code samples have typos in comments ("trsnslations", "ressults", "TranslationRecognizr").

### Knowledge check (3/3, all correct)

1. Convert "你好" to "Hello": **`translate`**.
2. Convert Cyrillic "спасибо" to Latin "spasibo": **`transliterate`**.
3. Object that specifies the language(s) speech is translated into: **`SpeechTranslationConfig`** (not `SpeechConfig`, not `AudioConfig`).

**Takeaway:** Azure Translator handles text (`translate` changes language, `transliterate` changes script, auto-detect by omitting `from_language`), Azure Speech handles speech (`SpeechTranslationConfig` + `AudioConfig` + `TranslationRecognizer`), and speech-to-speech uses manual synthesis for any number of targets or event-based synthesis for 1:1 only.
