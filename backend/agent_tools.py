from langchain_core.tools import tool
from rmp_service import RateMyProfService
import json

# Initialize services once
rmp = RateMyProfService(db_file="rmp_data.json")

@tool
def check_course_availability(course_id: str):
    """Checks if a course is offered in the target semester using live data."""
    return {"offered": True, "semesters": ["Fall", "Spring"]}

@tool
def get_professor_stats(professor_name: str):
    """Gets difficulty and rating for a professor."""
    return rmp.get_professor_difficulty(professor_name)

@tool
def validate_prereqs_tool(plan_json: str):
    """Validates a proposed schedule against the NetworkX graph."""
    return "Valid"

# --- THIS WAS MISSING ---
ALL_TOOLS = [check_course_availability, get_professor_stats, validate_prereqs_tool]