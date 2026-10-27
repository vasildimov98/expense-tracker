# P4 notes: Extract insights from visual data on Azure

## Module 1: Develop a vision-enabled generative AI application

**Goal:** deploy a multimodal model in Microsoft Foundry and send it prompts that mix text and images, using the Responses API or the ChatCompletions API.

### Vision-capable models

- To handle prompts with images you need a **multimodal model**: it accepts not only text but also images (and in some cases audio).
- Multimodal models in Foundry (among others): **Microsoft Phi-4-multimodal-instruct**, **OpenAI gpt-4.1**, **OpenAI gpt-4.1-mini**.
- **Test in the chat playground** of the Foundry portal: upload a local image and add text to the message.
- Not just object identification: some models can also reason about what they see, for example interpret a chart or judge whether an object is damaged.

### Vision-based chat in code

- Same basics as a text chat: a connection to the endpoint where the model is deployed, then submit messages and process the response.
- **Key difference:** the user message is **multi-part**, with a **text content item and an image content item** in one message (not two separate prompts, and not the image as the system message).
- **Two ways to give the image:**
  - A **web URL** of the image file.
  - A **local file encoded in Base64**, sent as a data URL: `data:image/jpeg;base64,{image_data}` (replace `jpeg` with `png` etc.).

| | Responses API | ChatCompletions API |
|---|---|---|
| Call | `client.responses.create(model, input=[...])` | `client.chat.completions.create(model, messages=[...])` |
| Use when | Model supports the Responses API (for example `gpt-4.1`) | Model does not support it (for example `Phi-4-multimodal-instruct`), through the Azure OpenAI endpoint |
| Instruction role | `developer` | `system` |
| Text item | `{"type": "input_text", "text": ...}` | `{"type": "text", "text": ...}` |
| Image item | `{"type": "input_image", "image_url": data_url}` | `{"type": "image_url", "image_url": {"url": data_url}}` (note the nested `url`) |
| Read the answer | `response.output_text` | `response.choices[0].message.content` |

- Base64 steps: open the file in binary mode (`"rb"`), `base64.b64encode(...)`, `.decode("utf-8")`, build the data URL.

**Possible lesson issue (flagged):** the knowledge check says an image can be included "as a URL or as binary data". The code actually sends **Base64 text inside a data URL**, not raw binary.

### Knowledge check (3/3, all correct)

1. Model type that responds to visual input: **multimodal models** (not "only OpenAI GPT models", not embedding models; Phi-4-multimodal is not OpenAI).
2. Submit a prompt that asks a model to analyze an image: **one prompt with a multi-part user message, containing both text and image content** (not two separate prompts, not the image as the system message).
3. Include an image in a message: **as a URL or as binary data** (Base64 data URL), not only one of the two.

**Takeaway:** vision needs a multimodal model (gpt-4.1, gpt-4.1-mini, Phi-4-multimodal-instruct), and the prompt is one multi-part user message with a text item and an image item; the image is a web URL or a Base64 data URL, sent through the Responses API (`input_text`/`input_image`) or ChatCompletions (`text`/`image_url`).

## Module 2: Generate images with AI

**Goal:** use an image generation model in Microsoft Foundry to create original images from natural language prompts, in the portal and from code.

### Image generation models

- Models in Foundry (among others): the **OpenAI gpt-image-1 series** and the **Black Forest Labs FLUX series**.
- Find them in the **model catalog** by filtering on the inference task **Text to image**.
- The model **generates new images** from what it learned in training. It is **not a search system** that retrieves images from a catalog.
- Use cases: illustrations or photorealistic images for articles and marketing, logos, any image you can describe.

### Foundry portal

- Create a Foundry project and use the **model playground (Images playground)** to submit prompts and view results.
- Subject to model support, you can set the **resolution (size)** and add a **reference image** for the model to base its output on.

### Client app (Images API)

- Use an SDK (OpenAI Python SDK, Azure OpenAI .NET SDK) or REST. The API is the **OpenAI Images API**.

| Step | Detail |
|---|---|
| Generate | `client.images.generate(model, prompt, n, size)`; for example `model="FLUX.1-Kontext-pro"`, `n=1` (number of images), `size="1024x1024"` |
| Read the result | `img_results.data[0].b64_json` holds the image as **Base64** |
| Save | `base64.b64decode(...)`, then write the bytes to a `.png` file opened in `"wb"` mode |

- Compare with P4 m1: **vision** (image in, text out) uses chat/Responses with an `image` content item; **image generation** (text in, image out) uses the **Images API**.

**Possible lesson issues (flagged):**
- The introduction names gpt-image-1, but the only code sample uses `FLUX.1-Kontext-pro`.
- The code section says the result is "a binary stream", but the code receives Base64 text (`b64_json`) and decodes it into bytes yourself.
- The text refers to example images ("could result in ... the following image") that are missing from the pasted text.

### Knowledge check (2/2, all correct)

