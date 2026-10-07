# NHS Employee Policy Assistant — index builder
# Author: Syed Ali Haider
#
# Rebuilds the Azure AI Search index from the NHS policy PDFs in ./Uploads.
# Text is extracted locally (no Document Intelligence, no embeddings) so the
# whole index fits on the Azure AI Search Free tier and costs nothing to build.
#
# Usage:
#   pip install -r requirements.txt pypdf
#   python ingest.py            # needs AZURE_SEARCH_* values in .env

import glob
import hashlib
import os
import re

import requests
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
SEARCH_ADMIN_KEY = os.environ["AZURE_SEARCH_KEY"]
SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "nhs-policy")
SEMANTIC_CONFIG = "nhs-policy-semantic-configuration"
API_VERSION = "2024-07-01"
DOCS_DIR = "Uploads"

# ~400 tokens per chunk with overlap, so a clause split across chunks is still found
CHUNK_CHARS = 1800
OVERLAP_CHARS = 250

HEADERS = {"Content-Type": "application/json", "api-key": SEARCH_ADMIN_KEY}

INDEX_SCHEMA = {
    "name": SEARCH_INDEX,
    "fields": [
        {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
        {"name": "content", "type": "Edm.String", "searchable": True, "analyzer": "en.microsoft"},
        {"name": "title", "type": "Edm.String", "searchable": True, "analyzer": "en.microsoft"},
        {"name": "filepath", "type": "Edm.String", "filterable": True},
        {"name": "url", "type": "Edm.String"},
        {"name": "page", "type": "Edm.Int32", "filterable": True},
    ],
    "semantic": {
        "configurations": [
            {
                "name": SEMANTIC_CONFIG,
                "prioritizedFields": {
                    "titleField": {"fieldName": "title"},
                    "prioritizedContentFields": [{"fieldName": "content"}],
                },
            }
        ]
    },
}


def clean_title(filename):
    stem = os.path.splitext(filename)[0]
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\s*\(\d+\)$", "", stem)  # "file (1)" download duplicates
    return re.sub(r"\s+", " ", stem).strip()


def chunk_pdf(path):
    """Yield (page_number, text) chunks, keeping the page each chunk starts on."""
    reader = PdfReader(path)
    buffer, start_page = "", 1
    for page_number, page in enumerate(reader.pages, start=1):
        text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
        if not text:
            continue
        if not buffer:
            start_page = page_number
        buffer = f"{buffer} {text}".strip()
        while len(buffer) >= CHUNK_CHARS:
            cut = buffer.rfind(". ", CHUNK_CHARS // 2, CHUNK_CHARS) + 1 or CHUNK_CHARS
            yield start_page, buffer[:cut].strip()
            buffer = buffer[cut - OVERLAP_CHARS:]
            start_page = page_number
    if buffer.strip():
        yield start_page, buffer.strip()


def build_documents():
    docs, seen_hashes = [], set()
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.pdf"))):
        with open(path, "rb") as f:
            digest = hashlib.md5(f.read()).hexdigest()
        filename = os.path.basename(path)
        if digest in seen_hashes:
            print(f"skip duplicate  {filename}")
            continue
        seen_hashes.add(digest)

        chunks = list(chunk_pdf(path))
        for i, (page, text) in enumerate(chunks):
            docs.append({
                "@search.action": "upload",
                "id": f"{digest[:12]}-{i:04d}",
                "content": text,
                "title": clean_title(filename),
                "filepath": filename,
                "url": "",
                "page": page,
            })
        print(f"{len(chunks):5d} chunks  {filename}")
    return docs


def main():
    base = f"{SEARCH_ENDPOINT}/indexes/{SEARCH_INDEX}"
    # Recreate the index so a rebuild never leaves stale chunks behind
    requests.delete(f"{base}?api-version={API_VERSION}", headers=HEADERS, timeout=30)
    r = requests.put(f"{base}?api-version={API_VERSION}", headers=HEADERS, json=INDEX_SCHEMA, timeout=30)
    r.raise_for_status()

    docs = build_documents()
    for i in range(0, len(docs), 500):
        batch = docs[i:i + 500]
        r = requests.post(
            f"{base}/docs/index?api-version={API_VERSION}",
            headers=HEADERS, json={"value": batch}, timeout=120,
        )
        r.raise_for_status()
        failed = [d["key"] for d in r.json()["value"] if not d["status"]]
        if failed:
            raise RuntimeError(f"{len(failed)} chunks failed to upload, e.g. {failed[:3]}")
    print(f"Uploaded {len(docs)} chunks to index '{SEARCH_INDEX}'")


if __name__ == "__main__":
    main()
