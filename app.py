# NHS Employee Policy Assistant
# Author: Syed Ali Haider 
# GitHub: github.com/alihaider1993/nhs-policy-assistant
# Built: June 2026
#
# I built this to help NHS staff find clear answers about their employment
# rights without reading through lengthy policy documents. The assistant
# uses a RAG pipeline over 16+ official NHS documents, powered by
# Azure OpenAI (GPT-4o) and Azure AI Search with hybrid semantic search.

import streamlit as st
import requests
import os
import re

st.set_page_config(page_title="NHS AI Policy Assistant", layout="wide")

st.title("🏥 NHS Employee Policy Assistant (AI RAG)")
st.write("Ask questions about NHS policies, leave, bullying, whistleblowing, and more.")

# =========================
# 🔐 AZURE CONFIG
# =========================
AZURE_OPENAI_ENDPOINT = "https://foundry-nhs-employee-assistant.openai.azure.com"
AZURE_OPENAI_KEY      = st.secrets.get("AZURE_OPENAI_KEY", os.getenv("AZURE_OPENAI_KEY", ""))
DEPLOYMENT_NAME       = "gpt-4o"

SEARCH_ENDPOINT = "https://nhs-search-basic.search.windows.net"
SEARCH_KEY      = st.secrets.get("AZURE_SEARCH_KEY", os.getenv("AZURE_SEARCH_KEY", ""))
SEARCH_INDEX    = "nhs-policy"

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
- Always remind staff that policies may vary between NHS Trusts and Deaneries — encourage them to contact their local Trust HR department or Deanery for advice specific to their situation"""
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
    - NHS Constitution 2023
    - Grievance & Disciplinary Policies
    - Whistleblowing / Freedom to Speak Up
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
# RAG FUNCTION
# Fixed to match Azure Foundry exactly:
# - semantic search (not simple)
# - correct API version
# - semantic configuration name
# - in_scope + strictness to match Foundry defaults
# =========================
def call_rag(question, history):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }

    # Build messages with conversation history (like Foundry does)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-6:]:  # last 3 turns for context
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": question})

    payload = {
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1000,
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": SEARCH_ENDPOINT,
                    "index_name": SEARCH_INDEX,
                    "authentication": {
                        "type": "api_key",
                        "key": SEARCH_KEY
                    },
                    "query_type": "semantic",
                    "semantic_configuration": "nhs-policy-semantic-configuration",
                    "top_n_documents": 5,
                    "in_scope": True,
                    "strictness": 3,
                }
            }
        ]
    }

    url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}"
        f"/chat/completions?api-version=2024-05-01-preview"
    )

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code} — {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


# =========================
# HANDLE INPUT
# Covers both chat input and sidebar button clicks
# =========================
user_input = st.chat_input("Ask an NHS policy question...")

# Handle sidebar suggested question clicks
if "pending_question" in st.session_state and st.session_state["pending_question"]:
    user_input = st.session_state["pending_question"]
    st.session_state["pending_question"] = None

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching NHS policy documents..."):
            result = call_rag(user_input, st.session_state.messages[:-1])

        if "error" in result:
            answer = f"❌ Error: {result['error']}"
            st.error(answer)
        else:
            try:
                answer = result["choices"][0]["message"]["content"]

                # Remove [doc1] style inline tags — cleaner for end users
                answer = re.sub(r'\[doc\d+\]', '', answer).strip()

                st.markdown(answer)

                # Show source citations
                try:
                    citations = (
                        result["choices"][0]["message"]
                        .get("context", {})
                        .get("citations", [])
                    )
                    if citations:
                        st.markdown("---")
                        st.markdown("**📚 Sources**")
                        seen = set()
                        for c in citations:
                            title = (
                                c.get("title")
                                or c.get("filepath", "NHS Policy Document")
                            )
                            title = (
                                title.replace(".pdf", "")
                                     .replace("-", " ")
                                     .replace("_", " ")
                                     .title()
                            )
                            if title not in seen:
                                st.caption(f"📄 {title}")
                                seen.add(title)
                except Exception:
                    pass

            except Exception:
                answer = str(result)
                st.markdown(answer)

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