1. Inference task to filter by in the model catalog to find image generators: **Text to image** (not Image to text, not Embeddings).
2. OpenAI API to use with image generation models: **Image** (the Images API, `client.images.generate`), not "Video" and not "Graphics" (there is no Graphics API).

**Takeaway:** image generation models (gpt-image-1 series, FLUX series) turn a text description into a new image; find them by the "Text to image" task, test them in the Images playground, and call them with the Images API (`images.generate`), decoding the Base64 result.

## Module 3: Generate videos with Microsoft Foundry

**Goal:** deploy Sora 2 in Microsoft Foundry, write effective video prompts, and generate videos from Python with the OpenAI SDK.

### Sora 2 and deployment

- **Sora 2** (OpenAI) creates realistic and imaginative video scenes from text prompts, reference images, or existing videos.
- **Prerequisites:** Azure subscription, access to the Foundry portal, a Foundry project where you may deploy models.
- **Deploy:** Foundry portal > create or select a project > **Build > Models** (model catalog) > find **Sora-2** > **Deploy** > choose deployment settings.

| Capability | Detail |
|---|---|
| Text to video | Video from a natural language prompt |
| Image to video | Turn an existing image into video |
| Video remix | Targeted adjustments to an existing video without regenerating from scratch |
| Audio generation | Audio in the output videos |
| Resolutions | Landscape `1280x720`, portrait `720x1280` |
| Duration | **4, 8 or 12 seconds** (default 4) |

### Generation parameters

| Parameter | Meaning | Values |
|---|---|---|
| `prompt` | Description of the video | Text (required) |
| `model` | Model to use | `sora-2` or `sora-2-pro` |
| `size` | Output resolution | `1280x720` or `720x1280` |
| `seconds` | Duration | 4, 8, 12 |
| `input_reference` | Reference image used as the **first frame** | JPEG, PNG or WebP file |
| `remix_video_id` | ID of a previous video to remix | Video ID string |

- Video generation is **asynchronous**: submit a request, then retrieve the video when ready. Typically **1 to 5 minutes**.
- **Video playground** in the portal: Playground tab, enter prompt, set resolution and duration, **Generate**. **View code** shows prefilled cURL samples.
- **Content moderation filter** applies: a prompt recognized as harmful returns no video.
- Tip: the model follows instructions better in **shorter clips**. Prefer two 4-second clips stitched together over one 8-second clip.

### Writing prompts

Think of briefing a cinematographer. Prompt anatomy: **camera framing** (shot type, angle), **subject** (distinctive details), **action** (in beats: steps, gestures, pauses), **lighting and palette**, **style** (for example "1970s film").

| Weak | Strong |
|---|---|
| "A beautiful street at night" | "Wet asphalt, zebra crosswalk, neon signs reflecting in puddles" |
| "Person moves quickly" | "Cyclist pedals three times, brakes, and stops at crosswalk" |
| "Cinematic look" | "Anamorphic 2.0x lens, shallow DOF, volumetric light" |

- Dialogue in the prompt gives the model words to sync with the character.
- Tips: one clear camera move and one clear subject action per shot; use beats for timing; reuse phrasing for characters to keep continuity; iterate (the second or third generation is often best).

### Reference images and remix

- **Reference image:** anchors the **first frame**; the prompt says what happens next. The image resolution **must match the target video size exactly** (1280x720 or 720x1280). Formats JPEG, PNG, WebP. Images with **human faces are currently rejected**.
- **Remix:** change specific aspects of an existing video while keeping scene transitions, layout and structure. Get the **video ID** of the finished job, call remix with the ID and an updated prompt, and describe **only the change** (one clear adjustment, for example "same shot, switch to 85mm lens"). Narrow edits keep more fidelity.

### Python (OpenAI SDK, `client.videos`)

Three steps: **create the job > poll for completion > download**.

| Step | Call |
|---|---|
| Create | `client.videos.create(model="sora-2", prompt=..., size="1280x720", seconds="4")` (add `input_reference=open("img.png", "rb")` for a reference image) |
| Poll | Loop with `time.sleep(...)` and `client.videos.retrieve(video.id)` until status is `completed`, `failed` or `cancelled` |
| Download | `client.videos.download_content(video.id, variant="video")`, then `.write_to_file("output.mp4")` |
| Remix | `client.videos.remix(video_id=..., prompt=...)` |

| Job status | Meaning |
|---|---|
| `queued` | Waiting to be processed |
| `in_progress` | Being generated |
| `completed` | Ready for download |
| `failed` | Generation failed; check `video.error` |
| `cancelled` | Job was canceled |

**Key limits:** up to **2 video creation jobs at the same time**; completed videos can be downloaded for **24 hours**; reference image resolution must match exactly; prompts are content-moderated.

