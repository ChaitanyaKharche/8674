from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Set, Dict, List, Optional
import pickle
import networkx as nx
from pathlib import Path
import httpx
from datetime import datetime, timedelta
from functools import lru_cache
import uvicorn
import os

from curriculum_optimizer import HybridOptimizer
from curriculum_analyzer import CurriculumAnalyzer
from rmp_service import RateMyProfService
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# ALWAYS initialize the service using the local DB
try:
    rmp_service = RateMyProfService(db_file="rmp_data.json")
    print("✓ RMP service initialized (Local Mode)")
except Exception as e:
    print(f"⚠️ RMP Service failed to load: {e}")
    rmp_service = None
    
# ===== CONSTANTS & GLOBALS =====
OFFERING_CACHE = {}
CACHE_DURATION = timedelta(hours=24)
SEARCHNEU_GRAPHQL = "https://searchneu.com/graphql"
PLANS_STORAGE = {}
# rmp_service = RateMyProfService()

# Course locking configuration - courses that must be taken in specific semesters
LOCKED_COURSES = {
    "fall_1": ["CS1800", "CS2500", "MATH1341", "ENGW1111"],
    "spring_1": ["CS2510", "CS2800", "MATH1342", "DS2000"],
}

def is_course_locked(course_id: str, year: int, semester: str) -> bool:
    """Check if a course is locked to a specific semester"""
    semester_key = f"{semester.lower()}_{year}"
    return course_id in LOCKED_COURSES.get(semester_key, [])

def get_course_locked_location(course_id: str) -> Optional[tuple]:
    """Get the semester/year where a course is locked, if any"""
    for lock_key, locked_courses in LOCKED_COURSES.items():
        if course_id in locked_courses:
            parts = lock_key.split('_')
            semester = parts[0]
            year = int(parts[1])
            return (semester, year)
    return None


optimizer = None
analyzer = None

# ===== PYDANTIC MODELS =====
class ApiStudentProfile(BaseModel):
    name: str
    current_gpa: float
    learning_style: str
    interests: List[str]
    career_goals: str
    completed_courses: List[str]
    time_commitment: int
    preferred_difficulty: str

class CourseValidationRequest(BaseModel):
    course_id: str
    target_semester: str
    target_year: int
    completed_courses: List[str]
    current_plan: Dict

class MoveCourseRequest(BaseModel):
    plan: Dict
    course_id: str
    from_semester: str
    from_year: int
    to_semester: str
    to_year: int
    completed_courses: List[str]

class SavePlanRequest(BaseModel):
    plan_id: Optional[str] = None
    plan: Dict
    profile: ApiStudentProfile
    track: str
    name: Optional[str] = None

