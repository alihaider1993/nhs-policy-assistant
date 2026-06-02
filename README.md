# 🏥 NHS Employee Policy Assistant

> A RAG-powered chatbot that lets NHS staff query their employment rights, sick pay, leave entitlements, whistleblowing rights, and workplace policies — in plain English.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-0078D4?logo=microsoft-azure)
![Azure AI Search](https://img.shields.io/badge/Azure%20AI%20Search-RAG-0078D4?logo=microsoft-azure)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 Overview

The **NHS Employee Policy Assistant** is a portfolio project demonstrating a production-grade **Retrieval-Augmented Generation (RAG)** pipeline built entirely on Microsoft Azure.

NHS staff (doctors, nurses, admin) can ask natural language questions like:

- *"How many sick days am I entitled to as a Band 5 nurse?"*
- *"What is the pay if I am a Band 5 Nurse?"*
- *"What is the NHS whistleblowing policy?"*
- *"How do I raise a formal grievance?"*
- *"What are my maternity leave entitlements?"*

The assistant retrieves relevant chunks from official NHS policy documents and generates accurate, cited answers using GPT-4o.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   Streamlit UI  │────▶│  Azure OpenAI GPT-4o │────▶│  Azure AI Search    │
│  (Chat frontend)│     │  (Response generation)│     │  (Vector + Semantic │
└─────────────────┘     └──────────────────────┘     │   RAG over NHS docs)│
                                                       └──────────┬──────────┘
                                                                  │
                                                       ┌──────────▼──────────┐
                                                       │  Azure Blob Storage  │
                                                       │  (NHS PDF corpus)    │
                                                       └─────────────────────┘
```

### Azure Resources

| Resource | Purpose | Tier |
|---|---|---|
| Azure AI Foundry | GPT-4o deployment & orchestration | Standard |
| Azure AI Search | Vector + semantic index over NHS docs | Basic |
| Azure Blob Storage | NHS PDF document store | LRS |
| text-embedding-ada-002 | Document & query vectorisation | Standard |

---

## 📚 Knowledge Base

The assistant is grounded in **16+ official NHS policy documents** including:

| Document | Coverage |
|---|---|
| AfC Handbook v60 (Jan 2026) | Pay, sick pay, annual leave, parental leave |
| NHS Constitution 2023 | Staff rights and pledges |
| NHS People Promise | Staff commitments |
| Grievance Policy & Procedure | Raising formal complaints |
| Disciplinary Policy | Conduct and performance management |
| Whistleblowing / Freedom to Speak Up | Speaking up safely |
| Flexible Working Toolkit | Flexible working requests |
| Civility & Respect Toolkit | Bullying & harassment |
| Health & Wellbeing at Work | Attendance and support |
| EDI Workforce Plan | Equality, diversity & inclusion |
| Pay & Conditions Circular 2026 | Latest pay guidance |

---

## ✨ Features

- 🔍 **Hybrid + Semantic Search** — combines keyword and vector search for accurate retrieval
- 📄 **Document Citations** — every answer shows which NHS policy document it came from
- 💬 **Conversation Memory** — maintains context across multi-turn conversations
- 🕐 **Chat History** — sidebar stores recent conversations
- 💡 **Suggested Questions** — quick-start prompts for common queries
- 🎨 **NHS-branded UI** — clean blue/white interface matching NHS design standards
- ⚠️ **Responsible AI** — always signposts to HR for personal advice, never gives legal advice-  recommends consulting your specific Trust and Deanery for local policy variations

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Azure subscription with:
  - Azure AI Foundry resource
  - GPT-4o model deployed
  - Azure AI Search (Basic tier)
  - NHS documents indexed

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/alihaider1993/nhs-policy-assistant.git
cd nhs-policy-assistant

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your Azure credentials (see Configuration section)

# 5. Run the app
streamlit run app.py
```

### Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
# Azure OpenAI (from ai.azure.com → Models + endpoints)
AZURE_OPENAI_ENDPOINT=https://your-foundry-resource.openai.azure.com
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o-nhs

# Azure AI Search (from portal.azure.com → nhs-search-basic → Keys)
AZURE_SEARCH_ENDPOINT=https://nhs-search-basic.search.windows.net
AZURE_SEARCH_KEY=your-key-here
AZURE_SEARCH_INDEX=nhs-policy
```

---

## ☁️ Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set `app.py` as the main file
5. Add your Azure credentials under **Settings → Secrets**:

```toml
AZURE_OPENAI_ENDPOINT = "https://..."
AZURE_OPENAI_KEY = "..."
AZURE_OPENAI_DEPLOYMENT = "gpt-4o-nhs"
AZURE_SEARCH_ENDPOINT = "https://..."
AZURE_SEARCH_KEY = "..."
AZURE_SEARCH_INDEX = "nhs-policy"
```

---

## 🔐 Security

- All credentials stored as environment variables — never hardcoded
- Azure Managed Identity used for service-to-service authentication
- `.env` file excluded from version control via `.gitignore`
- AI Search configured with `in_scope: true` to prevent hallucination outside the corpus

---

## 🧠 Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Search type | Hybrid + Semantic | Combines BM25 keyword matching with vector similarity for best accuracy |
| Chunk size | 1024 tokens | Large enough to capture full policy clauses, small enough for precision |
| Embedding model | text-embedding-ada-002 | Cost-effective, proven performance for English policy text |
| RAG approach | Azure AI Search "Add your data" | Native Azure integration, no custom orchestration needed |
| UI framework | Streamlit | Rapid prototyping, free cloud deployment, Python-native |

---

## 📁 Project Structure

```
nhs-policy-assistant/
├── app.py                        # Main Streamlit application
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .gitignore                    # Excludes .env and secrets
├── streamlit_secrets_template.toml  # Streamlit Cloud secrets reference
└── README.md                     # This file
```

---




## 👨‍💻 About Me & Why I Built This

My name is **Syed Ali Haider** and I'm transitioning into AI roles.

The idea for this project came from a personal experience. My spouse recently moved to 
the UK and started working for the NHS. She would regularly come home with questions 
about her employment rights — sick pay, leave entitlements, workplace policies — and 
we'd spend ages searching through lengthy NHS documents trying to find a clear answer. 
That frustration became the inspiration for this assistant.

NHS staff — doctors, nurses, admin — deserve quick, clear answers about their own 
rights without having to wade through 100+ page policy documents, often during already 
stressful situations. This assistant changes that.

**What this project taught me that no tutorial covers:**  
The hardest part wasn't the code — it was configuring RBAC and Managed Identity 
permission chains across Azure Storage, AI Search, Foundry, and Document Intelligence. 
Real Azure deployments are about permissions as much as architecture. I debugged every 
error, understood every fix, and built something that genuinely works end-to-end.


---

## ⚠️ Disclaimer

This assistant provides general information based on NHS policy documents for demonstration purposes. It does not constitute legal or HR advice. Policies may vary between NHS Trusts and Deaneries — always consult your specific Trust HR department, Deanery, line manager, or trade union representative for advice applicable to your situation.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for NHS staff by Syed Ali Haider | Powered by Microsoft Azure*
[GitHub](https://github.com/alihaider1993) · [LinkedIn](https://www.linkedin.com/in/syed-ali-haider-43777821)