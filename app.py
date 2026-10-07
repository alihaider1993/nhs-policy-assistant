# NHS Employee Policy Assistant
# Author: Syed Ali Haider 
# GitHub: github.com/alihaider1993/nhs-policy-assistant


# I built this to help NHS staff find clear answers about their employment
# rights without reading through lengthy policy documents. The assistant
# uses a RAG pipeline over 15 official NHS documents, powered by
# Azure OpenAI (GPT-4.1 mini) with in-memory BM25 search over the documents.

import json
import os
import re

import requests
import streamlit as st
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

st.set_page_config(page_title="NHS AI Policy Assistant", layout="wide")

st.title("🏥 NHS Employee Policy Assistant (AI RAG)")
st.write("Ask questions about NHS policies, leave, bullying, whistleblowing, and more.")

# =========================
# 🔐 AZURE CONFIG
# Streamlit Cloud reads these from Settings → Secrets; locally they come from .env
# =========================
load_dotenv()


def setting(name, default=""):
    try:
        return st.secrets[name]
    except Exception:  # no secrets.toml locally — fall back to environment
        return os.getenv(name, default)


AZURE_OPENAI_ENDPOINT = setting("AZURE_OPENAI_ENDPOINT").rstrip("/")
AZURE_OPENAI_KEY      = setting("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME       = setting("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")

if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
    st.error(
        "The assistant isn't configured yet: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY "
        "are missing. Add them in Streamlit → Settings → Secrets (or .env locally)."
    )
    st.stop()

# Chunks built from the NHS PDFs by ingest.py
CHUNKS_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chunks.json")
TOP_N_CHUNKS = 5

# Guards for a public URL — every question is billed per token
MAX_QUESTION_CHARS        = 500
MAX_QUESTIONS_PER_SESSION = 20

# =========================
# 💡 SUGGESTED QUESTIONS
# Questions I chose based on real NHS staff concerns
# =========================
SUGGESTED_QUESTIONS = [
    "I've been off sick for 3 weeks — what happens to my pay?",
    "My manager is making my life difficult — what are my options?",
    "Can I take unpaid leave to care for a family member?",
    "What counts as gross misconduct in the NHS?",
    "Am I entitled to a phased return after long-term sickness?",
    "How do I report something confidentially without fear of retaliation?",
    "What is my notice period as a Band 6 physiotherapist?",
    "Can my employer change my shift pattern without my agreement?",
]

# =========================
# 🧠 SYSTEM PROMPT
# Designed by Syed Ali Haider
# Goal: balance policy accuracy with empathy for frontline NHS staff
# =========================
SYSTEM_PROMPT = """You are an NHS Employee Policy Assistant — a trusted, professional resource 
for NHS staff including doctors, nurses, and administrative personnel.

Your role is to help staff understand their employment rights, workplace policies, and entitlements 
by answering questions clearly and accurately based on official NHS policy documents.

Guidelines:
- Always cite the specific NHS policy document or section you are referencing
- Use plain English — avoid jargon where possible
- Be empathetic and professional in tone
- If a question falls outside your knowledge base, say so honestly
- For urgent or sensitive matters (e.g. bullying, harassment, whistleblowing), remind staff of confidential support routes
- Always remind staff that policies may vary between NHS Trusts and Deaneries — encourage them to contact their local Trust HR department or Deanery for advice specific to their situation

Grounding rules:
- Answer only from the numbered sources supplied below — never from general knowledge
- Cite each fact with its source number in square brackets, e.g. [2]
- If the sources don't answer the question, say you couldn't find it in the NHS policy documents and suggest contacting local HR
- Politely decline questions unrelated to NHS employment policy"""

NOT_FOUND_ANSWER = (
    "I couldn't find anything about that in the NHS policy documents I have. "
    "Try rephrasing your question, or contact your local Trust HR department."
)
# =========================
# CHAT HISTORY
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar with suggested questions
with st.sidebar:
    st.markdown("## 💡 Suggested Questions")
    st.markdown("Click any question to ask it:")
    for q in SUGGESTED_QUESTIONS:
        if st.button(q, key=q):
            st.session_state["pending_question"] = q

    st.markdown("---")
    st.markdown("""
    **📋 Documents indexed:**
    - AfC Handbook v60 (2026)
    - NHS People Promise
    - Grievance & Disciplinary Policies
    - Maternity, Adoption & Parenting Leave
    - Flexible Working Toolkit
    - Civility & Respect Toolkit
    - Health & Wellbeing at Work
    - EDI Workforce Plan
    - Pay & Conditions Circular 2026
    - and more...
    """)
    st.markdown("---")
    st.caption("Built by Syed Ali Haider · AI-102 Certified")

# Render existing chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# =========================
# RETRIEVAL
# BM25 keyword search over the chunks in data/chunks.json — runs in memory,
# so there is no search service to host or pay for
# =========================
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "do", "does", "for", "from",
    "how", "i", "if", "in", "is", "it", "my", "of", "on", "or", "the", "to",
    "what", "when", "which", "who", "will", "with", "you", "your",
}