# ===== CREATE APP & ADD MIDDLEWARE =====
app = FastAPI(title="Curriculum Optimizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== HELPER FUNCTIONS =====
# Remove @lru_cache and make synchronous
def query_searchneu_offerings_sync(course_id: str) -> Dict:
    """Synchronous version without cache"""
    subject = ''.join([c for c in course_id if c.isalpha()])
    number = ''.join([c for c in course_id if c.isdigit()])
    
    try:
        import requests
        response = requests.post(
            SEARCHNEU_GRAPHQL,
            json={
                "query": """
                    query GetCourse($subject: String!, $classId: String!) {
                        class(subject: $subject, classId: $classId) {
                            sections { termId }
                        }
                    }
                """,
                "variables": {"subject": subject, "classId": number}
            },
            timeout=5
        )
        
        offerings = {"fall": True, "spring": True, "summer": True}
        
        if response.ok and response.json().get("data", {}).get("class", {}).get("sections"):
            for section in response.json()["data"]["class"]["sections"]:
                term_id = section.get("termId", "")
                if term_id.endswith("10"):
                    offerings["spring"] = True
                elif term_id.endswith("50"):
                    offerings["fall"] = True
        
        return offerings
    except:
        return {"fall": True, "spring": True, "summer": True}


# ===== CORE ENDPOINTS =====

@app.on_event("startup")
async def startup():
    global rmp_service
    # No scraping on startup needed - RapidAPI fetches on demand
    print("✓ RMP service initialized (fetches on demand)")


@app.get("/api/professors")
async def get_professors():
    """Get all cached professors with ratings"""
    professors = rmp_service._load_cached_professors()
    return {"professors": professors}

@app.get("/api/professor/{name}")
async def get_professor(name: str):
    """Get specific professor difficulty data"""
    data = rmp_service.get_professor_difficulty(name)
    return data



@app.post("/api/load_data")
async def load_data(file: UploadFile = File(...)):
    global optimizer, analyzer
    try:
        contents = await file.read()
        
        if not contents:
            raise HTTPException(status_code=400, detail="File is empty")
        
        data = pickle.loads(contents)
        print(f"Loaded pickle file, type: {type(data)}")
        
        # Handle both dict and direct DiGraph
        if isinstance(data, nx.DiGraph):
            graph = data
        elif isinstance(data, dict):
            if 'graph' in data:
                graph = data['graph']
            else:
                raise HTTPException(status_code=400, detail=f"Dict found but missing 'graph' key. Keys: {list(data.keys())}")
        else:
            raise HTTPException(status_code=400, detail=f"Expected DiGraph or dict, got {type(data)}")
        
        # Initialize
        optimizer = HybridOptimizer()
        optimizer.load_models()  # Load embedding model FIRST
        optimizer.load_data(graph)  # Then load the graph data
        
        print(f"✅ Loaded graph with {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        
        return {"message": "Curriculum data loaded successfully"}
    
    except pickle.UnpicklingError as e:
        raise HTTPException(status_code=400, detail=f"Failed to unpickle file: {str(e)}")
    except Exception as e:
        print(f"Load data error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")




from curriculum_optimizer import HybridOptimizer, StudentProfile

@app.post("/api/generate_plan")
async def generate_plan(
    profile: ApiStudentProfile,
    track: str = "ai_ml",  # Keep your default (ai_ml not general)
    plan_type: str = "simple"
):
    global optimizer, rmp_service
    
    if not optimizer or not optimizer.curriculum_graph:
        raise HTTPException(status_code=400, detail="Graph not loaded. Upload .pkl file first.")
    
    try:
        print(f"Generating {plan_type} plan for track: {track}")
        print(f"Difficulty: {profile.preferred_difficulty}")
        
        # Convert to StudentProfile dataclass
        student = StudentProfile(
            completed_courses=profile.completed_courses or [],
            time_commitment=profile.time_commitment or 40,
            preferred_difficulty=profile.preferred_difficulty or "moderate",  # NOW USED!
            career_goals=profile.career_goals or "",
            interests=profile.interests or [],
            current_gpa=profile.current_gpa or 3.5,
            learning_style=profile.learning_style or "Visual"
        )
        
        # Wire RMP service for difficulty-aware scoring
        if rmp_service:
            optimizer.rmp_service = rmp_service
        
        if plan_type == "llm":
            plan = optimizer.generate_llm_plan(student, track)
        else:
            plan = optimizer.generate_simple_plan(student, track)
        
        return plan
    
    except Exception as e:
        print(f"Plan generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

        
@app.get("/api/course_info/{course_id}")
async def get_course_info(course_id: str):
    if not optimizer:
        raise HTTPException(status_code=400, detail="Optimizer not loaded")
    
    if course_id not in optimizer.courses:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")
    
    course_data = optimizer.courses[course_id]
    return {
        "id": course_id,
        "name": course_data.get("name", course_id),
        "description": course_data.get("description", ""),
        "credits": course_data.get("maxCredits", 4),
        "complexity": course_data.get("complexity", 50),
        "professors": course_data.get("professors", [])

    }

@app.get("/api/courses")
async def get_all_courses():
    """
    Return all courses with their metadata (name, credits, complexity, etc.)
    Used by frontend to display course details in plans
    """
    if not optimizer:
        raise HTTPException(status_code=400, detail="Optimizer not loaded")
    
    return {
        "courses": optimizer.courses
    }


# ===== VALIDATION ENDPOINTS =====
@app.post("/api/validate_course_placement")
async def validate_course_placement(request: CourseValidationRequest):
    if not optimizer or not optimizer.curriculum_graph:
        raise HTTPException(status_code=400, detail="Optimizer not loaded")
    
    errors = []
    warnings = []
    suggestions = []

    # Check if course is locked to a specific semester
    locked_location = get_course_locked_location(request.course_id)
    if locked_location:
        locked_semester, locked_year = locked_location
        if request.target_semester.lower() != locked_semester or request.target_year != locked_year:
            errors.append({
                "type": "locked_course",
                "message": f"{request.course_id} is a required course that must be taken in {locked_semester.title()} Year {locked_year}",
                "locked_to": f"{locked_semester}_{locked_year}"
            })
            suggestions.append(f"Move {request.course_id} to {locked_semester.title()} Year {locked_year}")
            # Return early if course is locked to wrong semester
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
                "semester_complexity": 0,
                "total_credits": 0,
                "course_details": optimizer.courses.get(request.course_id, {})
            }

    
    prereqs = list(optimizer.curriculum_graph.predecessors(request.course_id)) \
        if request.course_id in optimizer.curriculum_graph else []
    
    courses_before_target = set(request.completed_courses)
    for year_key, year_data in request.current_plan.items():
        if not year_key.startswith("year_"):
            continue
        year_num = int(year_key.split("_")[1])
        
        if year_num < request.target_year:
            courses_before_target.update(year_data.get("fall", []))
            courses_before_target.update(year_data.get("spring", []))
        elif year_num == request.target_year and request.target_semester == "spring":
            courses_before_target.update(year_data.get("fall", []))
    
    expanded_completed = optimizer._get_completed_with_equivalents(courses_before_target)
    
    missing_prereqs = [p for p in prereqs if p not in expanded_completed]
    if missing_prereqs:
        errors.append({
            "type": "missing_prerequisite",
            "courses": missing_prereqs,
            "message": f"Missing prerequisites: {', '.join(missing_prereqs)}"
        })
        suggestions.append(f"Complete {', '.join(missing_prereqs)} before taking {request.course_id}")
    
    offerings = query_searchneu_offerings_sync(request.course_id)
    semester_offered = offerings.get(request.target_semester.lower(), False)
    
    if not semester_offered:
        warnings.append({
            "type": "not_typically_offered",
            "message": f"{request.course_id} is not typically offered in {request.target_semester.title()}",
            "severity": "medium"
        })
        offered_in = [sem.title() for sem, avail in offerings.items() if avail]
        if offered_in:
            suggestions.append(f"Consider taking {request.course_id} in {' or '.join(offered_in)}")
    
    year_key = f"year_{request.target_year}"
    semester_courses = request.current_plan.get(year_key, {}).get(request.target_semester.lower(), [])
    
    all_courses_in_semester = semester_courses + [request.course_id]
    semester_complexity = 0
    for cid in all_courses_in_semester:
        if cid in optimizer.courses:
            semester_complexity += optimizer.courses[cid].get("complexity", 5)
    
    if semester_complexity > 60:
        warnings.append({
            "type": "high_complexity",
            "message": f"This semester would have very high complexity ({semester_complexity})",
            "severity": "high"
        })
        suggestions.append("Consider moving a course to another semester to balance workload")
    elif semester_complexity > 45:
        warnings.append({
            "type": "moderate_complexity",
            "message": f"This semester has moderate-high complexity ({semester_complexity})",
            "severity": "low"
        })
    
    total_credits = sum(
        optimizer.courses.get(cid, {}).get("maxCredits", 4) 
        for cid in all_courses_in_semester
    )
    
    if total_credits > 20:
        warnings.append({
            "type": "high_credit_load",
            "message": f"This semester would have {total_credits} credits (>20 requires approval)",
            "severity": "high"
        })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "semester_complexity": semester_complexity,
        "total_credits": total_credits,
        "course_details": optimizer.courses.get(request.course_id, {})
    }

@app.post("/api/move_course")
async def move_course(request: MoveCourseRequest):
    if not optimizer:
        raise HTTPException(status_code=400, detail="Optimizer not loaded")
    
    updated_plan = dict(request.plan)
    
    from_year_key = f"year_{request.from_year}"
    if from_year_key in updated_plan:
        if request.from_semester in updated_plan[from_year_key]:
            courses = updated_plan[from_year_key][request.from_semester]
            if request.course_id in courses:
                courses.remove(request.course_id)
    
    to_year_key = f"year_{request.to_year}"
    if to_year_key not in updated_plan:
        updated_plan[to_year_key] = {}
    if request.to_semester not in updated_plan[to_year_key]:
        updated_plan[to_year_key][request.to_semester] = []
    
    updated_plan[to_year_key][request.to_semester].append(request.course_id)
    
    validation_request = CourseValidationRequest(
        course_id=request.course_id,
        target_semester=request.to_semester,
        target_year=request.to_year,
        completed_courses=request.completed_courses,
        current_plan=updated_plan
    )
    
    validation = await validate_course_placement(validation_request)
    
    all_courses = []
    for year_key, year_data in updated_plan.items():
        if year_key.startswith("year_"):
            all_courses.extend(year_data.get("fall", []))
            all_courses.extend(year_data.get("spring", []))
    
    plan_errors = []
    for year in range(1, 5):
        year_key = f"year_{year}"
        if year_key in updated_plan:
            for semester in ["fall", "spring"]:
                courses_in_sem = updated_plan[year_key].get(semester, [])
                for course in courses_in_sem:
                    prereqs = list(optimizer.curriculum_graph.predecessors(course)) \
                        if course in optimizer.curriculum_graph else []
                    
                    for prereq in prereqs:
                        if prereq not in all_courses[:all_courses.index(course)]:
                            plan_errors.append(f"{course} requires {prereq} which is not scheduled before it")
    
    return {
        "updated_plan": updated_plan,
        "validation": validation,
        "plan_errors": plan_errors,
        "success": validation["valid"] and len(plan_errors) == 0
    }

    # Check if course is locked and cannot be moved
    locked_location = get_course_locked_location(request.course_id)
    if locked_location:
        locked_semester, locked_year = locked_location
        if request.from_semester.lower() == locked_semester and request.from_year == locked_year:
            # Course is in its locked position, don't allow moving it
            raise HTTPException(
                status_code=400,
                detail=f"{request.course_id} is a required course locked to {locked_semester.title()} Year {locked_year} and cannot be moved"
            )

# ===== PLAN VARIATION ENDPOINTS =====
@app.post("/api/generate_variations")
async def generate_plan_variations(track: str = "ai_ml", max_variations: int = 5):
    if not optimizer:
        raise HTTPException(status_code=400, detail="Optimizer not loaded")
    
    try:
        all_plans = optimizer.generate_all_valid_plans(track)
        analytics = optimizer.analyze_track_flexibility(track)
        
        variations = []
        for i, plan_courses in enumerate(all_plans[:max_variations]):
            variation = {
                "id": f"{track}_var_{i+1}",
                "name": f"{track.title()} - Variation {i+1}",
                "courses": list(plan_courses),
                "elective_choices": {},
                "estimated_complexity": sum(
                    optimizer.courses.get(c, {}).get("complexity", 5) 
                    for c in plan_courses
                )
            }
            variations.append(variation)
        
        return {
            "track": track,
            "total_combinations": len(all_plans),
            "variations": variations,
            "analytics": analytics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating variations: {str(e)}")

# ===== PLAN PERSISTENCE =====
@app.post("/api/save_plan")
async def save_plan(request: SavePlanRequest):
    plan_id = request.plan_id or f"plan_{datetime.now().timestamp()}"
    
    PLANS_STORAGE[plan_id] = {
        "id": plan_id,
        "name": request.name or f"Plan - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "plan": request.plan,
        "profile": request.profile.dict(),
        "track": request.track,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    return {
        "plan_id": plan_id,
        "message": "Plan saved successfully"
    }

@app.get("/api/load_plan/{plan_id}")
async def load_plan(plan_id: str):
    if plan_id not in PLANS_STORAGE:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return PLANS_STORAGE[plan_id]

@app.get("/api/list_plans")
async def list_plans():
    return {
        "plans": [
            {
                "id": p["id"],
                "name": p["name"],
                "track": p["track"],
                "updated_at": p["updated_at"]
            }
            for p in PLANS_STORAGE.values()
        ]
    }

# ===== BULK VALIDATION =====
@app.post("/api/validate_entire_plan")
async def validate_entire_plan_post(body: Dict = Body(...)):
    plan = body.get('plan', {})
    completed = body.get('completed', [])
    if not optimizer:
        raise HTTPException(status_code=400, detail="Optimizer not loaded")
    
    all_errors = []
    all_warnings = []
    semester_complexities = {}
    
    for year in range(1, 5):
        year_key = f"year_{year}"
        if year_key not in plan:
            continue
            
        for semester in ["fall", "spring"]:
            if semester not in plan[year_key]:
                continue
                
            courses = plan[year_key][semester]
            if not courses:
                continue
            
            for course_id in courses:
                validation_request = CourseValidationRequest(
                    course_id=course_id,
                    target_semester=semester,
                    target_year=year,
                    completed_courses=completed,
                    current_plan=plan
                )
                
                result = await validate_course_placement(validation_request)
                
                all_errors.extend(result["errors"])
                all_warnings.extend(result["warnings"])
                
                sem_key = f"Year {year} {semester.title()}"
                if sem_key not in semester_complexities:
                    semester_complexities[sem_key] = 0
                semester_complexities[sem_key] = result["semester_complexity"]
    
    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": all_warnings,
        "semester_complexities": semester_complexities,
        "total_errors": len(all_errors),
        "total_warnings": len(all_warnings)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)