# OpenShelf — Tech Stack and Project Requirements

## Project Goal
Build OpenShelf, a free book-discovery website where users can search for books by title or author and find legitimate free reading, lending, download, and preview options.

## Technology Stack
- Frontend: React, Vite, TypeScript
- Backend: Python, FastAPI, Uvicorn
- Book data: Open Library Search API
- Optional book previews: Google Books API
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