from typing import TypedDict, List, Dict, Any, Optional

class PlannerState(TypedDict):
    # Inputs
    student_profile: Dict[str, Any]
    track: str
    
    # Working Memory
    draft_plan: Dict[str, Any]  # The plan being built
    critique: List[str]         # Errors found by Validator
    messages: List[Any]         # Chat history for the LLM
    
    # Control
    iterations: int