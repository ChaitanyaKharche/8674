# CurriculAI

**Intelligent 4-year curriculum planning for Northeastern CS students.**

Scrapes live course data → builds a prerequisite DAG → generates personalized degree plans using semantic embeddings + LLM reasoning + RateMyProfessors difficulty data.

---

## What It Does

```
SearchNEU GraphQL  →  Course Graph (DAG)  →  Hybrid Optimizer  →  Semester-by-Semester Plan
       ↓                    ↓                      ↓                       ↓
  Live catalog        Prerequisites          Embeddings +           Validated, balanced,
  + professors        + complexity           LLM + RMP              track-optimized
```

### Core Features

- **Live scraping** from SearchNEU API (courses, prerequisites, professors)
- **RateMyProfessors integration** for difficulty-aware scheduling
- **Multiple concentration tracks**: AI/ML, Systems, Security, Game Dev, General
- **Semantic course scoring** using BGE embeddings aligned to career goals
- **LLM-assisted planning** (Llama 3.1 8B) with rule-based fallback
- **Drag-and-drop editor** with real-time prerequisite validation
- **Complexity balancing** across semesters

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   neu_scraper.py ──→ curriculum_analyzer.py ──→ agentic_optimizer.py        │
│        │                      │                        │                     │
│   Scrape courses         Clean graph              Validate reqs              │
│   + professors          Fix prereq chains         Auto-patch missing         │
│   Build DAG             Tag accessibility         LLM suggestions            │
│                                                                              │
│   rmp_scraper.py ────────────────────────────────────────────────────────── │
│        │                                                                     │
│   RateMyProfessors                                                           │
│   difficulty ratings                                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OPTIMIZATION ENGINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   curriculum_optimizer.py (HybridOptimizer)                                  │
│        │                                                                     │
│        ├─ BGE embeddings → semantic course scoring                           │
│        ├─ Llama 3.1 8B (4-bit) → elective suggestions                        │
│        ├─ RMP service → professor difficulty                                 │
│        ├─ Track-aware priority queues                                        │
│        └─ Equivalency groups (MATH1341 ≡ MATH1241 ≡ MATH1231)               │
│                                                                              │
│   Outputs: 4-year plan with complexity analysis, validation, explanations   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API + FRONTEND                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   api.py (FastAPI)                     React + Ant Design                    │
│        │                                      │                              │
│        ├─ POST /api/load_data                 ├─ PlanGeneratorTab            │
│        ├─ POST /api/generate_plan             ├─ InteractivePlanEditor       │
│        ├─ POST /api/validate_course           ├─ DraggableCourse (dnd-kit)   │
│        ├─ POST /api/move_course               └─ CurriculumMapTab (Plotly)   │
│        └─ GET  /api/course_info/:id                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Data** | NetworkX, Pickle, SearchNEU GraphQL |
| **ML** | PyTorch, Sentence-Transformers (BGE), Llama 3.1 8B (4-bit quantized) |
| **Backend** | FastAPI, Pydantic, Uvicorn |
| **Frontend** | React 18, Vite, Ant Design, dnd-kit, Plotly.js |
| **External** | RateMyProfessors GraphQL |

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- CUDA-capable GPU (optional, for LLM mode)

---

## Setup

### 1. Backend

```bash
# Clone and enter
git clone <repo-url>
cd curriculai

# Virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Dependencies
pip install -r requirements.txt

# Start API
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend

```bash
cd frontend

npm install
npm run dev  # → http://localhost:5173
```

### 3. Data Pipeline (One-time)

```bash
# Step 1: Scrape NEU courses
python neu_scraper.py \
  --term 202510 \
  --subjects CS DS MATH CY PHYS ENGW \
  --output neu_data

# Step 2: Scrape RMP ratings (optional but recommended)
python rmp_scraper.py  # Uses the pickle from step 1

# Step 3: Clean and analyze graph
python curriculum_analyzer.py \
  --input neu_data_combined_*.pkl \
  --output neu_graph_clean.pkl

# Step 4: Validate requirements (optional)
python agentic_optimizer.py \
  --graph neu_graph_clean.pkl \
  --fix \
  --output neu_graph_fixed.pkl