**Possible lesson issues (flagged):**
- The Sora 2 deploy unit says "Select Build from the navigation pane on the right", then "Models from the left-hand menu" (the pane sides are inconsistent).
- The module deploys only "Sora 2", but the parameter table allows `sora-2-pro` without explaining it.
- `seconds` is documented as numbers 4, 8, 12, but the code passes a string (`"4"`).
- The unit title of the prompting unit is missing from the pasted text (the heading was cut off).

### Knowledge check (3/3, all correct)

1. Supported durations: **4, 8 or 12 seconds** (not 1-20 s, not up to 60 s).
2. Required with a reference image: **the image resolution must match the target video size** (not under 1 MB, not a human face; faces are rejected).
3. Purpose of remix: **targeted adjustments to an existing video without regenerating from scratch** (not combining videos, not adding music).

**Takeaway:** Sora 2 makes 4/8/12-second videos (1280x720 or 720x1280) from text, a first-frame reference image or a remix, through an asynchronous job: `videos.create` > poll `videos.retrieve` > `download_content`.

## Module 4: Analyze images with Content Understanding

**Goal:** use Azure Content Understanding (a Foundry Tool) to turn images into structured data with prebuilt or custom analyzers and a field schema.

### What Content Understanding is

- Uses generative AI to process **documents, images, video and audio** and return **structured output** for automation, analytics and search.
- You define a **schema** of the data you want; no complex prompt engineering.
- Benefits: one unified process for extraction and classification; **multiple AI models cross-validate** results; **confidence scores and grounding** reduce the cost of human review; **content classification** routes documents to the right analyzer.

| Component | Description |
|---|---|
| Inputs | Documents, images, video, audio |
| **Analyzer** | Defines how content is processed: extraction settings and field schema |
| Content extraction | Normalized text and metadata via OCR, speech transcription, layout detection |
| Field extraction | Key-value pairs from your schema |
| Confidence scores | Reliability **0 to 1** per extracted field value |
| **Grounding** | The **specific regions in the content where each value was extracted** |
| Structured output | **Markdown** for search scenarios, **JSON** for automation workflows |

- **Analyzer types:** **prebuilt** (invoices, receipts, call center analytics) and **custom** (your own field schema).
- **When you create an analyzer you set:** the **base analyzer type** (document, image, audio or video), the AI models, the field schema, and options such as confidence scoring and content segmentation.
- **Use cases:** intelligent document processing (invoices, contracts, claims), search and RAG (figure descriptions, layout analysis), agentic apps (standardized inputs for agents), analytics and reporting.
- **Responsible AI:** built-in **Azure AI Content Safety** filters harmful content; face description can identify facial attributes in images and video; biometric data needs notice and consent.

### Images

- **Supported formats:** JPEG, PNG, BMP, TIFF, HEIF, PDF (single or multi-page).

