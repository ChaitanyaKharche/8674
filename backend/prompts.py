def get_semester_selection_prompt(profile_str: str, courses_str: str, num_courses: int = 4) -> str:
    """Generate optimized prompt for LLM course selection"""
    
    return f"""You are an expert academic advisor for computer science students.

TASK: Select exactly {num_courses} courses for the upcoming semester.

STUDENT PROFILE:
{profile_str}

AVAILABLE COURSES:
{courses_str}

SELECTION CRITERIA:
1. Prerequisites must be satisfied (from completed courses list)
2. Prioritize courses that align with student's career goals
3. Balance workload - mix harder and easier courses
4. Consider logical progression (foundations before advanced)
5. Focus on CS, DS, IS courses for AI/ML career path

OUTPUT FORMAT (must be valid JSON):
{{
    "courses": ["COURSE_ID_1", "COURSE_ID_2", "COURSE_ID_3", "COURSE_ID_4"],
    "reasoning": "One sentence explaining the selection"
}}

Return ONLY the JSON object, no other text."""

def get_plan_optimization_prompt(student_profile: dict, available_courses: list, semester_num: int) -> str:
    """Generate prompt for full degree plan optimization"""
    
    return f"""Create semester {semester_num} schedule for an AI/ML-focused student.

COMPLETED: {', '.join(student_profile.get('completed_courses', []))}
GOAL: {student_profile.get('career_goals', 'AI Engineer')}
INTERESTS: {', '.join(student_profile.get('interests', []))}

MUST FOLLOW RULES:
- Take foundations first: CS1800, CS2500, CS2510, CS2800, CS3000, CS3500
- Year 1: Focus on 1000-2000 level courses
- Year 2: Add 3000 level courses  
- Year 3-4: Include 4000+ level courses
- Avoid labs, recitations, seminars (they're auto-enrolled)

AVAILABLE COURSES:
{chr(10).join(available_courses[:20])}

OUTPUT: JSON with "courses" array (4 course IDs) and "reasoning" string."""