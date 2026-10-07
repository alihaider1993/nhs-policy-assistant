# NHS Employee Policy Assistant — index builder
# Author: Syed Ali Haider
#
# Turns the NHS policy PDFs in ./Uploads into text chunks saved to
# data/chunks.json. The app searches these chunks in memory (BM25), so there
# is no search service to pay for. Re-run this whenever the PDFs change and
# commit the updated data/chunks.json.
#
# Usage:
#   pip install pypdf
#   python ingest.py

import glob
import hashlib
import json
import os
import re

from pypdf import PdfReader

DOCS_DIR = "Uploads"
OUTPUT_PATH = os.path.join("data", "chunks.json")

# ~400 tokens per chunk with overlap, so a clause split across chunks is still found
CHUNK_CHARS = 1800
OVERLAP_CHARS = 250

# Readable names shown in the app's source citations
TITLES = {
    "2025_09_Disciplinary_Policy.pdf": "Disciplinary Policy (2025)",
    "B2044_NHS_EDI_Workforce_Plan.pdf": "NHS EDI Workforce Plan",
    "HEE National Relocation Framework Final 1 November 2020.pdf": "HEE National Relocation Framework",
    "NHS England » Data protection policy.pdf": "NHS England Data Protection Policy",
    "NHS-People-Promise.pdf": "NHS People Promise",
    "NHSi-Civility-and-Respect-Toolkit-v9.pdf": "NHS Civility and Respect Toolkit",
    "Parenting Leave Policy (HR 010 V3 March 2021) ext to November 2024.pdf": "Parenting Leave Policy",
    "Pay-and-Conditions-Circular-(MD)-1-2026_0.pdf": "Pay and Conditions Circular (MD) 1/2026",
    "Pay-and-Conditions-Circular-(MD)-1-2026_0 (1).pdf": "Pay and Conditions Circular (MD) 1/2026",
    "disciplinary_policy_and_procedure.pdf": "Disciplinary Policy and Procedure",
    "flexible-working-toolkit-for-individuals.pdf": "Flexible Working Toolkit",
    "guide-nhs-scotland-grievance-policy-guide-for-employees-1-2-last-updated-march-2026.pdf":
        "NHS Scotland Grievance Policy Guide",
    "heeoe_gpst_lead_employer_-_grievance_policy_and_procedure.pdf": "Grievance Policy and Procedure",
    "maternity_adoption_leave_policy_v_3_2.pdf": "Maternity and Adoption Leave Policy",
    "nhs-terms-and-conditions-of-service-handbook-Version 60.pdf":
        "NHS Terms and Conditions of Service Handbook (v60)",
    "promoting-health-and-wellbeing-and-attendance-at-work--2225_1.pdf":
        "Promoting Health, Wellbeing and Attendance at Work",
}


def clean_title(filename):
    stem = os.path.splitext(filename)[0]
    stem = re.sub(r"[_\-]+", " ", stem)
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
            # Prefer to end on a sentence; always advance at least half a chunk
            cut = buffer.rfind(". ", CHUNK_CHARS // 2, CHUNK_CHARS) + 1 or CHUNK_CHARS
            yield start_page, buffer[:cut].strip()
            buffer = buffer[cut - OVERLAP_CHARS:]
            start_page = page_number
    if buffer.strip():
        yield start_page, buffer.strip()


def build_chunks():
    chunks, seen_hashes = [], set()
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.pdf"))):
        with open(path, "rb") as f:
            digest = hashlib.md5(f.read()).hexdigest()
        filename = os.path.basename(path)
        if digest in seen_hashes:
            print(f"skip duplicate  {filename}")
            continue
        seen_hashes.add(digest)

        title = TITLES.get(filename, clean_title(filename))
        pdf_chunks = list(chunk_pdf(path))
        for page, text in pdf_chunks:
            chunks.append({"title": title, "page": page, "content": text})
        print(f"{len(pdf_chunks):5d} chunks  {title}")
    return chunks


def main():
    chunks = build_chunks()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=1)
    print(f"Saved {len(chunks)} chunks to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
