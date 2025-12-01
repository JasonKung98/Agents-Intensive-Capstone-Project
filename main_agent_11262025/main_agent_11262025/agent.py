# Conceptual Code: Parallel Information Gathering
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from google.adk.agents import SequentialAgent, ParallelAgent, LlmAgent
from google.adk.tools import ToolContext, google_search, google_maps_grounding
from google.adk.tools.function_tool import FunctionTool

load_dotenv()

class KeyValuePair(BaseModel):
    """Replaces Dict[str, float] for strict JSON Schema compatibility."""
    key: str = Field(description="The preference category name.")
    value: float = Field(description="The preference score (0.0 to 1.0).")

class UserProfile(BaseModel):
    """
    Defines the User Profile structure, using List[KeyValuePair] for compatibility.
    """
    
    # The Preference Vector is now a list of explicit KeyValuePairs
    preference_vector: List[KeyValuePair] = Field(
        description="A list of objects, each defining a category and its preference score."
    )
    
    # Change Optional[float] to a mandatory float, relying on downstream code for 'None' handling
    max_daily_budget: float = Field(
        description="The maximum preferred budget for one full day of activities/travel, in USD."
    )
    
    preferred_transport_mode: str = Field(
        default="Walk", 
        description="The user's most preferred method of intra-city travel."
    )

# This Pydantic class defines the exact structure for the ECA's output.
class MoodAnalysis(BaseModel):
    """Structured output for the Emotional Context Agent."""
    
    # The classified primary emotional state (e.g., 'Stress Relief', 'Excited', 'Intellectual').
    primary_state: str = Field(description = "The dominant emotional state or trip goal derived from the user's input.")
    
    # Mandatory constraints (keywords) for filtering POIs (e.g., 'Quiet', 'Low-Energy').
    mandatory_constraints: List[str] = Field(description = "A list of non-negotiable keywords for activity filtering.")
    
    # Budget sensitivity adjustment (e.g., 'Strict', 'Flexible', 'High-End').
    budget_sensitivity: str = Field(description = "Indicates how strictly the budget should be adhered to (affects the Negotiation Loop).")

# Conceptual function for the ECA within the ADK environment
# This abstracts the ADK's specific LLM interaction methods.

# MOCK_USER_DATABASE is simplified to a single default profile
MOCK_DEFAULT_PROFILE = {
    "preference_vector": {"Nature": 0.9, "Culture/History": 0.7, "Nightlife": 0.2},
    "max_daily_budget": 250.00,
    "preferred_transport_mode": "Public Transport"
}

# The tool function
def read_user_profile(tool_context: ToolContext) -> Dict[str, Any]:
    """Retrieves the DEFAULT UserProfile data and transforms it.""" 
    
    profile_raw = MOCK_DEFAULT_PROFILE
    
    # Transformation step (Dict to List[KeyValuePair]) remains the same
    list_vector = [
        KeyValuePair(key=k, value=v).model_dump()
        for k, v in profile_raw["preference_vector"].items()
    ]
    
    profile_data = {
        "preference_vector": list_vector,
        "max_daily_budget": profile_raw["max_daily_budget"],
        "preferred_transport_mode": profile_raw["preferred_transport_mode"]
    }
    
    UserProfile(**profile_data) # Validate schema
    
    return {"status": "success", "profile_data": profile_data}

ProfileReadTool = FunctionTool(
    func=read_user_profile,
)

def analyze_user_emotion(user_input: str) -> MoodAnalysis:
    """
    Analyzes user text input to classify emotional state and derive constraints.
    This function represents the ECA's core logic using the LLM-as-Classifier method.
    """
    
    # 1. Prepare the input for the LLM
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": f"User's request: {user_input}"}
    ]
    
    # 2. Call the ADK's LLM engine
    # (The ADK handles sending the prompt and enforcing the Pydantic schema)
    
    # --- Conceptual ADK Call ---
    # response = adk_llm.generate(
    #     messages=messages,
    #     output_schema=MoodAnalysis
    # )
    # --- End Conceptual ADK Call ---
    
    # For demonstration, we'll simulate a successful structured output:
    if "stress" in user_input.lower() or "relax" in user_input.lower():
        # Simulated LLM output based on a 'Stress Relief' prompt
        return MoodAnalysis(
            primary_state="Stress Relief",
            mandatory_constraints=["Quiet", "Low-Energy", "Nature", "Comfort"],
            budget_sensitivity="Flexible" # Willing to pay a bit more for comfort
        )
    else:
        # Default or other state classification...
        return MoodAnalysis(
            primary_state="General",
            mandatory_constraints=[],
            budget_sensitivity="Normal"
        )

# UPA Definition (LlmAgent for Tool Calling)
UPA_Agent = LlmAgent(
    name="User_Profile_Agent",
    instruction="Use the read_user_profile tool to retrieve the default user's profile data.",
    tools=[ProfileReadTool],
    model="gemini-2.5-flash",
    output_key="user_profile"
)

# ECA Definition (LlmAgent for Classification)
ECA_SYSTEM_PROMPT = """
You are the Emotional Context Agent (ECA). Analyze the user's emotion and translate it into trip constraints. Output a JSON object that strictly conforms to the MoodAnalysis schema. DO NOT add any extra fields.
"""
ECA_Agent = LlmAgent(
    name="Emotional_Context_Agent",
    instruction=ECA_SYSTEM_PROMPT,
    tools=[],
    model="gemini-2.5-pro",
    output_key="emotional_context"
)

gather_concurrently = ParallelAgent(
    name="ConcurrentFetch",
    sub_agents=[UPA_Agent, ECA_Agent]
)

synthesizer = LlmAgent(
    name="Synthesizer",
    model = "gemini-2.5-flash",
    instruction="Combine results from {user_profile}, {emotional_context}."
)

composer_agent = SequentialAgent(
    name="FetchAndSynthesize",
    sub_agents=[gather_concurrently, synthesizer] # Run parallel fetch, then synthesize
)

planner_agent = LlmAgent(
    name = "logistics_agent",
    model="gemini-2.5-pro",
    description = "Agent to estimate an optimal travel route using ADK v1.15+ google_maps_grounding tool.",
    instruction = "Use the provided google_maps_grounding tool to suggest an optimal travelling route for the user given from composer_agent. Please ask for user's confirmation before proceed to the suggestions given",
    tools = [google_maps_grounding],
    output_key = "travel_route"
)

ticket_booking_agent = LlmAgent(
    name = "ticket_booking_agent",
    model="gemini-2.5-pro",
    description = "Agent to search flight schedule available for booking tickets.",
    instruction = "Use the built-in Google Search tool to search for flights booking.",
    tools = [google_search],
    output_key = "flight_schedule"
)

root_agent = SequentialAgent(
    name="TripPlanningAgent",
    sub_agents=[composer_agent, planner_agent, ticket_booking_agent]
)