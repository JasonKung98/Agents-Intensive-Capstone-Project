# Agents-Intensive-Capstone-Project

🚀 **Multi-Agent Trip Planner: Project Write-up**

1. Project Overview

This project details the development of an intelligent, low-latency trip planning system built using the Google Agent Development Kit (ADK). The system is designed to overcome the limitations of monolithic planners by employing a highly specialized, multi-agent architecture. The primary objective is to transform an unstructured user query into a precise, optimized, and personalized itinerary by balancing a user's long-term preferences (static data) with their immediate emotional needs (dynamic context).

🎯 Architecture Pattern

The system's architecture is a Hierarchical Pipeline Architecture with Concurrent Fan-Out . This structure is deliberately chosen to maximize performance by running independent data fetching tasks in parallel while maintaining strict sequential dependencies for complex transformation and optimization tasks.

2. Agent Roles and Workflow Orchestration

The system comprises five distinct agent roles, with the Composer Agent acting as the central orchestrator, managing the flow using the ADK's ParallelAgent and SequentialAgent classes.

A. The Five Agent Roles

- Composer Agent
  Core Function: Orchestration & Synthesis
  Data Type Handled: Flow Control, Data Integration
  Key Tooling: ParallelAgent, SequentialAgent, LlmAgent (Synthesizer)

- User Profile Agent (UPA)
  Core Function: Static Data Retrieval
  Data Type Handled: Long-term preferences (preference_vector), budget
  Key Tooling: FunctionTool: Database Access (read_user_profile)

- Emotional Context Agent (ECA)
  Core Function: Dynamic Context Analysis
  Data Type Handled: Real-time emotional state, mandatory constraints
  Key Tooling: LLM Reasoning (No external tools)

- Recommendation Agent (RA)
  Core Function: Filtering & Scoring
  Data Type Handled: Activity catalog, UPA/ECA outputs
  Key Tooling: FunctionTool: query_activity_database

- Logistics Agent (LA)
  Core Function: Optimization & Scheduling
  Data Type Handled: Ranked activities, location data, timing, budget
  Key Tooling: FunctionTool: Route Optimization (Maps_route_optimizer)

B. Implementation Flow Summary

The workflow adheres to a strict 9-step process, engineered for minimal latency:
- HA Initiation: The Host Agent receives the user query.
- Fan-Out: The Composer Agent triggers the UPA and ECA concurrently via a ParallelAgent.
- UPA Tool Call: UPA executes its database tool to fetch the UserProfile.
- ECA Reasoning: ECA analyzes the query to produce MoodAnalysis constraints.
- Gather & Synthesize: The Composer Agent collects the parallel outputs and uses an LlmAgent to synthesize the data bundle.
- Sequential Processing: The bundle is passed sequentially to the RA.
- RA Decision: The RA applies ECA constraints as hard filters and UPA preferences as soft scores to generate a RankedActivityList.
- LA Optimization: The LA receives the ranked list and uses its routing tool to calculate time, distance, and sequence.
- Final Itinerary: The LA produces the time-boxed, budget-compliant FinalItinerary as the system's output.

3. Technical Implementation Details

A. ADK and Schema Compatibility Fix

A core challenge encountered was ensuring data structures were compatible with the strict Gemini API function-calling protocol. Pydantic's default translation of Dict[str, float] for the preference vector generates the unsupported "additionalProperties": true flag.

Solution: The UserProfile schema was modified to use an explicitly defined, non-ambiguous structure: List[KeyValuePair]. This sacrifices Pythonic dictionary convenience for ADK reliability, ensuring the generated JSON Schema is strictly closed and passes validation.

Python
class KeyValuePair(BaseModel):
    key: str = Field(description="Preference category")
    value: float = Field(description="Preference score (0.0 to 1.0)")
    
class UserProfile(BaseModel):
    preference_vector: List[KeyValuePair] # Corrected structure
    # ... other fields ...

B. Agent Specialization and Non-Duplication

The functional distinction between the RA and LA is maintained by enforcing different output schemas and transformation steps:
RA (Selection): Focuses solely on scoring. Its output, RankedActivityList, is unordered (ranked by score) and contains no temporal data (no start_time or travel_duration).
LA (Optimization): Focuses solely on scheduling. Its output, FinalItinerary, is ordered by time and contains the critical logistical data (e.g., start_time, travel_mode, duration) calculated by its external routing tool.

This strict separation ensures that the system avoids conflicting recommendations and maximizes the specialization benefits of the multi-agent architecture.

4. Future Development Path

To further enhance efficiency and coherence, the immediate future development involves merging the RA and LA into a single, advanced Integrated Planner Agent (IPA). This IPA will leverage a sophisticated instruction set to perform simultaneous multi-objective optimization, weighing relevance score against routing efficiency in a single chain-of-thought, thereby eliminating the sequential data handoff and reducing overall execution time.
