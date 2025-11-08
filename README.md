## 🧭 1. Architecture and conceptual overview

At a high level, the system will look like this:

```markdown
 ┌──────────────────────────┐
 │        YOU (operator)    │
 └─────────────┬────────────┘
               │ triggers a job (manual or scheduled)
               ▼
 ┌──────────────────────────┐
 │     IDE Agent Runner     │ ← Cursor extension or VS Code task
 │  (runs locally inside IDE)│
 └─────────────┬────────────┘
               │
               ▼
 ┌──────────────────────────┐
 │   Agent Orchestrator     │ ← crewAI / Autogen / OpenDevin
 │  (runs, coordinates)     │
 └─────────────┬────────────┘
        runs tasks via local LLM
               ▼
 ┌──────────────────────────┐
 │   Local Model Runtime    │ ← Ollama (Llama3, CodeLlama, GPT-OSS)
 │  (LLM reasoning engine)  │
 └─────────────┬────────────┘
               │
               ▼
 ┌──────────────────────────┐
 │  Your WordPress codebase │
 │   (theme/plugins repo)   │
 │ - Respects ignore rules  │
 │ - Analyses raw PHP files │
 └─────────────┬────────────┘
               │
               ▼
 ┌──────────────────────────┐
 │  Agent Outputs           │
 │ - JSON for flagged issues│
 │ - Markdown refactor suggestions │
 │ - Option to accept/reject proposals │
 │ - Optional: BugHerd ticket summaries (read-only) │
 └──────────────────────────┘
```

### 🧠 The core idea

- Ollama runs a **local model API** that behaves like OpenAI’s API.
- crewAI (or another orchestration framework) lets you define **Agents**, each with:
    - A goal (”check PHP array keys”)
    - A backstory (how it should “think”)
    - A *task input/output pipeline*.
- These agents interact with your **local model** (not the cloud), meaning zero recurring cost and full privacy.
- You can create multiple agents and orchestrate them sequentially or in parallel, e.g.:
    - Static QA agent runs first.
    - Refactor agent uses its findings.
    - Summariser agent produces a report.
    - Optional BugHerd connecter posts results.

## ⚙️ 2. Package and component breakdown

Below are the packages and their roles in this system.

### 🧩 Ollama

- **Purpose**: Local inference engine (runs your chosen LLM on your machine)
- **Why you need it**: Avoids API costs (like GPT-4), provides AI-compatible interface, can run fine-tuned code models.
- **How it’s used**: crewAI & LangChain will talk to it as `http://localhost:11434/v1` - it pretends to be the OpenAI API.
- **Models**: You can choose `llama3.1`, `codellama`, `phi3`, `mistral`, or `gpt-oss:20b`

### 🧩 Python (virtual environment)

- **Purpose**: The runtime environment for orchestrating agents and scripts.
- **Why**: Keeps dependencies isolated so you don’t clutter your system Python.

### 🧩 crewAI

- **Purpose**: Lightweight framework for defining and coordinating multiple AI agents.
- **Why**: Handles “who does what” and “in what order” - it gives you agent management, task execution, and chaining.
- **How**: You create `Agent` objects (each has an LLM, role, and goal). Then you assign each a `Task`. A `Crew` runs them.

**Example**:

```python
crew = Crew(
    agents=[qa_agent, refactor_agent],
    tasks=[Task(...), Task(...)]
)
crew.kickoff()
```

### 🧩 LangChain

- **Purpose**: Middleware between your code/data and the LLM.
- **Why**: It standardises how the LLM gets prompts, file content, or tool output.
- **How it’s used**: crewAI uses it under the hood. You can also use LangChain tools (like file loaders, retrievers) to feed in PHP code snippets or lint outputs.

### 🧩 OpenAI-compatible interface

- **Purpose**: Bridges LangChain and Ollama.
- **Why**: crewAI expects an OpenAI-style API - Ollama provides it locally.
- **How it works**: By setting `OPENAI_API_BASE=http://localhost:11434/v1`, all “OpenAI” calls go to your local LLM.

### 🧩 python-dotenv

- **Purpose**: Loads environment variables from a `.env` file.
- **Why**: Keeps your model config (`MODEL=llama3.1`) and API endpoint private and flexible.
- **Used for**: Storing keys or model names without hardcoding them.

### 🧩 requests (and BugHerd integration)

- **Purpose**: Used for calling BugHerd’s REST API.
- **Why**: Lets you fetch or create BugHerd tasks programatically.
- **Example**: After the agents finish analysis, you can push the report to BugHerd.

```python
requests.post(
  "https://www.bugherd.com/api_v2/tasks.json",
  headers={"Authorization": "Basic YOUR_API_KEY"},
  json={"task": {"description": summary_output}}
)
```

## ⚙️ 3. How it all flows together

Here’s the conceptual data pipeline:

```markdown
(1) You run run_agents.py
     │
     ▼
(2) crewAI orchestrator loads your Agents (Static QA, Refactor, etc.)
     │
     ▼
(3) Each Agent uses LangChain + ChatOpenAI to send a prompt to Ollama
     │
     ▼
(4) Ollama model analyses PHP code (direct text or via PHPStan results)
     │
     ▼
(5) Each Agent writes its findings (JSON, Markdown, BugHerd upload)
     │
     ▼
(6) Optional: a final “Reporting Agent” summarises and outputs a QA report
```

