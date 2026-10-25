# BrandShield AI — CodeVertex Round 2 MVP

A working prototype of the Round 1 proposal: explainable, human-controlled pre-publication content review.

## What is implemented
- Brand guideline management: add/delete prohibited terms, required terms, fact/source notes, and tone guidelines.
- Content review: submit a draft and receive findings from configured rules plus transparent heuristic checks for absolute claims.
- Explanations: category, severity, matched wording, evidence note, and suggested action.
- Human review workflow: save revisions/notes and set a review to Under Review, Revision Requested, Approved, or Rejected.
- SQLite persistence for rules and reviews.
- Review history and status filtering.
- Responsive React interface.

## Important limitations (be transparent with judges)
- This MVP uses deterministic rule checks and simple pattern matching, not a trained machine-learning model or external generative AI integration.
- It does not independently verify factual claims. “Unsupported” means a claim needs human/source verification; it is not a finding of falsity.
- Visual/OCR checks, authentication, multi-user roles, file uploads, and enterprise analytics are not implemented in this MVP.
- Default rules are demo data. Replace or add rules to match the test brand you demonstrate.

## Requirements
- Python 3.10+ (Python 3.11 recommended)
- Node.js 20+ and npm

## Run locally on Windows (VS Code)
Open two terminals.

### Terminal 1 — Flask backend
```powershell
cd brandshield-ai\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py app.py
```
Backend: http://127.0.0.1:5000
Health check: http://127.0.0.1:5000/api/health

If PowerShell blocks activation, run `py -m pip install -r requirements.txt` without activating the environment, or use Command Prompt and `.venv\Scripts\activate.bat`.

### Terminal 2 — React frontend
```powershell
cd brandshield-ai\frontend
npm install
npm run dev
```
Open the local URL Vite prints (normally http://localhost:5173). Keep both terminals running.

## Deployment notes
The frontend and backend are separate services. Deploy the Flask backend first, then set `VITE_API_URL` to the public backend URL when building the frontend. Deploy the built frontend as a static site. Configure the backend's `BRANDSHIELD_DB` to a persistent disk path on your host; an ephemeral filesystem can reset the SQLite database. Test the public URL in a private/incognito browser before submitting. Never include secrets in frontend code.

## API endpoints
- `GET /api/health`
- `GET /api/rules`, `POST /api/rules`, `DELETE /api/rules/<id>`
- `POST /api/analyse`
- `GET /api/reviews`
- `PATCH /api/reviews/<id>`

## Demo flow for judges
1. Open Brand guidelines and show seeded rules; add a prohibited term such as `miracle cure`.
2. Return to Content review and analyse: `Guaranteed 100% results for everyone.`
3. Show severity, explanation, evidence note, and suggested action.
4. Enter a revised statement, save revision, then approve or reject it.
5. Open Review history and show the saved item/status.
6. Add a rule and run a second draft to demonstrate configurable checks.

## Suggested Round 3 improvements
1. Evidence-grounded retrieval from approved documents with source snippets and citation links.
2. Image/document checks for logos, accessibility, and visual brand rules.
3. Multi-user reviewer roles, audit logs, and analytics for recurring violations.
