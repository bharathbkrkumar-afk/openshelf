# OpenShelf — Tech Stack and Project Requirements

## Project Goal
Build OpenShelf, a free book-discovery website where users can search for books by title or author and find legitimate free reading, lending, download, and preview options.

## Technology Stack
- Frontend: React, Vite, TypeScript
- Backend: Python, FastAPI, Uvicorn
- Approved Book Sources:
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
- PDF inspection: pypdf
- Malware scanning: ClamAV
- File hashing: Python hashlib using SHA-256
- Optional local history: SQLite

## Requirements
- No paid APIs or subscriptions.
- Must work locally on Windows.
- Responsive, modern, accessible user interface.
- Display book titles, authors, covers, and legitimate source links.
- Never invent download links or link to unauthorized copies.
- Clearly distinguish online reading, previews, lending, and downloads.
- Scan locally uploaded PDFs when scanning tools are available.
- Check PDF structure and calculate its SHA-256 hash.
- Report accurate scan statuses: No threats detected, Threat detected, Suspicious features found, Scanner unavailable, or Could not verify.
- Never claim that a file is guaranteed safe.
- Never automatically upload user files to external services.
- Do not download arbitrary URLs for scanning.
- Validate file type and size, use temporary storage safely, and delete temporary files after processing.
- Include helpful error messages and a clean README with Windows setup instructions.
- Add tests for important backend functionality.

## Full-Book Access Requirements

### 1. Prioritize complete editions
- Search authorized sources for complete, full-text books and complete PDF editions where available.
- Search public-domain libraries, official publisher websites, legitimate open-access repositories, and library borrowing services.
- Use official APIs and permitted search mechanisms to discover relevant editions.
- A search query containing `filetype:pdf` is only a discovery technique. It does NOT prove that the PDF contains the entire book.

### 2. Verify completeness before labeling a result
Classify each result as one of the following:
- **Full book — verified:** Reliable source metadata explicitly identifies a complete edition, or completeness has been checked using permitted metadata or document inspection.
- **Borrowable full book:** The library source offers the complete book for borrowing, subject to its access rules.
- **Preview/sample only:** The source explicitly limits access to a sample, preview, or selected pages.
- **Completeness unknown:** The available evidence is insufficient to establish whether the full book is present.

Do not label a book as verified complete merely because:
- Its filename ends in `.pdf`.
- The PDF opens successfully.
- The title and author match the requested book.
- A search result says "free PDF."
- A preview contains some chapters or pages.

### 3. Reject incomplete versions when searching for the full book
- If a source explicitly identifies a result as a sample, excerpt, preview, or partial edition, do not present it as the requested full book.
- Prefer complete editions over previews when both are available.
- If only previews or incomplete copies are found, clearly say that a verified complete version was not found.
- Never fabricate download links or bypass publisher restrictions, DRM, library lending controls, or paywalls.
- If a full version is available only through authorized borrowing or purchase, explain that clearly.

### 4. Improve the book results interface
For each result, show:
- Book title and author.
- Edition or publication details when available.
- Access type: Full text, Borrow, Preview only, Purchase, or Unknown.
- File format when verified.
- Source and a legitimate link to read, borrow, or purchase.
- A clear completeness indicator that distinguishes verified information from unverified claims.

Add a filter such as **Full books only**. When enabled, exclude previews and results whose completeness is unknown. Borrowable full books may remain visible in a separate clearly labeled section.

### 5. Be honest about verification
Do not promise that every book can be found in full for free. If the available APIs cannot verify completeness, mark the result as unknown rather than guessing. Explain when a source requires an account, borrowing period, or payment.