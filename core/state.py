# core/state.py
from typing import TypedDict, Sequence, Optional, List, Dict, Any, Literal, Annotated
import operator
from langchain_core.messages import BaseMessage

class AgentGraphState(TypedDict):
    """
    Represents the state passed between nodes in the LangGraph.

    Attributes:
        query: Original user input query.
        context_str: String representation of recent conversation history.
        session_id: Unique identifier for the conversation session.
        messages: Sequence of BaseMessage objects (user, ai). Use operator.add for accumulation.
        intent: The agent/route determined by the supervisor ('SQL_AGENT', 'POLICY_GURU', 'CALCULATOR', 'AMBIGUOUS', 'MULTI_DOMAIN').
        needs_customer_data: Boolean flag indicating if the query requires customer-specific DB lookup.
        customer_ids: List of customer IDs extracted from query or context.
        customer_data: List of dictionaries containing fetched data for identified customer_ids.
        agent_outcome: Stores the result or status from the last executed agent node (e.g., success, failure, clarification_needed).
        final_answer: The consolidated natural language answer to be presented to the user.
        error_message: Stores any error message encountered during processing.
        multi_domain_agents: List of agent names identified for multi-domain queries.
    """
    query: str
    context_str: Optional[str]
    session_id: Optional[str]
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: Optional[Literal["SQL_AGENT", "WHAT_IF_CALCULATOR", "POLICY_GURU", "AMBIGUOUS", "MULTI_DOMAIN"]]
    needs_customer_data: Optional[bool]
    customer_ids: Optional[List[int]]
    customer_data: Optional[List[Dict[str, Any]]]
    agent_outcome: Optional[str] # e.g., "success", "clarification_needed", "enhancement_needed", "error"
    final_answer: Optional[str]
    error_message: Optional[str]
    multi_domain_agents: Optional[List[str]]