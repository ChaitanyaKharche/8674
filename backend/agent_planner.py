import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

from agent_state import PlannerState
from agent_tools import ALL_TOOLS
from curriculum_optimizer import HybridOptimizer  # To reuse your validation logic

load_dotenv()

# 1. Initialize The Brain (Groq Llama-3 70B)
llm = ChatGroq(
    temperature=0.1,
    model_name="llama3-70b-8192",
    api_key=os.getenv("GROQ_API_KEY")
)

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(ALL_TOOLS)

# 2. Define Nodes

def drafter_node(state: PlannerState):
    """Generates the initial plan or fixes it based on critique."""
    profile = state["student_profile"]
    track = state["track"]
    critique = state.get("critique", [])
    iteration = state["iterations"]

    # Prompt Engineering
    system_msg = f"""You are an expert Academic Advisor at Northeastern University.
    Your goal: Create a valid 4-year course plan for a {track} major.
    
    Student Profile:
    - Goal: {profile.get('career_goals')}
    - Interests: {profile.get('interests')}
    - Difficulty Preference: {profile.get('preferred_difficulty')}
    - Completed: {profile.get('completed_courses')}
    
    Constraints:
    - Use the provided tools to check professor ratings if difficulty is a concern.
    - Output strictly valid JSON format for the plan (Year 1 Fall, Year 1 Spring, etc.).
    """
    
    user_msg = "Generate the plan."
    if critique:
        user_msg = f"The previous plan had errors: {critique}. Please fix these specific issues and output the full plan again."

    # Call LLM
    response = llm_with_tools.invoke([SystemMessage(content=system_msg), HumanMessage(content=user_msg)])
    
    # Parse LLM response (Simplified for brevity - implies LLM returns JSON)
    # In production, use structured output parsing or PydanticOutputParser
    try:
        # This assumes the LLM outputs raw JSON in the content
        # You might need a parser here depending on how chatty the model is
        draft_plan = json.loads(response.content) 
    except:
        draft_plan = state.get("draft_plan", {}) # Fallback

    return {
        "draft_plan": draft_plan, 
        "iterations": iteration + 1,
        "messages": [response]
    }

def validator_node(state: PlannerState):
    """Uses your deterministic NetworkX logic to check the plan."""
    plan = state["draft_plan"]
    profile = state["student_profile"]
    
    # ---------------------------------------------------------
    # HOOK: Use your existing optimizer for strict validation
    # ---------------------------------------------------------
    optimizer = HybridOptimizer() 
    # Load graph here if not globally loaded (or pass it in)
    # optimizer.load_data(graph_instance) 
    
    # For now, let's assume we call your existing validate method:
    # validation_results = optimizer.validate_plan(plan, student_obj)
    
    # Mocking validation for the script to run standalone:
    errors = []
    # logic to check if 'CS2800' is before 'CS3000', etc.
    
    return {"critique": errors}

# 3. Define Routing Logic
def should_continue(state: PlannerState):
    errors = state.get("critique", [])
    if not errors:
        return "end"
    if state["iterations"] >= 3:
        return "end" # Max retries reached
    return "refine"

# 4. Build the Graph
workflow = StateGraph(PlannerState)

workflow.add_node("drafter", drafter_node)
workflow.add_node("validator", validator_node)

workflow.set_entry_point("drafter")
workflow.add_edge("drafter", "validator")
workflow.add_conditional_edges(
    "validator",
    should_continue,
    {
        "end": END,
        "refine": "drafter"
    }
)

agent_app = workflow.compile()