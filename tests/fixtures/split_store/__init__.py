"""Known-answer fixture corpus for the split-store E2E acceptance test.

Author: Claude (Stream 1)
Created: 2026-09-27
Scope: SLICE-49B "Test infrastructure" — a few short text documents plus 5
       queries, each with one known relevant passage, embedded by a
       deterministic bag-of-words test embedder (no model download, no
       network). Recall assertions are meaningful: each query's tokens
       overlap distinctly with its target document and only weakly with the
       four distractor documents, so a real cosine-similarity ranking (not a
       fixture that fakes the outcome) puts the known passage at the top.

Layout:
  docs/*.txt      — five short documents, one topic each (financial aid,
                    library hours, course registration, campus housing,
                    health insurance).
  queries.json    — one persona, 5 questions, ``server.core.query_loader``
                    format (matches production ``queries_file`` shape).

``EXPECTED_KEYWORDS`` maps each query's exact text to a lowercase keyword
that appears only in its target document — the test checks that keyword
against the ranked chunk text rather than tracking chunk_id <-> filename,
since the RecursiveCharacterTextSplitter chunk boundaries are an
implementation detail of ``chunk_text``, not a fixture contract.
"""

from __future__ import annotations

from pathlib import Path

FIXTURE_DIR = Path(__file__).parent
DOCS_DIR = FIXTURE_DIR / "docs"
QUERIES_FILE = FIXTURE_DIR / "queries.json"

# RecursiveCharacterTextSplitter(chunk_size=220, overlap=0) keeps each ~160-174
# char document as exactly one chunk (verified against the 5 fixture docs) —
# see docs/plan/slices/05-storage/SLICE-49B-VECTOR-STORE-DATA-PATH-REWIRE.md
# "Test infrastructure".
CHUNK_SIZE = 220
CHUNK_OVERLAP = 0

EXPECTED_KEYWORDS: dict[str, str] = {
    "When is the Pell Grant deadline?": "pell",
    "What time does the library close on weekends?": "library",
    "When does spring course registration open?": "registration",
    "When are on campus housing applications due?": "housing",
    "How do I enroll in student health insurance?": "insurance",
}
