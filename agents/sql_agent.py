# agents/sql_agent.py
import json
import os
import time
from typing import Optional, List, Any, Dict, Union

from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage
from langchain_core.runnables.base import Runnable

# Core components
from core.constants import SQLITE_DB_URI, DB_METADATA_PATH
from core.llm_provider import get_llm
from core.state import AgentGraphState # Import state definition

# Custom tools
from agents.tools.sql_tools import CustomSQLDatabaseToolkit

# Pydantic models (required by the original Text2SQL logic)
from pydantic import BaseModel
class SQLAgentResponse(BaseModel):
    SQL: str
    sql_output: str
    response: str
    sender: str = "SQLAgent"

class ColumnInformation(BaseModel):
    name: str
    dtype: str
    description: str
    nullable: Optional[bool] = None
    unique_count: Optional[int] = None
    sample_values: Optional[List[Any]] = None

# --- Singleton Agent Executor ---
# Initialize the complex agent setup once
_sql_agent_executor: Optional[Runnable] = None
_sql_db_connection: Optional[SQLDatabase] = None
_table_metadata: Optional[Dict] = None

def _initialize_sql_agent():
    """Initializes the Langchain SQL agent executor (singleton)."""
    global _sql_agent_executor, _sql_db_connection, _table_metadata
    if _sql_agent_executor is not None:
        return _sql_agent_executor

    print("Initializing SQL Agent Executor...")
    llm = get_llm(temperature=0.0) # Use 0 temp for deterministic SQL

    # --- Database Connection ---
    try:
        db_path = SQLITE_DB_URI.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found at: {db_path}")
        _sql_db_connection = SQLDatabase.from_uri(SQLITE_DB_URI)
        print(f"SQL Agent connected to DB: {SQLITE_DB_URI}")
    except Exception as e:
        print(f"❌ SQL Agent DB connection failed: {e}")
        raise RuntimeError(f"Failed to load database: {e}")

    # --- Metadata Loading ---
    _table_metadata = {}
    try:
        if DB_METADATA_PATH.exists(): # Use Path object's exists()
            with open(DB_METADATA_PATH, 'r') as f:
                metadata_dict = json.load(f)
            for table_name, columns in metadata_dict.items():
                _table_metadata[table_name] = [ColumnInformation(**col) for col in columns if all(k in col for k in ['name', 'dtype', 'description'])]
            print(f"SQL Agent loaded metadata from: {DB_METADATA_PATH}")
        else:
            print(f"⚠️ SQL Agent: Metadata file not found at {DB_METADATA_PATH}. Using basic schema.")
    except Exception as e:
        print(f"⚠️ SQL Agent: Failed to load metadata: {e}. Using basic schema.")

    # --- Format Metadata for Prompt ---
    if not _table_metadata:
        try:
            table_metadata_str = _sql_db_connection.get_table_info()
            if not table_metadata_str: raise ValueError("DB returned empty schema.")
            print("SQL Agent using basic schema info from DB for prompt.")
        except Exception as e:
            print(f"❌ SQL Agent critical error: Could not get schema info: {e}")
            raise RuntimeError(f"Cannot initialize SQL agent without schema: {e}")
    else:
        formatted_text = "DATABASE SCHEMA INFORMATION (with descriptions and samples):\n\n"
        for table_name, columns in _table_metadata.items():
            formatted_text += f"Table: {table_name}\n"
            for col in columns:
                formatted_text += f"  - {col.name} ({col.dtype}): {col.description}\n"
                if col.sample_values:
                    samples = ", ".join([str(v) for v in col.sample_values[:3]])
                    formatted_text += f"    Sample values: {samples}\n"
            formatted_text += "\n"
        table_metadata_str = formatted_text

    # --- Create Agent ---
    try:
        toolkit = CustomSQLDatabaseToolkit(db=_sql_db_connection, llm=llm) # Pass LLM to toolkit

        # Simple inline prompts (as requested)
        PREFIX = f"""You are an agent designed to interact with a SQL database containing loan information.
Given an input question about loans, create a syntactically correct {{dialect}} query to run.
Then, look at the results of the query and return a helpful, natural language answer to the user.

IMPORTANT RULES:
- Unless the user specifies a specific number of examples, always limit your query to at most 10 results using LIMIT 10.
- Never query for all columns from a table unless necessary. Only request the columns needed to answer the question (e.g., SELECT monthly_emi, status FROM loan_data...). Use SELECT * sparingly.
- You have access to tools: {', '.join([t.name for t in toolkit.get_tools()])}. ONLY use these provided tools.
- ONLY use the information returned by the tools to construct your final answer.
- You MUST use the 'sql_db_query_checker' tool to validate your query BEFORE using 'sql_db_query'.
- **CRITICAL: DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE). Only SELECT queries are allowed.**
- If the question does not seem related to the loan database, return "I cannot answer questions unrelated to loan data."

DATABASE SCHEMA:
{table_metadata_str}

Begin! Respond with the final natural language answer directly.
"""
        SUFFIX = """Thought: The user is asking a question. I need to:
1. Understand the question and identify necessary information.
2. Construct a {dialect} SELECT query.
3. Use 'sql_db_query_checker' to validate the query.
4. If valid, use 'sql_db_query' to execute it.
5. Analyze the results and formulate a natural language answer.
Remember all rules.

User Question: {input}
Agent Action:""" # Langchain agent needs input key

        _sql_agent_executor = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=True, # Enable for debugging
            prefix=PREFIX.format(dialect=_sql_db_connection.dialect, table_metadata_str=table_metadata_str), # Pre-format dialect and schema
            suffix=SUFFIX, # Use simplified suffix
            agent_type="openai-tools",
            handle_parsing_errors="Check your output and make sure it conforms!", # Provide specific error feedback
            agent_executor_kwargs={
                "return_intermediate_steps": True,
                "handle_parsing_errors": True,
            },
        )
        print("✅ SQL Agent Executor initialized successfully.")
        return _sql_agent_executor

    except Exception as e:
        print(f"❌ Failed to create SQL Agent Executor: {e}")
        raise RuntimeError(f"SQL Agent Executor creation failed: {e}")

