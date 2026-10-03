# OpenShelf

OpenShelf is a local, free book-discovery project built with React, Vite, TypeScript, and Python FastAPI. This repository is currently in Milestone 1: project foundation.

## Folder structure

```text
openshelf/
├── .gitignore
├── README.md
├── TECHSTACK.md
├── ANTIGRAVITY_INSTRUCTIONS.MD
├── frontend/
│   ├── package.json
│   ├── src/
│   └── vite.config.ts
├── backend/
│   ├── .gitignore
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       └── main.py
└── .venv/
```

## Windows PowerShell setup

Use these commands in PowerShell from the repository root.

> Important: this project works with Python 3.12. Python 3.14 caused a build failure for the FastAPI dependency stack, so the setup below uses the compatible interpreter.

If you do not already have Python 3.12 installed, run this once in a PowerShell window:

```powershell
winget install --id Python.Python.3.12 --source winget --accept-source-agreements --accept-package-agreements
```

Then continue with:

```powershell
# 1) Go to the project folder
cd "d:\openshelf\openshelf"

# 2) Make sure Python 3.12 is available
py -3.12 --version

# 3) Create a project virtual environment with Python 3.12
py -3.12 -m venv .venv

# 4) Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 5) Upgrade pip so installs are more reliable
python -m pip install --upgrade pip

# 6) Install the backend dependencies
cd backend
python -m pip install -r requirements.txt

# 7) Go back to the repo root and install frontend dependencies
cd ..
cd frontend
npm install
```

If PowerShell blocks activation with a policy error, run this once in the same PowerShell window:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then run the activation command again:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Run the app locally

### Start the backend

From the backend folder, run:

```powershell
cd "d:\openshelf\openshelf\backend"
. ..\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs

### Start the frontend

Open a second PowerShell window and run:

```powershell
cd "d:\openshelf\openshelf\frontend"
npm run dev -- --host 127.0.0.1
```

The frontend will be available at:

- http://127.0.0.1:5173/

## Notes

- This repository intentionally does not include secrets or uploaded PDFs.
- The backend is built with FastAPI and requires Python 3.12.
- The frontend is a Vite + React + TypeScript app.
- ClamAV is optional but recommended for PDF safety scanning. If installed, the backend will automatically use `clamscan` for threat detection.

## Run the Tests

To run the automated backend tests using Pytest, activate your virtual environment and run the following command from the `backend` folder:

```powershell
cd "d:\openshelf\openshelf\backend"
. ..\.venv\Scripts\Activate.ps1
pytest tests/
```
