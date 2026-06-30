# Sentinel — AI-Assisted Document Anonymization

> A full-stack review workspace for detecting, reviewing, and correcting PII in documents using regex, heuristic rules, and Gemini AI.
---

## Quick Start

```bash
# 1. Backend — install dependencies
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -e .

# 2. Backend — copy env and add your Gemini API key
cp .env.example .env
# Edit .env: set GEMINI_API_KEY="your-key-here"

# 3. Backend — start the API server
uvicorn app.main:app --reload --port 8000
```

```bash
# 4. Frontend — install dependencies
cd frontend
npm install

# 5. Frontend — start the dev server
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** → upload a document → detection runs automatically → review workspace opens.

The frontend proxies `/api/*` to `http://localhost:8000/api/*` via Next.js rewrites (see `frontend/next.config.ts`).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 16)                    │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │   Pages   │  │    Components    │  │     Stores        │  │
│  │  /upload  │  │  DocumentViewer  │  │  document-store   │  │
│  │ /document │  │  ReviewQueue     │  │  review-store     │  │
│  │  /[id]    │  │  CorrectionBar   │  │  detection-store  │  │
│  │ /history  │  │  AddPiiPopover   │  │  risk-store       │  │
│  │ /settings │  │  EntityDrawer    │  │  ui-store         │  │
│  └──────────┘  └──────────────────┘  └───────────────────┘  │
│                      │  │         │                          │
│                 ┌─────┘  │  ┌─────┘                          │
│                 ▼        ▼  ▼                                 │
│          ┌────────────────────────┐                           │
│          │   Services / Hooks     │                           │
│          │  api-client.ts         │                           │
│          │  use-review-actions.ts │                           │
│          └───────────┬────────────┘                           │
└──────────────────────┼────────────────────────────────────────┘
                       │  HTTP (localhost:3000 → localhost:8000)
┌──────────────────────┼────────────────────────────────────────┐
│  Backend (FastAPI)   ▼                                        │
│  ┌─────────────────────────────────────────────────────┐      │
│  │                    Routes                            │      │
│  │  /documents/upload →  DetectionPipeline             │      │
│  │  /detection/run   →  RegexDetector                  │      │
│  │  /review/*        →  RuleDetector                    │      │
│  │  /risk/assess     →  GeminiDetector                  │      │
│  │  /export/*        →  EntityMerger                    │      │
│  │                    →  ConflictResolver               │      │
│  │                    →  ConfidenceEngine               │      │
│  └─────────────────────────────────────────────────────┘      │
│                        │                                       │
│  ┌─────────────────────▼───────────────────────────────┐      │
│  │                   Services                           │      │
│  │  DocumentService  DetectionService  ReviewService   │      │
│  │  RiskService      ExportService     AuditService    │      │
│  │  PriorityEngine   ValidationService HistoryService  │      │
│  └─────────────────────┬───────────────────────────────┘      │
│                        │                                       │
│  ┌─────────────────────▼───────────────────────────────┐      │
│  │                 Stores (in-memory)                   │      │
│  │  InMemoryDocumentStore  InMemoryReviewStore          │      │
│  └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
SprintFour/
├── backend/                         # FastAPI Python backend
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── main.py              # Router assembly
│   │   │   ├── schemas/responses.py # API envelope shapes
│   │   │   └── v1/
│   │   │       └── routes/          # Route handlers
│   │   │           ├── health.py    # Health check
│   │   │           ├── documents.py # Upload + retrieve
│   │   │           ├── detection.py # Run PII detection
│   │   │           ├── review.py    # Human review CRUD + batch
│   │   │           ├── risk.py      # Risk assessment
│   │   │           └── export.py    # Validate + redact + export
│   │   ├── core/                    # Config, exceptions, middleware
│   │   ├── detectors/               # PII detection strategies
│   │   │   ├── base.py              # Abstract detector
│   │   │   ├── entity_types.py      # 20+ PII categories (enum)
│   │   │   ├── regex_detector.py    # 16 compiled patterns
│   │   │   ├── rule_detector.py     # Heuristic rules
│   │   │   └── gemini_detector.py   # Gemini AI detector
│   │   ├── domain/models/           # Detection, Document, Review, Risk, Export
│   │   ├── pipeline/                # Detection orchestration
│   │   │   ├── detection_pipeline.py# 7-stage pipeline
│   │   │   ├── entity_merger.py     # Dedup overlapping spans
│   │   │   ├── conflict_resolver.py # Resolve type conflicts
│   │   │   └── confidence_engine.py # Calibrate scores
│   │   ├── extractors/              # TXT / PDF (PyMuPDF) / DOCX
│   │   ├── normalizer/              # Text normalization
│   │   ├── export/                  # Redaction + formatting
│   │   ├── services/                # Business logic
│   │   │   ├── document_service.py  # Ingestion lifecycle
│   │   │   ├── detection_service.py # Pipeline orchestration
│   │   │   ├── review_service.py    # Review operations
│   │   │   ├── audit_service.py     # Append-only event log
│   │   │   ├── history_service.py   # Undo/redo stacks
│   │   │   ├── priority_engine.py   # Queue prioritisation
│   │   │   └── risk_service.py      # Risk scoring
│   │   ├── providers/               # Gemini provider
│   │   └── store/                   # In-memory stores
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/                        # Next.js 16 + React 19
│   ├── app/                         # App Router pages
│   │   ├── page.tsx                 # Dashboard / document list
│   │   ├── document/[id]/page.tsx   # Review workspace
│   │   ├── history/[id]/page.tsx    # Audit trail
│   │   └── settings/page.tsx        # User preferences
│   ├── components/
│   │   ├── workspace/
│   │   │   └── review-workspace.tsx # Main orchestrator
│   │   ├── document/
│   │   │   ├── document-viewer.tsx  # Text renderer + text selection
│   │   │   ├── entity-highlight.tsx # Colour-coded entity spans
│   │   │   ├── add-missed-pii-popover.tsx  # Floating type picker
│   │   │   └── document-navigator.tsx      # Page thumbnails
│   │   ├── review/
│   │   │   ├── review-queue.tsx     # Sidebar queue with sections
│   │   │   ├── review-card.tsx      # Entity card with batch checkbox
│   │   │   ├── correction-toolbar.tsx # Mode toggle + batch actions
│   │   │   ├── filter-panel.tsx     # Queue filter pills
│   │   │   ├── risk-panel.tsx       # Risk score summary
│   │   │   └── search-bar.tsx       # Queue search
│   │   ├── layout/                  # AppLayout, Toolbar, StatusBar, Sidebar
│   │   ├── modals/                  # ExportModal, ValidationModal
│   │   ├── entity-drawer.tsx        # Entity detail slide-over
│   │   └── undo-snackbar.tsx        # Undo notification
│   ├── hooks/
│   │   ├── use-review-actions.ts    # Approve/reject/add/batch/undo
│   │   ├── use-workspace-data.ts    # Load document + detection + risk
│   │   └── use-keyboard-shortcuts.ts# ⌨️ Full shortcut map
│   ├── stores/                      # Zustand stores
│   │   ├── document-store.ts
│   │   ├── detection-store.ts
│   │   ├── review-store.ts
│   │   ├── risk-store.ts
│   │   └── ui-store.ts             # + HistoryStore, + Correction state
│   ├── services/                    # API client wrappers
│   └── lib/                         # Types, mappers, utils
│       └── types.ts                 # 270+ lines of TypeScript types
│
├── participant.md                   # Author info
├── test-doc.txt                     # Sample document for testing
└── Dharshan_CV.pdf                  # Sample document for testing
```

---

## Key Features

### 1. Multi-Strategy Detection Pipeline

| Detector | Method | Confidence | Covers |
|---|---|---|---|
| **Regex** | 16 compiled patterns | 0.99 | Email, PAN, Aadhaar, Credit Card, Phone, URLs, IPs, Driving License, Voter ID, Passport, IFSC, UPI, MAC, Bank Account |
| **Rule** | Honorific matching + label-value pairs | 0.75 | Person names (Mr/Dr/Prof), labelled PII (DOB, Phone, Email in key:value format) |
| **Gemini** | AI prompt + response parsing | 0.60–0.95 | Anything the regex/rule detectors might miss; hallucinations filtered via substring validation |

Pipeline stages: `Regex → Rule → Gemini → Merge → Resolve Conflicts → Calibrate Confidence → Build Summary`

### 2. Risk-Based Review Queue

Entities are sorted into queue sections by priority:

| Section | Criteria |
|---|---|
| **Critical missed PII** | Sensitivity ≥ 0.85 (govt IDs, financial) |
| **High-risk unresolved** | Sensitivity + unreviewed or low confidence |
| **Low confidence** | AI confidence < 0.7 (most likely false positives) |
| **False positives** | Marked as rejected by the reviewer |
| **Reviewed** | Approved or manually added |

Risk score = weighted combination of unreviewed ratio (50%), sensitivity (30%), and confidence (20%).

### 3. Human Review (Approve / Reject / Edit / Add / Delete)

- Single-key shortcuts: `Enter` = approve, `Delete/Backspace` = reject
- Each action is validated, audit-logged, and undo-able
- Auto-advance to next unresolved entity after each action
- Batch approve/reject from the correction toolbar

### 4. Correction Experience (Problem 3)

See dedicated section below.

### 5. Export with Validation

- Validation checks: critical unreviewed items, invalid offsets, empty fields
- Export formats: TXT (redacted text), JSON (full report)
- Supports human-in-the-loop: validation modal warns before export

---

## Correction Experience Deep-Dive

The correction mode helps a human reviewer quickly fix two common AI failure modes: **false positives** (tool flagged something that isn't PII) and **missed PII** (tool didn't flag something that is PII).

### Four Modes

| Mode | Triggers | What the reviewer does |
|---|---|---|
| **Review** (default) | Normal review | Approve/reject with keyboard shortcuts, scroll queue |
| **Missed PII** | Suspect tool missed something | Select text in document → floating popover appears → pick entity type → detection is created |
| **False positives** | Tool made too many errors | Entities shown struck-through in amber; batch-select and reject all at once |
| **All mistakes** (diff) | Want to see what changed | Colour-coded dots: 🟢 approved / 🟡 false positive / 🔵 manually added / 🔴 pending |

### Adding Missed PII Flow

```
1. User clicks "Missed PII" mode button
   → Document viewer shows rose-tinged gaps (un-flagged text)
   → Review queue auto-filters to show manually added entities

2. User selects text in the document viewer
   → DOM Range API captures selection offsets, page number, text
   → TextSelectionRange stored in UI store
   → "Mark as missed PII" button appears in correction toolbar

3. User clicks "Mark as missed PII" or presses Ctrl+Shift+M
   → AddMissedPiiPopover floats near the selection
   → Quick-type grid: PERSON, PHONE, EMAIL, AADHAAR, PAN, etc.
   → Custom type input for edge cases

4. User picks an entity type
   → useReviewActions.add() called
   → Backend: POST /api/v1/review/add with offsets + type
   → Detection created with review_state = "manually_added"
   → Workspace refreshes → new entity appears in queue
```

### Batch Operations

- Checkbox on each review card toggles selection
- Correction toolbar shows `{N} / {M} selected` counter
- "Select all" / "Deselect all" toggle
- "Approve all" and "Reject all" buttons
- Calls `POST /api/v1/review/batch-approve` or `POST /api/v1/review/batch-reject`

### Visual Indicators (per mode)

| Mode | Entity highlight style |
|---|---|
| Review (off) | Standard coloured underlines per entity type |
| Missed PII (`spot_missed`) | Rose-tinged gaps, manually added in cyan border |
| False positives (`review_false_positives`) | Amber struck-through text |
| Diff (`diff`) | Dot indicators + tooltips explaining state |

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Enter` | Approve active entity |
| `Delete` / `Backspace` | Reject active entity |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / Redo |
| `Ctrl+E` | Open export validation |
| `Ctrl+F` | Focus queue search |
| `Tab` / `Shift+Tab` | Next / Previous unresolved entity |
| `↑` / `↓` | Previous / Next entity |
| `←` / `→` | Previous / Next occurrence |
| `Space` | Toggle entity detail drawer |
| `E` | Edit active entity |
| `A` | Add new detection |
| `Ctrl+Shift+M` | Add missed PII from selection |
| `Escape` | Close drawer / modals / popover |

---

## API Overview

All endpoints are proxied via Next.js rewrites. Full API at `http://localhost:8000/docs` (Swagger UI).

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Health check + uptime |
| `POST` | `/api/v1/documents/upload` | Upload TXT/PDF/DOCX (multipart) |
| `GET` | `/api/v1/documents/{id}` | Retrieve document metadata |
| `POST` | `/api/v1/detection/run` | Run full detection pipeline |
| `POST` | `/api/v1/review/items` | List review items with states |
| `POST` | `/api/v1/review/approve` | Approve a detection |
| `POST` | `/api/v1/review/reject` | Reject a detection |
| `POST` | `/api/v1/review/edit` | Edit detection fields |
| `POST` | `/api/v1/review/add` | Add manually created detection |
| `POST` | `/api/v1/review/delete` | Delete a detection |
| `POST` | `/api/v1/review/undo` | Undo last review action |
| `POST` | `/api/v1/review/redo` | Redo undone action |
| `POST` | `/api/v1/review/batch-approve` | Approve multiple detections |
| `POST` | `/api/v1/review/batch-reject` | Reject multiple detections |
| `GET` | `/api/v1/review/history/{id}` | Audit trail for a document |
| `POST` | `/api/v1/risk/assess` | Full risk assessment |
| `POST` | `/api/v1/risk/summary` | Lightweight risk summary |
| `POST` | `/api/v1/export/validate` | Validate export readiness |
| `POST` | `/api/v1/export/run` | Redact + render export |

---

## Tech Stack

### Backend
- **Python 3.11+** with **FastAPI 0.104**
- **Pydantic v2** for settings + model validation
- **PyMuPDF** (fitz) for PDF extraction
- **python-docx** for DOCX extraction
- **google-generativeai** for Gemini AI detection
- **Uvicorn** for ASGI serving

### Frontend
- **Next.js 16.2.9** (App Router, Turbopack)
- **React 19.2.4** with server components + client components
- **TypeScript 5** strict mode
- **Zustand 5** for state management (5 stores)
- **TanStack Query 5** for server state (via QueryProvider)
- **Tailwind CSS v4** with PostCSS
- **Framer Motion 11** for animations
- **Lucide React** for icons

---

## Settings

User settings are persisted to `localStorage` under `sentinel-settings`:

| Setting | Default | Description |
|---|---|---|
| `actorName` | `"reviewer"` | Name recorded in audit events |
| `requireFullReview` | `false` | Block export if any entity unreviewed |
| `defaultExportFormat` | `"txt"` | Default export format (txt | json) |
| `showKeyboardHints` | `true` | Show keyboard shortcut hints in UI |

---

## Development Notes

- **In-memory stores**: The backend uses `InMemoryDocumentStore` and `InMemoryReviewStore`. All data resets on server restart.
- **Gemini API key**: Set `GEMINI_API_KEY` in `backend/.env`. Without it, the Gemini detector is skipped.
- **Next.js 16.x**: This project uses Next.js 16.2.9 which has breaking changes from v15. See `frontend/AGENTS.md` and check `node_modules/next/dist/docs/` before writing new code.
- **No database**: No PostgreSQL/Redis are required for development. Database placeholders exist in `config.py` for future production use.
- **Sample documents**: `test-doc.txt` and `Dharshan_CV.pdf` are included for testing.