## 🧮 Example agent workflow (WordPress build QA)

1. **StaticCodeQA agent**
    1. Reads plugin/theme folder.
    2. Detected unguarded array keys, missing sanitisation, warnings.
    3. Products JSON of flagged issues.
2. **RefactorAgent**
    1. Reads the above JSON.
    2. Suggests refactor plans, consolidates duplicated files or code, and proposes standardisation.
3. **SummaryAgent**
    1. Compiles results into a markdown QA report (severity, recommendations, and references).
    2. Optionally posts summary to BugHerd.

---

## Phase 0: Preparation

**Goal**: Set up your environment so all dependencies and projects are isolated and ready.

**Steps**:

1. Install Python 3.11+
2. Set up a virtual environment for your agents in the root of your project:

```bash
python -m venv .venv
source .venv/bin/activate # macOS/Linux
.venv\Scripts\activate # Windows
```

1. Install core packages:

```bash
pip install crewai langchain requests python-dotenv
```

1. Install Ollama and choose a code model:
    1. e.g., `llama3.1` or `codellama` 
    2. Confirm local API runs at `http://localhost:11434/v1` 
2. Create the project structure in the root of your project:

```bash
/.agents
/.agentsignore
/venv
.env
run_agents.py
```

1. Add the following to your `.env` file:

```
OPENAI_API_BASE=http://localhost:11434/v1
MODEL=gpt-oss:20b
BUGHERD_API_KEY=<optional, for read-only fetching>
```

## Phase 1: Build agents

**Goal**: Create the individual agents that will perform QA, refactor suggestions, and summaries.

**Steps**:

1. **StaticCodeQA Agent**
    1. Reads all plugin/theme files (respects `.agentsignore`).
    2. Detects:
        1. Unguarded array keys
        2. Missing sanitisation/escaping
        3. General PHP warnings (e.g. notices, deprecated functions)
    3. Outputs JSON of issues:

```json
[
  {
    "file": "plugins/example-plugin/inc/helpers.php",
    "line": 45,
    "issue": "Accessing array key 'foo' without isset()"
  }
]
```

1. **RefactorAgent**
    1. Reads JSON from StaticCodeQA.
    2. Detects:
        1. Duplicate functions or template code
        2. Opportunities to consolidate repeated logic
        3. Suggests consistent code style
    3. Produces Markdown summary or JSON with propopsed changes.
2. SummaryAgent
    1. Compiles all ouputs into a final Markdown report: severity, recommendations, references.
    2. Optionally reads Bugherd tickets (read-only) for context.
    3. Tracks proposals accepted/rejected in a local JSON or SQLite database.

## Phase 2: Orchestration with crewAI

**Goal**: Chain the agents and manage execution flow.

**Steps**:

1. Define agents in Python:

```python
from crewai import Agent, Task, Crew

qa_agent = Agent(name="StaticCodeQA", model="codellama", role="QA agent for PHP code")
refactor_agent = Agent(name="RefactorAgent", model="codellama", role="Refactor suggestions agent")
summary_agent = Agent(name="SummaryAgent", model="codellama", role="Compile report agent")

crew = Crew(
    agents=[qa_agent, refactor_agent, summary_agent],
    tasks=[Task(...), Task(...)]
)
```

1. Create a `run_agents.py` entry point
    1. Handles reading `.agentsignore` 
    2. Loads PHP files and optional BugHerd tickets
    3. Passes content to agents sequentially
    4. Writes output to `/reports` or IDE panel
2. Test orchestration
    1. Run `python run_agents.py`
    2. Verify each agent produces expected outputs (JSON/Markdown)

## Phase 3: IDE integration

**Goal**: Display results and suggestions inside Cursor or VS Code.

**Steps**:

1. **Cursor**
    1. Create a local script panel to run `run_agents.py`
    2. Parse JSON/Markdown to highlight issues and proposed refactors.
    3. Allow “accept/reject” proposals to update local tracking.
2. VS Code (alternative)
    1. Configure a Task in `tasks.json`, optionally use the VS Code API or extension to highlight file lines and show a panel for proposals:

```json
{
  "label": "Run QA Agents",
  "type": "shell",
  "command": "python run_agents.py",
  "problemMatcher": []
}
```

## Phase 4: Proposal tracking and repeat avoidance

**Goal**: Avoid repeated suggestions for rejected changes.

**Steps**:

1. Maintain a local JSON or SQLite database:

```json
{
  "proposals": [
    {
      "id": "unique_issue_id",
      "status": "rejected",
      "timestamp": "2025-11-08T20:00:00"
    }
  ]
}
```

1. Agents read this database before generating proposals.
2. Accepted changes can optionally update the JSON or just be logged.

## Phase 5: Iteration and improvement

**Goal**: Refine agent behaviour and workflow.

**Steps**:

1. Adjust agent prompts for better QA or refactor suggestions.
2. Expand `.agentsignore` to reduce noise.
3. Add additional agents for specialised checks (e.g., ACF, PHPStan lint integration).
4. Automate periodic runs (cron job or VS Code scheduled task).