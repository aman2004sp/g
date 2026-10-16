# GATE CS PYQ Lab

A local browser-based mock-test app generated from the uploaded GATE CS papers and answer keys. The 2021 paper is intentionally excluded, as requested.

## Run on Windows
1. Extract the ZIP.
2. Double-click `Run-GATE-Quiz.bat`.
3. Open `http://localhost:8000` if the browser does not open automatically.
4. Keep the terminal window open while using the app.

Python 3 is required; no external Python packages are required to run the quiz. The `build.py` PDF rebuild script uses PyMuPDF and Tesseract OCR for OCR fallback.

## Features
- Eight separate tests: 2022 CS1, 2023 CS1, 2024 CS1/CS2, 2025 CS1/CS2, 2026 CS1/CS2.
- Timer, question palette, previous/next navigation, mark-for-review, MCQ/MSQ/NAT input, submission, scoring, and JSON result export.
- **Original PDF page view inside each question.** The app embeds the corresponding page of the uploaded source PDF, so diagrams, graphs, tables, circuit drawings, and mathematical notation are shown from the original PDF rather than redrawn or approximated. Use the “View original PDF page” disclosure under each question to inspect it.
- `papers.json` is independent structured question data that can be reused by another frontend/backend. It includes `source_page`, `source_pdf`, answer keys, marks, sections, and review flags.
- `build.py` can regenerate `papers.json` from the PDFs in `source_pdfs/`.

## 2023 key note
The apparent missing entry was Q.27. The official answer-key PDF actually contains the entry `A, C, D OR C, D`; the earlier parser failed to understand this multiple-accepted-set format. The app now accepts either set for Q.27. This is based on the supplied answer key, not a guessed answer.

## Validation and limitations
- All eight included papers have 65 question records and 65 answer-key entries in the generated data; every question has a source-page mapping.
- Some text/options remain flagged for review where parsing was uncertain. The original PDF page is provided to inspect exact content and diagrams.
- The source page view is the authoritative visual reference; extracted text/options may still have OCR/layout artifacts and are not guaranteed pixel-identical to the interactive option labels.
- The application has been syntax/data-validated but not exhaustively browser-tested for every question. Review flagged questions before relying on a score.
- MCQ scoring uses -1/3 for 1-mark and -2/3 for 2-mark wrong answers; MSQ/NAT incorrect answers score zero. Verify any year-specific marking exceptions against official rules.

## Data schema
Each paper contains `id`, `title`, `source_pdf`, `key_pdf`, `pages`, `key_count`, `review_count`, and `questions`. Each question includes `number`, `text`, `options`, `answer`, `answer_variants`, `answer_raw`, `type`, `section`, `marks`, `source_page`, and `needs_review`.