def tokenize(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    # Crude plural folding so "days" matches "day"
    return [w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w
            for w in words if w not in STOPWORDS]


@st.cache_resource
def load_index():
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    bm25 = BM25Okapi([tokenize(f"{c['title']} {c['content']}") for c in chunks])
    return chunks, bm25


def retrieve(query):
    chunks, bm25 = load_index()
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:TOP_N_CHUNKS]
    return [chunks[i] for i in ranked if scores[i] > 0]


# =========================
# RAG FUNCTION
# Retrieves the best chunks, then asks the model to answer only from them
# =========================
def call_rag(question, history):
    # Include the previous question so follow-ups like "what about after 5 years?" still match
    previous = [m["content"] for m in history if m["role"] == "user"][-1:]
    sources = retrieve(" ".join(previous + [question]))
    if not sources:
        return {"answer": NOT_FOUND_ANSWER, "sources": []}

    context = "\n\n".join(
        f"[{n}] {s['title']} (page {s['page']})\n{s['content']}"
        for n, s in enumerate(sources, start=1)
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-6:]:  # last 3 turns for context
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "system", "content": f"Sources from the NHS policy documents:\n\n{context}"})
    messages.append({"role": "user", "content": question})

    url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}"
        f"/chat/completions?api-version=2024-10-21"
    )
    headers = {"Content-Type": "application/json", "api-key": AZURE_OPENAI_KEY}
    payload = {"messages": messages, "temperature": 0.3, "max_tokens": 1000}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            return {"error": "The assistant is busy right now. Please wait a minute and try again."}
        return {"error": f"The policy service returned an error ({e.response.status_code}). Please try again shortly."}
    except requests.exceptions.RequestException:
        return {"error": "Couldn't reach the policy service. Check your connection and try again."}

    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 1 <= int(n) <= len(sources)})
    # Remove [1] style inline tags — cleaner for end users; sources are listed below
    answer = re.sub(r"\s*\[\d+\]", "", answer).strip()
    return {"answer": answer, "sources": [sources[n - 1] for n in cited]}


# =========================
# HANDLE INPUT
# Covers both chat input and sidebar button clicks
# =========================
user_input = st.chat_input("Ask an NHS policy question...")

# Handle sidebar suggested question clicks
if "pending_question" in st.session_state and st.session_state["pending_question"]:
    user_input = st.session_state["pending_question"]
    st.session_state["pending_question"] = None

questions_asked = sum(1 for m in st.session_state.messages if m["role"] == "user")
if user_input and len(user_input) > MAX_QUESTION_CHARS:
    st.warning(f"Please keep your question under {MAX_QUESTION_CHARS} characters.")
    user_input = None
elif user_input and questions_asked >= MAX_QUESTIONS_PER_SESSION:
    st.warning(
        f"You've reached the {MAX_QUESTIONS_PER_SESSION}-question limit for this demo session. "
        "Clear the conversation to start again."
    )
    user_input = None

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching NHS policy documents..."):
            result = call_rag(user_input, st.session_state.messages[:-1])

        if "error" in result:
            answer = f"❌ {result['error']}"
            st.error(answer)
        else:
            answer = result["answer"]
            st.markdown(answer)

            # Show source citations, one line per document with its pages
            pages_by_title = {}
            for source in result["sources"]:
                pages_by_title.setdefault(source["title"], set()).add(source["page"])
            if pages_by_title:
                st.markdown("---")
                st.markdown("**📚 Sources**")
                for title, pages in pages_by_title.items():
                    page_list = ", ".join(str(p) for p in sorted(pages))
                    st.caption(f"📄 {title} — p. {page_list}")

    st.session_state.messages.append({"role": "assistant", "content": answer})

# Clear conversation button
if st.session_state.messages:
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

# Personal footer
st.markdown("""
> ⚠️ **Disclaimer:** This assistant provides general information based on official NHS 
> policy documents. It does not constitute legal or HR advice. Policies may vary between 
> NHS Trusts and Deaneries — always consult your specific Trust HR department, Deanery, 
> line manager, or trade union representative for advice applicable to your situation.
""")
st.caption(
    "Built by Syed Ali Haider . "
    "[GitHub](https://github.com/alihaider1993/nhs-policy-assistant) . "
    "[LinkedIn](https://www.linkedin.com/in/syed-ali-haider-43777821)"
)