# Step 5: Inspect (debug)
python inspect_graph.py neu_graph_fixed.pkl
```

**Upload the final `.pkl` file via the web UI to start planning.**

---

## Usage

1. **Upload** your `.pkl` graph file in the Plan Generator tab
2. **Set profile**: completed courses, time commitment, difficulty preference
3. **Select track**: AI/ML, Systems, Security, Game Dev, or General
4. **Generate**: Rule-based (fast) or LLM-optimized (smarter electives)
5. **Edit**: Drag courses between semesters; validation runs in real-time
6. **Export**: Save or download your finalized plan

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/load_data` | Upload `.pkl` graph file |
| `POST` | `/api/generate_plan` | Generate 4-year plan |
| `GET` | `/api/course_info/{id}` | Course details + professors |
| `GET` | `/api/courses` | All courses with metadata |
| `POST` | `/api/validate_course_placement` | Check single course placement |
| `POST` | `/api/validate_entire_plan` | Bulk plan validation |
| `POST` | `/api/move_course` | Move course + re-validate |
| `GET` | `/api/professor/{name}` | RMP difficulty rating |

### Request Example

```bash
curl -X POST http://localhost:8000/api/generate_plan \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Student",
    "completed_courses": ["CS1800", "CS2500"],
    "time_commitment": 40,
    "preferred_difficulty": "moderate",
    "career_goals": "ML Engineer",
    "interests": ["deep learning", "NLP"],
    "current_gpa": 3.5,
    "learning_style": "Visual"
  }' \
  --url-query "track=ai_ml&plan_type=simple"
```

---

## Project Structure

```
.
├── api.py                    # FastAPI backend
├── curriculum_optimizer.py   # Core optimization engine
├── curriculum_analyzer.py    # Graph cleaning pipeline
├── agentic_optimizer.py      # LLM-based requirement validator
├── neu_scraper.py            # SearchNEU data scraper
├── rmp_scraper.py            # RateMyProfessors scraper
├── rmp_service.py            # RMP lookup service
├── inspect_graph.py          # Graph diagnostic tool
├── interactive_visualizer.py # Streamlit + Plotly graphs
├── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   └── components/
    │       ├── PlanGeneratorTab.jsx
    │       ├── CurriculumMapTab.jsx
    │       ├── DraggableCourse.jsx
    │       ├── InteractivePlanEditor.jsx
    │       ├── InteractiveGraph.jsx
    │       └── ...
    ├── package.json
    └── vite.config.js
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_BACKEND_URL` | `http://localhost:8000` | API base URL (frontend) |
| `RAPIDAPI_KEY` | - | RapidAPI key for RMP (optional) |

### Concentration Tracks

Defined in `curriculum_optimizer.py → CONCENTRATION_REQUIREMENTS`:

- **ai_ml**: CS4100, DS4400, CS4120, DS4420, etc.
- **systems**: CS3650, CS4700, CS5700, CS4730
- **security**: CY2550, CY3740, CY4740, CY4760
- **game_dev**: CS3540, CS4520, CS4300, CS4700
- **general**: Broadest elective pool

### Locked Courses

Some courses are locked to specific semesters (non-movable):

```python
# api.py
LOCKED_COURSES = {
    "fall_1": ["CS1800", "CS2500", "MATH1341", "ENGW1111"],
    "spring_1": ["CS2510", "CS2800", "MATH1342", "DS2000"],
}
```

---

## Algorithms

### Plan Generation

1. **Topological sort** of prerequisite DAG
2. **Semantic scoring** via cosine similarity (career goals ↔ course descriptions)
3. **Track-aware priority queues** per year
4. **Difficulty filtering** based on student preference + RMP data
5. **Equivalency expansion** (e.g., MATH1341 satisfies MATH1241 prereqs)
6. **Complexity balancing** across semesters

### Validation

- Prerequisite satisfaction (expanded for equivalencies)
- Credit hour limits (>20 triggers warning)
- Semester offering checks (via SearchNEU)
- Locked course enforcement

---

## Known Issues

- `CS3700` was renamed to `CS5700` (Networks) — handled via `agentic_optimizer.py`
- Some 5000-level courses are accessible to undergrads but must be whitelisted
- RMP scraping may hit rate limits; use cached `rmp_data.json` when possible

---

## Roadmap

- [ ] Multi-term offering prediction
- [ ] Co-op integration (alternate semesters)
- [ ] GPA impact estimation
- [ ] Export to NEU degree audit format
- [ ] Collaborative plan sharing

---

## License

MIT

---

**Built by Chaitanya** | MS CS @ Northeastern | [GitHub](https://github.com/your-username)
