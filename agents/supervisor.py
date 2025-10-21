# agents/supervisor_agent.py
import json
import re
from typing import Optional, Dict, Any, List

# Core components
from core.llm_provider import get_llm
from core.state import AgentGraphState
from core.routing_models import AgentType # Use the Enum for type safety
from core.constants import SUPERVISOR_ROUTING_CONFIDENCE_THRESHOLD
from core.utils import fetch_customer_data, _extract_customer_ids_from_text # Import customer data utils
from langchain_core.messages import AIMessage, HumanMessage

# --- Node Functions ---

def supervisor_router_node(state: AgentGraphState) -> Dict[str, Any]:
    """Determines intent and routes to the appropriate agent or handles ambiguity."""
    print("--- Supervisor Router Node ---")
    query = state["query"]
    context_str = state.get("context_str", "No history.")
    messages = list(state.get("messages", []))
    llm = get_llm(temperature=0.0) # Use 0 temp for deterministic routing

    # Simple inline prompt for routing
    routing_prompt = f"""Analyze the user query below and determine the primary intent and whether it requires customer-specific data.

Conversation History (for context):
{context_str}

User Query: "{query}"

Available Intents:
- SQL_AGENT: For queries about existing loan details (EMI, balance, status, history, specific customer info). Needs customer data if about 'my' loan or specific IDs.
- POLICY_GURU: For questions about rules, eligibility, policies, documents required. Might need customer data for personalized eligibility.
- CALCULATOR: For hypothetical calculations, 'what-if' scenarios (prepayment impact, new loan EMI). Might need customer data for prepayment sims.
- AMBIGUOUS: If the query is unclear, too broad, a greeting, or not related to loans.

Does the query require customer-specific data (e.g., refers to 'my loan', customer ID)? Answer true/false.

Provide your response ONLY in JSON format like this:
{{
  "reasoning": "Brief explanation for your choice.",
  "intent": "SQL_AGENT | POLICY_GURU | CALCULATOR | AMBIGUOUS",
  "needs_customer_data": true | false,
  "confidence": float (0.0 to 1.0) // Your confidence in the intent classification
}}"""

    try:
        response = llm.invoke(routing_prompt)
        # Clean potential markdown backticks
        cleaned_response = response.content.strip().strip('`').strip()
        # Find JSON block
        json_match = re.search(r"\{.*\}", cleaned_response, re.DOTALL)
        if not json_match:
             raise ValueError("LLM did not return a JSON object for routing.")
        routing_decision = json.loads(json_match.group(0))

        intent = routing_decision.get("intent", "AMBIGUOUS").upper()
        needs_data = routing_decision.get("needs_customer_data", False)
        confidence = routing_decision.get("confidence", 0.0)
        reasoning = routing_decision.get("reasoning", "N/A")

        print(f"Supervisor LLM Routing:")
        print(f"  Intent: {intent}, Confidence: {confidence:.2f}, Needs Data: {needs_data}")
        print(f"  Reasoning: {reasoning}")

        # --- Decision Logic ---
        if intent == "AMBIGUOUS" or confidence < SUPERVISOR_ROUTING_CONFIDENCE_THRESHOLD:
            print("Routing: Ambiguous or low confidence -> AMBIGUOUS")
            # Ask for clarification directly
            clarification_message = f"I'm not quite sure how to help with '{query}'. Could you please specify if you're asking about existing loan details, a calculation, or general policy?"
            messages.append(AIMessage(content=clarification_message))
            return {"messages": messages, "intent": "AMBIGUOUS", "final_answer": clarification_message} # End here
        else:
            # Check for customer IDs and set flag/data for next node
            customer_ids = _extract_customer_ids_from_text(query) or _extract_customer_ids_from_text(context_str or "")
            print(f"Supervisor: Extracted Customer IDs: {customer_ids}")
            return {
                "intent": intent,
                "needs_customer_data": needs_data,
                "customer_ids": customer_ids if needs_data else [], # Pass IDs if data needed
                "messages": messages # Pass messages along
            }

    except Exception as e:
        print(f"❌ Error during Supervisor routing: {e}")
        error_msg = f"Sorry, I had trouble understanding your request: '{query}'. Can you rephrase?"
        messages.append(AIMessage(content=error_msg))
        # Route to end with error message
        return {"messages": messages, "intent": "AMBIGUOUS", "final_answer": error_msg}


def fetch_data_node(state: AgentGraphState) -> Dict[str, Any]:
    """Fetches customer data if needed based on supervisor routing."""
    print("--- Fetch Data Node ---")
    needs_data = state.get("needs_customer_data", False)
    customer_ids = state.get("customer_ids", [])
    customer_data = None # Default to None

    if needs_data and customer_ids:
        print(f"Fetching data for customer IDs: {customer_ids}")
        customer_data = fetch_customer_data(customer_ids) # Use util function
        if not customer_data:
            print("Fetch Data Node: No data found for specified customer IDs.")
            # Decide how to handle this - maybe route to ambiguous/clarification?
            # For now, proceed but agent node will handle lack of data.
    elif needs_data and not customer_ids:
        print("Fetch Data Node: 'needs_customer_data' is true, but no customer IDs found.")
        # This could also trigger clarification
        pass # Let agent node handle missing data
    else:
        print("Fetch Data Node: No customer data needed.")

    return {"customer_data": customer_data} # Update state with fetched data (or None)


def handle_error_node(state: AgentGraphState) -> Dict[str, Any]:
    """Handles errors reported by agent nodes."""
    print("--- Handle Error Node ---")
    error_msg = state.get("error_message", "An unspecified error occurred.")
    messages = list(state.get("messages", []))
    final_answer = f"I'm sorry, I encountered an error: {error_msg}. Please try rephrasing your request or contact support."
    messages.append(AIMessage(content=final_answer))
    return {"messages": messages, "final_answer": final_answer}