| Prebuilt analyzer | Use |
|---|---|
| `prebuilt-image` | General image analysis: content extraction and **figure description** |
| `prebuilt-receipt` | Vendor names, items, totals, dates from receipts |
| `prebuilt-invoice` | Invoice details: line items, amounts, vendor |
| `prebuilt-idDocument` | Identity documents (driver's licenses, passports) |

### Field schema: three extraction methods

| Method | What it does | Example |
|---|---|---|
| `extract` | Pulls values **as they appear** | Text from a label or sign |
| `classify` | Picks from **predefined options** (`enum`) | "damaged" or "undamaged" |
| `generate` | **Creates** a value from analyzing the image | A description of the scene |

- A custom analyzer JSON has `description`, `baseAnalyzerId` (for example `prebuilt-image`) and `fieldSchema.fields`; each field has `type`, `method`, `description` (and `enum` for classify).

### Analyze an image (Python)

1. `pip install azure-ai-contentunderstanding`.
2. `ContentUnderstandingClient(endpoint=<Foundry endpoint>, credential=AzureKeyCredential(key) or DefaultAzureCredential(), api_version="2025-11-01")`.
3. `poller = client.begin_analyze(analyzer_id=..., inputs=[AnalysisInput(data=file_bytes)])` (long-running operation; image URL or file).
4. `result = poller.result()` (`AnalysisResult`).

**Result contents:**

| Property | Meaning |
|---|---|
| `markdown` | Text representation of the image; good for search and RAG |
| `fields` | Extracted values matching the schema, each with a confidence score (for example `valueString`, `confidence`) |
| `source` | **Grounding**: where in the image the value was found (for example `D(1,100,50,300,50,...)`) |

### Confidence scores

| Score | Action |
|---|---|
| High, **0.9+** | Trust for automated processing |
| Medium, **0.7-0.9** | Consider human review for critical applications |
| Low, **below 0.7** | Manual verification |

- Build workflows that send low-confidence values to human reviewers and process high-confidence ones automatically.

### Tips for better images

Higher resolution; clear lighting and contrast; one clear subject (not cluttered); consistent upright orientation.

**Possible lesson issues (flagged):**
- The code sample uses placeholders (`{FOUNDRY_ENDPOINT}`, `{KEY_OR_IDENTITY}`, `{ANALYSER_ID}`) and does not import `json` or `sys`, so it will not run as is.
- The text says each field has a confidence score, but in the example response the generated `Description` field has none (and `Condition` has no `source`).
- The score bands overlap at 0.9 (high "0.9+", medium "0.7-0.9").
- The introduction of the analyzers section lists `prebuilt-receipt`, `-invoice` and `-idDocument` as "image analyzers", but they are document-type analyzers that also accept images and PDFs.

### Knowledge check (3/3, all correct)

1. Purpose of grounding: **identify the specific regions in the content where each value was extracted** (not connecting to Azure storage, not filtering harmful content; that is Content Safety).
2. Confidence 0.95: **the value can be trusted for automated processing** (not failure, not a classify method).
3. Prebuilt analyzer for vendor names and totals on a purchase receipt: **`prebuilt-receipt`** (not `prebuilt-image`, not `prebuilt-invoice`).

**Takeaway:** Content Understanding runs an analyzer (prebuilt or custom, with a schema of `extract`/`classify`/`generate` fields) over images and returns Markdown plus JSON fields with confidence scores and grounding, which you use to automate high-confidence values and route low-confidence ones to people.

## Module 5: Create a multimodal analysis solution with Azure Content Understanding

**Goal:** understand what Content Understanding can analyze, how to build a custom analyzer in Content Understanding Studio, and how the REST API analyzes content asynchronously. (Information extraction domain.)

### What it is

- A **multimodal generative AI service** that extracts insights and data from content in practically any format, with one service and one consistent process.
- Needs a **Microsoft Foundry resource**. Develop and manage a solution in: the **Foundry portal**, **Content Understanding Studio**, or the **Content Understanding API**.

| Content | Example uses |
|---|---|
| Documents and forms | Field values, for example key data from an invoice to automate payment |
| Images | Infer information from charts, find physical defects, detect objects or people |
| Audio | Summarize conference calls, sentiment of customer calls, key data from phone messages |
| Video | Key points of video conferences, summaries of presentations, activity in security footage |

- **Bring Your Own Model:** connect your own generative AI model deployments from Foundry for custom analyzers, to optimize for quality, latency or cost.

### Create an analyzer: four steps

1. Create a **Foundry resource**.
2. **Define a schema** for the information to extract (based on a content sample and an analyzer template).
3. **Build the analyzer** from the finished schema.
4. **Use the analyzer** to extract or generate fields from new content.

- **Analyzer templates** speed things up. Thanks to generative AI you need **minimal sample data**: define the schema by example; the service often maps sample values to schema elements automatically. You can also **label fields explicitly** (for example in documents) to improve performance.

### Content Understanding Studio

- Visual interface to create a project, define a schema, and build and test an analyzer. Use it for **custom analyzers**; only certain prebuilt models are available directly in the Foundry portal.
- **Project:** associated with a Foundry resource; creating it provisions supporting Azure resources, including **storage** and a **key vault** (for credentials and keys). Only available in **supported Azure regions**.
- **Schema editor:** upload a sample file (document, image, audio or video), apply a **schema template**, define the fields. Templates and field types **depend on the content type** of the sample; some types add options (for example barcodes and formulae in documents).
- **Testing:** run analysis on the sample or other uploaded files at any time; results show the extracted fields and the **JSON** output a client app would get.
- **Build the analyzer:** makes it available to client apps through the **Foundry resource endpoint**. You can keep testing and refine the schema into new **named versions**.

### Content Understanding API (REST)

- HTTP calls to the Foundry resource's Content Understanding endpoint with one of the **keys in the header** (keys and endpoint in the Azure portal or Foundry portal), or the Foundry API with **Entra ID**.
- Analysis is **asynchronous**:

| Step | Detail |
|---|---|
| 1. Submit | `POST {endpoint}/contentunderstanding/analyzers/{analyzer}:analyze?api-version=2025-11-01` with `{"inputs": [{"url": "..."}]}` |
| 2. Response | `Operation-Id` and `Operation-Location` headers, body `{"id": ..., "status": "NotStarted"}` |
| 3. Poll | `GET {endpoint}/contentunderstanding/analyzerResults/{operation-id}?api-version=2025-11-01` until it succeeds or fails |
| 4. Results | JSON; depends on content and schema |

- Pass a **URL** in `inputs`; to send **binary file data** use the **`analyzeBinary`** operation instead.
- **Confidence scores and source grounding** per field appear when the analyzer is configured with **`estimateFieldSourceAndConfidence`** enabled.

**Possible lesson issues (flagged):**
- The heading of the "Create a Content Understanding analyzer" unit is cut off in the paste ("reate").
- The text says the analyzer is "trained" to extract information, but you do not train it; you define a schema (with optional labels or samples).
- The module says to build custom analyzers in Studio, while the Foundry portal and the Python SDK (P4 m4) can also work with analyzers; the module does not say which operations are portal-only.

### Knowledge check (3/3, all correct)

1. What Content Understanding helps build: **analyzers that extract information from documents, images, videos and audio** (not translation chatbots, not image generators).
2. Graphical tool to create a project: **Content Understanding Studio** (not Visual Studio, not Azure Machine Learning studio).
3. What you define for the information to extract: **a schema** (not an index, not a cluster).

**Takeaway:** Content Understanding is one multimodal service for documents, images, audio and video: you define a schema in Content Understanding Studio, build the analyzer, then call it through the endpoint (`:analyze` for a URL, `analyzeBinary` for bytes), poll `analyzerResults` with the operation ID, and enable `estimateFieldSourceAndConfidence` to get confidence and grounding.

## Module 6: Create an Azure Content Understanding client application

**Goal:** write client code (Python SDK and REST API) that creates an analyzer, submits content to it and processes the results. (Information extraction domain.)

### Prepare

- **Resource:** a Microsoft Foundry resource, either created in the Azure portal or included by default in a **Foundry project** (the project also gives you visual tools for schemas and analyzers).
- **To connect you need:** the **Foundry resource endpoint** and **one of its API keys** (Azure portal, or the Foundry portal project home page). In a project you can also use the Foundry SDK with **Entra ID** to retrieve the connection details.
- **SDK:** `pip install azure-ai-contentunderstanding` (Python **3.9 or later**). REST works from any language.
- **Important prerequisite:** set up **default model deployments** on the Foundry resource: **`GPT-4.1`, `GPT-4.1-mini` and `text-embedding-3-large`** (Azure portal or API).

### Create an analyzer in code

- Usually build and test analyzers in **Content Understanding Studio**, but you can also submit a **JSON definition**.

| Analyzer JSON property | Meaning |
|---|---|
| `description` | Text description |
| `baseAnalyzerId` | Analyzer to build on (for example `prebuilt-document`) |
| `config` | Settings, for example `"returnDetails": true` |
| `fieldSchema.fields` | Fields, each with `type`, `method` (`extract` = value exists in the document and is read), `description` |
| `models` | Generative models used: `completion` (`gpt-4.1`) and `embedding` (`text-embedding-3-large`) |

| | Python SDK | REST |
|---|---|---|
| Call | `client.begin_create_analyzer(analyzer_name, body=definition)` | `PUT {endpoint}/contentunderstanding/analyzers/{name}?api-version=2025-11-01` |
| Auth | `ContentUnderstandingClient(endpoint, AzureKeyCredential(key))` | Header `Ocp-Apim-Subscription-Key: <key>` |
| Async handling | Returns a **poller**; `poller.result()` waits (result has `analyzer_id`) | Response header **`Operation-Location`** = callback URL; `GET` it until the operation is no longer running |

### Analyze content

- Content can be a **URL** (Internet-accessible file) or **binary data** (PDF, PNG, MP3, MP4 ...). The request names the **analyzer**. Analysis is **asynchronous**.

| | Python SDK | REST |
|---|---|---|
| Submit | `client.begin_analyze(analyzer_id=name, inputs=[AnalysisInput(url=...)])` | `POST {endpoint}/contentunderstanding/analyzers/{name}:analyze?api-version=2025-11-01` with `{"inputs": [{"url": ...}]}`; use **`analyzeBinary`** for file bytes |
| Wait | `poller.result()` polls for you | Take the operation `id`, then `GET {endpoint}/contentunderstanding/analyzerResults/{id}?api-version=2025-11-01` until `status` is `Succeeded` |
| Read fields | `result.contents[0].fields`: `field_data.type`, `field_data.value` | `result_json["result"]["contents"][i]["fields"]`: `field_data["type"]`, `field_data["valueString"]` |

- **`AnalysisResult.contents`** is a list of content objects, each with `fields`, `markdown` and metadata.
- **Results depend on:** the content kind (document, image, audio, video), the schema, and the file contents.
- **A document analyzer response contains:** the **extracted fields** and the **OCR layout** (pages with lines, words, paragraphs, locations).
- **Field object (REST):** `type`, a **type-specific value** (`valueString` for strings), `spans`, `confidence`, `source` (grounding location, for example `D(1,69,234,...)`).
- **Response top level:** `id`, `status` (`Succeeded`), `result` with `analyzerId`, `apiVersion`, `createdAt`, `warnings`, `contents` (with `kind`, `markdown`, `pages`, `paragraphs`, `sections`, `unit`).

**Possible lesson issues (flagged):**
- The REST polling loops use `while status == "Running"` with no `sleep`, and the earlier module showed an initial status of `NotStarted`, which that loop would skip (it should also wait while `NotStarted`).
- The URL f-strings contain `{<YOUR_ENDPOINT>}`, which is not valid Python (a placeholder inside braces).
- The SDK sample reads `field_data.value` but the REST JSON uses `valueString`; the lesson does not explain that the SDK exposes a typed `value`.
- The sample response uses the analyzer ID `biz_card_analyser_2` while the code creates `business_card_analyser`.
- The introduction says the SDK or REST API "is the focus" (singular) while the module covers both.

### Knowledge check (3/3, all correct)

1. Configuration values needed for the API: **the endpoint and key for the Foundry resource** (not resource group name, not subscription ID and tenant ID).
2. What you must specify when calling analyze: **the name of the analyzer** (not the resource name, not an `Operation-Location`).
3. How extracted fields are returned: **as type-specific values** (not a list of strings, not a single blob).

**Takeaway:** a Content Understanding client needs the Foundry endpoint and key (plus GPT-4.1, GPT-4.1-mini and text-embedding-3-large deployments), creates analyzers with `begin_create_analyzer` or `PUT`, analyzes with `begin_analyze` or `POST ...:analyze` (poll `analyzerResults` by operation ID in REST), and reads type-specific field values with confidence and source grounding.

## Module 7: Extract data with Azure Document Intelligence

**Goal:** use Azure Document Intelligence (a Foundry service) to extract text, key-value pairs, tables and fields from forms and documents, with document analysis models, prebuilt models and custom models. (Information extraction domain.)

### What it is

- Cloud AI service in Foundry using **OCR and deep learning** to extract text, key-value pairs, selection marks and tables.
- OCR creates **bounding boxes** around detected objects; the coordinates are relative to the page and returned as structured **JSON** that keeps the relationships from the original document.
- The underlying models are already trained on thousands of forms, so you get high accuracy with little effort.

| Model category | What it does |
|---|---|
| **Document analysis** | `read` and `layout`: text, structure, tables, selection marks |
| **Prebuilt** | Common document types (invoices, receipts, tax forms, IDs ...), no training |
| **Custom** | Your own forms, trained on your labeled data: template, neural, composed, custom classifiers |

- **Access:** REST API, SDKs (Python, C#, Java, JavaScript), **Document Intelligence Studio** (`documentintelligence.ai.azure.com`), Foundry portal.
- **Resource:** a **Foundry resource** (multi-service, one endpoint and key for several Foundry tools) **or** a dedicated **Document Intelligence resource** (single service). Use the dedicated one only if you need Document Intelligence alone.
- **Input requirements:** JPEG, PNG, BMP, PDF (text or scanned), TIFF (the read model also accepts Office formats); file size **under 500 MB** (standard tier) or **4 MB** (free tier); image size **50 x 50 to 10,000 x 10,000 pixels**; PDF under **17 x 17 inches** (A3) and **not password-protected**.

### Document Intelligence Studio

- Project types: **document analysis models** (read, layout), **prebuilt models**, **custom models** (build, label, train, test extraction models and classifiers).
- **Prebuilt in Studio:** create resource > open Studio, pick model > give endpoint and key > upload file or URL > review fields and confidence scores.
- **Custom model project workflow:**
  1. Create the resource.
  2. Upload **at least 5-6 sample forms** to an Azure **Blob Storage** container.
  3. Configure **CORS** so the Studio can reach the container.
  4. Create the project, linking storage and resource.
  5. **Label** fields in the visual interface.
  6. **Train** and review accuracy metrics.
  7. **Test** on a new document not used in training.
- The Studio **generates `ocr.json`, `labels.json` and `fields.json` automatically**.

| Add-on capability | What it does |
|---|---|
| High resolution extraction | More accurate text from high-resolution documents |
| Formula extraction | Math formulas |
| Font property extraction | Style, weight, color |
| Barcode extraction | Detect and read barcodes |
| Searchable PDF | Scanned document to searchable PDF |
| Query fields | Natural language queries for specific fields |
| Key-value pairs | Label-response pairs, using the layout model |

- Some add-ons are **premium** and cost extra.

### Document analysis models

| Model | Does | Use when |
|---|---|---|
| **Read** | Printed **and handwritten** text; detects the **language** of each line; labels text as handwritten or printed; foundation of all other models; `pages` parameter selects pages of multi-page PDF/TIFF | Words and lines from documents with **no fixed structure** |
| **Layout** | Everything in read **plus selection marks, tables and document structure**; optional **`keyValuePairs`** feature; handles angled scans, merged cells, incomplete rows; each cell has content, bounding box, row/column index; selection marks have bounding box, confidence and selected state | Text **and table structure** from documents with varying formats, no specific labeled fields needed |

- The old **general document model** was deprecated in the 2023-10-31-preview release; its key-value pair and entity extraction moved into the layout model and other features.

### Prebuilt models (no training)

| Group | Models |
|---|---|
| Financial and legal | Invoice (customer, vendor, PO number, dates, addresses, line items, totals), Receipt (merchant, date/time, line items, totals; single-page hotel receipts), Bank statement, Check, Pay stub, Credit card, Contract |
| US tax | Unified US tax, W-2, 1098, 1099, 1040 (and variations) |
| US mortgage | 1003 (URLA), 1004 (URAR), 1005, 1008, Closing disclosure |
| Personal identification | **ID document** (US driver's licenses, EU IDs and driver's licenses, international passports), Health insurance card, Marriage certificate |

- **ID document privacy:** personal data covered by data protection laws; get the person's permission and comply with the law.
- **Prebuilt features:** text extraction (printed and handwritten) in all models; **key-value pairs** (label and its value, for example Weight and 31 kg); **selection marks**; **tables** (rows, columns, headings, merged cells); **fields** (fixed set per form type, for example `CustomerName`, `InvoiceTotal`).
- **Prebuilt vs custom:** always check whether a prebuilt model exists first. Use custom only for industry-specific or unique forms, because it needs time and sample data.

### Custom models

Supervised learning: you **label** sample documents and the service trains a model.

| Factor | Custom template | Custom neural |
|---|---|---|
| Best for | Structured forms with a consistent visual layout (questionnaires, applications, government forms) | Structured, semi-structured and unstructured documents with varying layouts |
| Training | Minutes, lower cost | Longer, higher cost, more resources |
| Accuracy | High for fixed layouts, drops when layout varies | Higher overall, especially for varying formats |
| Languages | 100+ | Fewer (check docs) |
| Supports | Key-value pairs, selection marks, tables, regions, signatures | Overlapping fields, signature detection, table/row/cell-level confidence |

- Tip: start with **template** (faster and cheaper); switch to **neural** if accuracy is not enough or layouts vary.
- **Custom classifier:** identifies the **document type** before extraction, so you can route documents to the right extraction model.
- **Composed model:** combines several custom models into one; Document Intelligence **classifies** the submitted document, picks the best component model, and returns that model's results.

**Train with the REST API / SDK:**
1. Put sample forms in a blob container with: an **`ocr.json`** per form (made with the Analyze document function), one **`fields.json`** (the fields to extract), and a **`labels.json`** per form (maps fields to locations).
2. Generate a **SAS URL** for the container.
3. Call **Build model** (REST) or the SDK equivalent.
4. Call **Get model** to retrieve the trained model ID.

**Use a custom model:** call **Analyze document** with the model ID (Python `DocumentIntelligenceClient.begin_analyze_document(model_id, AnalyzeDocumentRequest(url_source=...))` then `.result()`; C# `AnalyzeDocumentAsync(WaitUntil.Completed, modelId, fileUri)`). The response has an **`analyzeResult`** object with content and a `pages` array.

**Possible lesson issues (flagged):**
- The unit lists sample forms "at least 5-6" but one knowledge check option says "a minimum of 100 labeled forms", a distractor that sounds like the 100+ languages figure.
- The Studio steps say "Azure Document Intelligence or Foundry Tools resource" while elsewhere it is called a "Foundry resource" (inconsistent naming).
- The module says the exercise focuses on the Python SDK, but the custom model code shows C# first.
- The Python snippet for a custom model omits its imports and the client setup lines are sample placeholders.
- In question 3 the pasted text marks no option as "Correct" (the answer is the composed model or custom classifier).

### Knowledge check (3/3, all correct)

1. Text and table structure from documents with varying formats, no labeled fields: **the layout model** (not read, which has no tables; not invoice).
2. Training artifacts for the REST API: **sample forms plus `ocr.json`, `labels.json` and `fields.json` in a blob container** (not forms only, not 100 forms and a classifier).
3. A single endpoint that routes invoices and receipts to the right extraction model: **a composed model, or a custom classifier paired with extraction models** (not a custom neural model, not the read model).

**Takeaway:** Document Intelligence has read (text) and layout (text + tables + selection marks) models, many prebuilt models for common documents, and custom models (template for fixed layouts, neural for varying ones) trained from labeled forms in blob storage via a SAS URL; use a custom classifier or composed model to route mixed document types.

## Module 8: Create a knowledge mining solution with Azure AI Search

**Goal:** use Azure AI Search to index data from many sources, enrich it with AI skills, query and filter the index, and persist enriched data in a knowledge store. (Information extraction domain.)

### What Azure AI Search is

- Cloud service for **indexing and querying** structured, semi-structured and unstructured data, at high scale.
- Lets you: index documents from many sources; **enrich index data with AI skills**; store extracted insights in a **knowledge store**.
- An index can hold text read with **OCR** from images, **entities and key phrases** from text analytics, and other derived data.
- **Applications:** enterprise search; **RAG** for generative AI (vector-based indexes as prompt grounding data); **knowledge mining** (the focus here): infer insights and extract granular data assets from documents for analytics.

### Indexer and enrichment pipeline

| Piece | Role |
|---|---|
| **Data source** | Where the original data lives (blob container, database, other store) |
| **Indexer** | Automates extraction and indexing; runs the **enrichment pipeline**; **document cracking** extracts content from the source documents; builds a hierarchical (JSON) document with the fields the index needs. It is what is **scheduled** to populate the index |
| **Skillset** | The AI skills the pipeline applies, **in order** |
| **Index** | The searchable result: a collection of JSON documents |
| **Knowledge store** | Optional persisted projections of the enriched data |

- **Document building:** one document per indexed entity. It starts with fields from the source (`metadata_storage_name`, `metadata_author`, `content`). If images are extracted they go in a **`normalized_images`** collection, which is the input for image skills. Each skill adds fields (for example `language`). Skills run in a **context** (a level of the hierarchy), for example OCR **per image**. A skill's output can feed later skills (a **merge skill** combines `content` with image text into `merged_content`).
- **Mapping to the index:**
  - Fields from the source: **implicit** (same name) or **explicit** (field mapping, to rename or apply a function).
  - **Skill outputs are always explicitly mapped** from their hierarchical location to the index field (output field mappings).

### AI skills

| Skill type | Details |
|---|---|
| **Built-in** | Use **Foundry Tools** (Azure Vision, Azure Language): detect language, extract entities, extract **key phrases**, **translate** text, find or remove **PII**, **OCR** text from images, generate **captions and tags** for images |
| **Custom** | Your own logic returning new field values; often a wrapper around a service, for example an **Azure Function** that passes data to an **Azure Document Intelligence** model to extract form fields |

- **Built-in skills need a Foundry Tools resource:** either the **restricted free resource** included with Azure AI Search (limited to **20 or fewer documents**) or an attached Foundry Tools resource in your subscription, which must be in the **same region** as the search resource.

### Search an index

**Index field attributes:**

| Attribute | Meaning |
|---|---|
| `key` | Unique key for records |
| `searchable` | Can be queried with full-text search |
| `filterable` | Usable in filter expressions |
| `sortable` | Usable to order results |
| `facetable` | Usable to compute facets (UI filter lists of known values) |
| `retrievable` | Can be returned in results (**default: all fields**) |

- **Full-text search** uses **Lucene query syntax**: **Simple** (basic, matches literal terms) or **Full** (complex filtering, regular expressions, more sophisticated queries).
- **Query parameters:** `search` (the terms), `queryType` (`simple` or `full`), `searchFields` (fields to search), `select` (fields to return), `searchMode` (`Any` = documents with any term; `All` = documents with all terms, for example both "comfortable" and "hotel").

**Query processing: four stages (in order):**

| # | Stage | What happens |
|---|---|---|
| 1 | Query parsing | Expression becomes a tree of subqueries: term, phrase (`"free parking"`), prefix (`air*`) |
| 2 | Lexical analysis | Lower-casing, stopword removal, root forms ("comfortable" to "comfort"), splitting composite words |
| 3 | Document retrieval | Query terms matched against indexed terms |
| 4 | Scoring | Relevance score per result using **TF/IDF** |

**Filter, facet, sort:**
- **Filter:** in a simple search expression, or with an **OData `$filter`** parameter plus a full-syntax search: `search=London`, `$filter=author eq 'Reviewer'`, `queryType=Full`. Only on **filterable** fields. **OData `$filter` is case-sensitive.**
- **Facets:** a first query returns the possible values of a **facetable** field (`search=*`, `facet=author`); the next query filters with the chosen value (`$filter=author eq '...'`). Best for fields with few discrete values.
- **Sort:** default is relevance score, highest first. Override with OData **`$orderby`** on **sortable** fields (`$orderby=last_modified desc`).

### Knowledge store

- The index is the main output, but the enriched data is also useful for: exporting JSON for **ETL**, normalizing into **relational tables** for analysis and reporting, saving extracted **images as files**.
- Define the **knowledge store in the skillset**. It holds **projections** of the enriched data; they are generated and persisted whenever the indexer runs the pipeline.

| Projection | Result |
|---|---|
| **Object** | JSON objects |
| **Table** | Relational schema (tables) |
| **File** | Image files |

**Possible lesson issues (flagged):**
- The first filter example `search=London+author='Reviewer'` with `queryType=Simple` is not valid simple syntax for filtering on a field; the `$filter` form with full syntax is the correct pattern.
- The lesson says the restricted resource is "limited to 20 or fewer documents" without saying it is a free, limited allowance.
- The intro paragraph says "the indexing process... filters results using full-text search", but the module does not cover vector, hybrid or semantic search (only mentions vector indexes for RAG). Those are planned as separate self-study (plan Days 40-41).
- The unit text calls the index "created and updated by an indexer", but the index definition is created separately; the indexer populates it.

### Knowledge check (3/3, all correct)

1. Component scheduled to extract and enrich data to populate an index: **indexer** (not projection, not query).
2. Service that supports built-in AI skills: **Foundry Tools** (not Azure Functions, which is for custom skills; not Cosmos DB).
3. Projection that results in a relational schema: **table** (not file, not object).

**Takeaway:** an indexer reads a data source, cracks documents and runs a skillset (built-in Foundry Tools skills or custom skills) to build enriched JSON documents, maps them to an index (queried with Lucene simple or full syntax plus `$filter`, facets and `$orderby`), and can persist the enrichment as object, table or file projections in a knowledge store.
