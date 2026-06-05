# GrantOwl: An Agentic AI Scholarship Adviser
GrantOwl is an intelligent, autonomous academic agent engineered specifically to bridge the educational accessibility gap for Filipino students. Unlike passive listing archives or conventional search engines, GrantOwl securely processes unstructured student resumes or manual application forms, neutralizes security vulnerabilities at the perimeter, evaluates baseline qualifications against hard-coded deterministic rules, and leverages live web search tools to match students with active 2026 scholarship opportunities.

🛠️ Tech Stack & Project Dependencies
The application is written natively in Python 3.12 and utilizes the following core ecosystem packages:
Core Framework & Analytics
Streamlit: Dictates stateful application routing, active step view structures, and session-state guided navigation.
Plotly: Drives the visual interactive analytics layer, rendering the multi-variable Profile Matching Topology radar matrices and horizontal benchmark bar charts.
PyPDF2 / PDFPlumber: Intercepts uploaded resume documents to handle raw, local byte-stream extraction without persisting text files to disk.
Generative AI & Autonomous Web Tools
OpenAI Python SDK: Manages structured communication pipelines to the gpt-4o-mini engine via optimized, low-temperature JSON contracts.
Tavily Search API: Empowers the agent to break past static LLM knowledge cutoffs and autonomously query live institutional web portals for active 2026 criteria.
Security, Safety, & Environment Configuration
Python re (Regex): Operates at the absolute perimeter as an adversarial defense layer to sanitize character encodings and flag malicious prompt injections.
python-dotenv: Silently binds server-side configuration environments and hidden API access tokens at initial instantiation.
