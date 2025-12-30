# CurriculAI (NEU Curriculum Optimizer)

A curriculum planning tool that:
1) Scrapes Northeastern course catalog data for selected terms and subjects  
2) Builds a prerequisite graph (DAG when data is clean)  
3) Cleans and enriches the graph (filters irrelevant subjects, fixes bad edges, adds complexity scores)  
4) Generates a personalized 4 year plan based on goals, interests, workload preference, and prerequisites

This repo is intended to be a practical, runnable code sample (not a notebook).

## What this project does

### Data pipeline
1) **Scrape** course and prerequisite data across multiple terms and subjects  
2) **Merge** into one canonical course dictionary + prerequisite graph  
3) **Analyze + clean**: remove irrelevant courses, fix known broken prereq chains, remove spurious edges, compute complexity  
4) **Plan generation**: produce a structured semester-by-semester plan and validate prereqs

### Planner behavior
The planner is hybrid:
- Rule based requirements and year-by-year course level constraints
- Semantic scoring using embeddings to align courses with career goals and interests
- Optional LLM-assisted suggestions (falls back safely if LLM is unavailable)

## Repo layout (expected)
- `frontend/` UI (web)
- `backend/` API and planner code (Python)
- `docs/` documentation
- `requirements.txt` backend Python dependencies

## Setup

### Backend
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
