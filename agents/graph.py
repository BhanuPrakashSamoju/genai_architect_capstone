# agents/graph.py
import operator
from typing import TypedDict, Sequence, Optional, List, Dict, Any, Literal, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Import state definition
from core.state import AgentGraphState

# Import node functions
from agents.supervisor_agent import supervisor_router_node, fetch_data_node, handle_error_node
from agents.sql_agent import sql_agent_node
from agents.policy_guru import policy_guru_node
from agents.calculator_agent import calculator_node

# --- Graph Definition ---
workflow = StateGraph(AgentGraphState)

# --- Define Nodes ---
workflow.add_node("supervisor", supervisor_router_node) # Entry point for routing
workflow.add_node("fetch_data", fetch_data_node)     # Node to fetch data if needed
workflow.add_node("sql_agent", sql_agent_node)
workflow.add_node("policy_guru", policy_guru_node)
workflow.add_node("calculator", calculator_node)
workflow.add_node("handle_error", handle_error_node) # Node to handle agent errors

# --- Define Edges ---

# Start with the supervisor
workflow.set_entry_point("supervisor")

# After supervisor, always try to fetch data (even if it does nothing)
workflow.add_edge("supervisor", "fetch_data")

# Conditional routing after fetching data (or skipping fetch)
def route_after_fetch(state: AgentGraphState):
    intent = state.get("intent")
    print(f"Routing after fetch. Intent: {intent}")
    if intent == "SQL_AGENT":
        return "sql_agent"
    elif intent == "POLICY_GURU":
        return "policy_guru"
    elif intent == "CALCULATOR":
        return "calculator"
    elif intent == "AMBIGUOUS": # Supervisor decided ambiguity
        return END # End directly, supervisor added clarification msg
    else: # Should not happen with current supervisor logic
        print(f"⚠️ Unknown intent after fetch: {intent}. Routing to error handler.")
        return "handle_error" # Or END

workflow.add_conditional_edges(
    "fetch_data",
    route_after_fetch,
    {
        "sql_agent": "sql_agent",
        "policy_guru": "policy_guru",
        "calculator": "calculator",
        "handle_error": "handle_error", # Route unexpected intents here
        END: END,
    }
)

# Conditional routing after each agent node
def route_after_agent(state: AgentGraphState):
    outcome = state.get("agent_outcome")
    print(f"Routing after agent. Outcome: {outcome}")
    if outcome == "success":
        return END # Agent succeeded, end the flow
    elif outcome == "clarification_needed":
        # Let supervisor format/send the clarification message stored in state
        # Route to error handler for now, enhance later if needed
        # return "handle_clarification_supervisor" # Need a supervisor node for this
        print("Agent needs clarification, routing to error handler (for now).")
        return "handle_error" # Simplification: Treat clarification needed as error for now
    elif outcome == "enhancement_needed":
         # Route back to supervisor to enhance? Or handle error?
         # return "enhance_query_supervisor" # Need supervisor node
         print("Agent needs enhancement, routing to error handler (for now).")
         return "handle_error"
    else: # Includes "error" or None
        return "handle_error"

workflow.add_conditional_edges("sql_agent", route_after_agent)
workflow.add_conditional_edges("policy_guru", route_after_agent)
workflow.add_conditional_edges("calculator", route_after_agent)

# Error handler always ends the graph
workflow.add_edge("handle_error", END)

# --- Compile the Graph ---
app_graph = workflow.compile()
print("✅ Simple LangGraph application compiled.")

# Optional: Visualize
try:
    graph_img = app_graph.get_graph().draw_png()
    with open("loan_navigator_graph_simple.png", "wb") as f:
        f.write(graph_img)
    print("Graph visualization saved to loan_navigator_graph_simple.png")
except Exception as e:
    print(f"Could not draw graph (requires graphviz): {e}")