def _extract_sql_info_from_steps(intermediate_steps: List) -> Tuple[str, str]:
    """Extracts the last SQL query and its direct result from agent steps."""
    sql_query = "N/A"
    sql_output = "N/A"
    if not intermediate_steps:
        return sql_query, sql_output

    for step in reversed(intermediate_steps):
        if len(step) == 2:
            action, observation = step
            if hasattr(action, 'tool') and action.tool == "sql_db_query":
                if hasattr(action, 'tool_input') and isinstance(action.tool_input, dict) and "query" in action.tool_input:
                    sql_query = action.tool_input["query"]
                    sql_output = str(observation)
                    return sql_query, sql_output # Return the first (last executed) sql_db_query found

    print("⚠️ SQL Agent: Could not find 'sql_db_query' execution in intermediate steps.")
    return sql_query, sql_output


# --- LangGraph Node Function ---
def sql_agent_node(state: AgentGraphState) -> Dict[str, Any]:
    """Executes the SQL agent logic."""
    print("--- SQL Agent Node ---")
    query = state["query"]
    messages = list(state.get("messages", [])) # Get existing messages
    outcome = "error" # Default outcome
    final_answer = "Sorry, I encountered an error while accessing loan data."
    error_message = None
    clarification_needed = False
    clarification_message = None
    sql_query_executed = "N/A"

    try:
        agent_executor = _initialize_sql_agent() # Get or init executor
        if not agent_executor:
            raise RuntimeError("SQL Agent Executor failed to initialize.")

        agent_input = {"input": query}
        agent_result = agent_executor.invoke(agent_input)

        final_answer = agent_result.get("output", "No final output generated.")
        intermediate_steps = agent_result.get("intermediate_steps", [])
        sql_query_executed, sql_output = _extract_sql_info_from_steps(intermediate_steps)

        # Basic check for zero results or errors mentioned in the final answer
        answer_lower = final_answer.lower()
        if sql_output == "[]" or sql_output == "" or "no results" in answer_lower or "could not find" in answer_lower or "no data" in answer_lower:
             print(f"SQL Agent: Zero results detected for query '{query}'.")
             outcome = "clarification_needed"
             clarification_needed = True
             # Use a simpler clarification message
             clarification_message = f"I couldn't find specific data for '{query}'. Could you please verify the details (like Loan ID or Customer ID) or try rephrasing?"
             final_answer = clarification_message # The response *is* the clarification
        elif "error" in answer_lower or "cannot answer" in answer_lower:
             print(f"SQL Agent: Potential error or inability to answer query '{query}'.")
             outcome = "clarification_needed" # Treat errors/refusals as needing clarification
             clarification_needed = True
             clarification_message = f"I had trouble processing the data request for '{query}'. Could you simplify or rephrase the question?"
             final_answer = clarification_message
        else:
             outcome = "success"
             print(f"SQL Agent executed successfully for query '{query}'.")

    except Exception as e:
        print(f"❌ SQL Agent Node Error: {e}")
        error_message = f"SQL Agent failed: {str(e)}"
        outcome = "error"
        # Generate a generic clarification if error occurs
        clarification_needed = True
        clarification_message = f"Sorry, I encountered an error trying to get loan data for '{query}'. Please try rephrasing."
        final_answer = clarification_message

    # Update state
    # Don't add AI message here if clarification is needed, supervisor will add it
    if outcome == "success":
        messages.append(AIMessage(content=final_answer))

    return {
        "messages": messages,
        "agent_outcome": outcome,
        "final_answer": final_answer if outcome == "success" else None, # Only set final_answer on success
        "error_message": error_message,
        "clarification_needed": clarification_needed,
        "clarification_message": clarification_message,
        # Optionally add SQL query to state for logging/audit
        # "last_sql_query": sql_query_executed
    }