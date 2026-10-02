# Instructions for Building OpenShelf

You are building OpenShelf, a free book-discovery website.

Before coding:
1. Read TECHSTACK.md completely.
2. Inspect the repository and existing files.
3. Explain the implementation plan briefly.

Build in small, testable milestones.

## Milestone 1: Project foundation
- Create a React + Vite + TypeScript frontend.
- Create a Python FastAPI backend.
- Provide a clear project folder structure.
- Add .gitignore files or rules to prevent secrets, virtual environments, caches, and uploaded PDFs from entering Git.
- Write a README with exact Windows PowerShell setup commands.

## Milestone 2: Book search
- Integrate the Open Library Search API.
- Support searches by book title and author.
- Show book covers when available, title, author, publication information, and source links.
- Handle empty results, loading states, network failures, and API errors.
- Clearly label previews, online reading, lending, and downloads.
- Use only legitimate source links. Never invent URLs or bypass copyright restrictions.

## Milestone 3: PDF safety checks
- Allow users to select a local PDF for inspection.
- Validate file size, PDF signature, and file structure.
- Use pypdf for structural inspection.
- Calculate a SHA-256 hash.
- Integrate ClamAV when installed and available.
- Report whether malware scanning actually ran.
- Use these statuses when appropriate: No threats detected, Threat detected, Suspicious features found, Scanner unavailable, Could not verify.
- Explain that no scan guarantees complete safety.
- Never automatically upload user files to third-party services.
- Never fetch arbitrary URLs supplied by users.
- Use safe temporary files and clean them up reliably.
- Do not serve uploaded files publicly.

## Milestone 4: Quality and testing
- Add backend tests for validation, hashing, PDF handling, and scanner-unavailable cases.
- Test API errors and empty search results.
- Run available tests and fix errors.
- Document any dependencies or tools the user must install.
- Keep the project free to run locally.

## Working rules
- Do not use paid APIs or require paid subscriptions.
- Do not pretend an API, scanner, or test succeeded when it did not.
- Do not leave fake download links or placeholder functionality presented as complete.
- Explain commands before asking a beginner to run them.
- Implement one milestone at a time. Start with Milestone 1, verify it, and then continue.
- Never commit secrets, API keys, environment files, or user-uploaded PDFs.

Begin by inspecting the repository and implementing Milestone 1.