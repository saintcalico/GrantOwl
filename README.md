# GrantOwl: An Agentic AI Scholarship Adviser 🇵🇭

**GrantOwl** is an academic agent engineered specifically to bridge the educational accessibility gap for Filipino students. Unlike passive listing archives or conventional search engines, GrantOwl securely processes unstructured student resumes or manual application forms, neutralizes security vulnerabilities at the perimeter, evaluates baseline qualifications against hard-coded deterministic rules, and leverages live web search tools to match students with active 2026 scholarship opportunities.

---

## 🛠️ Tech Stack & Project Dependencies

The application is written natively in Python 3.12 and utilizes the following core ecosystem packages:

### Core Framework & Analytics
* Streamlit: Dictates stateful application routing, active step view structures, and session-state guided navigation.
* Plotly: Drives the visual interactive analytics layer, rendering the multi-variable Profile Matching Topology radar matrices and horizontal benchmark bar charts.
* PyPDF2 / PDFPlumber: Intercepts uploaded resume documents to handle raw, local byte-stream extraction without persisting text files to disk.

### Generative AI & Autonomous Web Tools
* OpenAI Python SDK: Manages structured communication pipelines to the gpt-4o-mini engine via optimized, low-temperature JSON contracts.
* Tavily Search API: Empowers the agent to break past static LLM knowledge cutoffs and autonomously query live institutional web portals for active 2026 criteria.

### Security, Safety, & Environment Configuration
* Python re (Regex): Operates at the absolute perimeter as an adversarial defense layer to sanitize character encodings and flag malicious prompt injections.
* python-dotenv: Silently binds server-side configuration environments and hidden API access tokens at initial instantiation.

---

## 🚀 Installation & Local Environment Setup

Follow this sequential terminal script to isolate system dependencies, configure your environment tokens, and spin up the GrantOwl workspace locally.

### 1. Clone the Repository & Initialize Environment

# Clone the repository
git clone [https://github.com/saintcalico/GrantOwl.git](https://github.com/saintcalico/GrantOwl.git)
cd GrantOwl

# Create a virtual isolation environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install modular requirements
python -m pip install --upgrade pip
python -m pip install -r requirements.txt


### 2. Configure Your Access Tokens
Create a file named .env in the root project directory and paste your live API credentials:

OPENAI_API_KEY=your_actual_openai_api_key_here
TAVILY_API_KEY=your_actual_tavily_api_key_here


### 3. Run the Application Workspace

python -m streamlit run app.py


---

## 🧠 How It Works

GrantOwl processes user data securely through a structured, multi-step pipeline directly on your local runtime container:

1. Perception & Security Cleansing: The user provides input via structural web forms or a raw resume upload. The system runs the text block through a regular-expression boundary layer to eliminate corrupt characters and instantly filter out Prompt Injection threats before any data hits the network.
2. Layer 1: Deterministic Filtering Engine: The text profile is evaluated against a hard-coded Python rule matrix (if/else statements). Absolute gates like citizenship status, GPA minimums, and strict income ceilings are verified programmatically, eliminating the risk of AI hallucination for core eligibility rules.
3. Action Layer (Tavily Discovery Call): Viable constraints are bundled into dynamic, optimized keyword search queries. The agent triggers the external Tavily Search API to comb institutional data loops for live, real-time 2026 scholarship structures.
4. Layer 2: OpenAI Reasoning Engine: Validated scholarship targets are processed alongside the user's profile through the gpt-4o-mini model (temperature=0.0). The cognitive engine evaluates qualitative alignments—such as matching a student's leadership footprints with a grantor's organizational values—and assigns a 1–10 compatibility index.
5. Episodic Memory Loop (st.session_state): As the user interacts with the dashboard, their navigations are continuously logged to a running session array (preference_log). This feedback loop dynamically refines subsequent tactical advice and application milestone calendars within that active run.

---

## ⚠️ System Limitations

To guarantee complete computational safety, GrantOwl operates inside explicit boundaries:
* Self-Reported Data Reliance: The system has no backend connection to third-party academic registries or government record offices. Analytical output assumes complete, uncompromised honesty from the user during input stages.
* External Formatting Dependency: Real-time web tool discovery relies heavily on the layout integrity of target institutional web portals. Drastic unstructured changes to external site layouts can occasionally skew secondary text parsing parameters.
* Advisory Status Scope: GrantOwl functions purely as a strategic counselor and preparation companion. It does not submit applications directly to scholarship boards or communicate natively with academic registrar committees.

---

## Disclaimer

*GrantOwl is an educational advisory system designed to optimize your application strategy, not guarantee financial awards. Users retain complete accountability over their actual submissions and timeline tracking. To ensure strict data privacy, all parsed outputs, document data arrays, and tracking logs are stored transiently inside ephemeral session containers; no personal identifying information is ever permanently recorded, saved, or leaked to external databases.*
