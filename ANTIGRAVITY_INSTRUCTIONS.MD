# OPENSHELF — COMPLETE PROJECT DEVELOPMENT INSTRUCTIONS

Act as a senior full-stack developer, software architect, security engineer, UI/UX designer, and QA engineer. Your responsibility is to turn the existing OpenShelf repository into a polished, reliable, secure, fully tested book-discovery application.

## PHASE 1 — AUDIT THE EXISTING PROJECT
- Inspect the entire repository.
- Identify what works, what is incomplete, and what must be preserved.
- Update `TECHSTACK.md` and `ANTIGRAVITY_INSTRUCTIONS.md`.

## PHASE 2 — APPROVED BOOK SOURCES
Use these ten sources as the approved book-discovery sources:
1. Open Library — https://openlibrary.org/
2. Internet Archive — https://archive.org/
3. Project Gutenberg — https://www.gutenberg.org/
4. Standard Ebooks — https://standardebooks.org/
5. ManyBooks — https://manybooks.net/
6. Feedbooks Public Domain — https://www.feedbooks.com/catalog/public_domain
7. OAPEN — https://www.oapen.org/
8. Directory of Open Access Books — https://www.doabooks.org/
9. OpenStax — https://openstax.org/
10. Open Textbook Library — https://open.umn.edu/opentextbooks

## PHASE 3 — IN-APP BOOK SEARCH
- Support searches by title, author, ISBN, and subject.
- Search the approved sources directly inside OpenShelf (no external primary search).
- Normalize metadata and deduplicate matching editions.
- Display comprehensive metadata (title, author, cover, year, edition, language, format, source, access type).

## PHASE 4 — CRITICAL: FIND COMPLETE BOOKS, NOT SHORT PREVIEWS
### A. Classify every result
Use these categories:
1. FULL BOOK — VERIFIED
2. COMPLETE BOOK — AUTHORIZED BORROWING REQUIRED
3. PREVIEW / SAMPLE / PARTIAL TEXT
4. COMPLETENESS UNVERIFIED

### B. Evidence-based verification
- Rely on explicit full-text metadata, official download records, table of contents, and document structure.
- Do not rely on just `.pdf` extension or successful opening.
- If insufficient evidence, mark as COMPLETENESS UNVERIFIED.

### C. Full-book filters
- Provide filters: All Results, Verified Full Books, Free Full-Text Downloads, Read Online, Borrow Full Book, Preview / Partial, Completeness Unverified.
- "Verified Full Books" filter must exclude previews, partial books, and unverified files.

### D. When a complete book cannot be found
- Do not fill results with short previews. Tell the user no verified complete version was found and offer legitimate alternatives.

## PHASE 5 — PDF DISCOVERY USING FILETYPE:PDF
- Support targeted searches combining title, author, approved source domains, and `filetype:pdf`.
- Every PDF candidate must go through the completeness-classification workflow.

## PHASE 6 — LEGAL ACCESS AND PRICE COMPARISON
- Prioritize legitimate free full-text books.
- Clearly distinguish free downloads, reading, borrowing, previews, and purchases.

## PHASE 7 — PDF SAFETY CHECKER
- Validate uploaded file type, PDF signature, and file size.
- Store temporarily, calculate SHA-256 hashes, use ClamAV when installed.
- Do not automatically upload to third-party services.
- Provide clear results and avoid absolute safety guarantees.

## PHASE 8 — SECURITY, PRIVACY, AND PERFORMANCE
- Validate inputs, set timeouts, handle concurrency.
- Ensure secure temporary-file handling, no hardcoded secrets, appropriate CORS.
- Prevent SSRF vulnerabilities.

## PHASE 9 — PROFESSIONAL UI/UX
- Responsive desktop/mobile layouts.
- Distinct access labels, accessible contrast, loading states.
- Preserve existing working behavior and visual identity where appropriate.

## PHASE 10 — AUTOMATED TESTING
- Update automated tests for search, integrations, timeouts, empty responses, duplicates, invalid files, and UI states.

## PHASE 11 — DOCUMENTATION AND REPOSITORY QUALITY
- Update `TECHSTACK.md`, `ANTIGRAVITY_INSTRUCTIONS.md`, `README.md`, `.env.example`, `.gitignore`.
- Provide exact Windows PowerShell commands.

## PHASE 12 — IMPLEMENTATION ORDER
1. Audit and update documentation.
2. Verify source integrations.
3. Implement backend book search for 10 sources.
4. Add source adapters.
5. Implement completeness classification.
6. Add search interface and filters.
7. Preserve and harden PDF safety checker.
8. Add error handling and security.
9. Add tests.
10. Improve UI.
11. Update README.
12. Verify functionality.