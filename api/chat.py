# api/chat.py
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

# Import the compiled graph and state definition
from agents.graph import app_graph
from core.state import AgentGraphState # Use the state definition
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage

router = APIRouter()

# --- Conversation Storage (Simple in-memory) ---
conversations: Dict[str, List[Dict[str, Any]]] = {}

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    session_id: str
    # metadata: Optional[Dict[str, Any]] = None # Keep if graph adds useful metadata

# --- API Endpoints ---
@router.post("/chat/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Processes chat message using the simplified LangGraph application."""
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    if session_id not in conversations:
        conversations[session_id] = []
        print(f"New session started: {session_id}")

    # Add user message to history *before* calling graph
    user_message_record = {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
    conversations[session_id].append(user_message_record)
    print(f"Received: '{request.message[:100]}' (Session: {session_id})")

    # --- Prepare Initial State ---
    # Create context string from recent history (excluding current message)
    history_limit = 5
    recent_history = conversations[session_id][-(history_limit + 1):-1]
    context_str = "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in recent_history]) or "No previous conversation history."

    initial_state = AgentGraphState(
        query=request.message,
        context_str=context_str,
        session_id=session_id,
        messages=[HumanMessage(content=request.message)], # Start graph with only the user message
        intent=None,
        needs_customer_data=None,
        customer_ids=None,
        customer_data=None,
        agent_outcome=None,
        final_answer=None,
        error_message=None,
        multi_domain_agents=None
    )

    # --- Invoke LangGraph ---
    try:
        config = {"configurable": {"session_id": session_id}} # Pass session_id for potential persistence later
        final_state = app_graph.invoke(initial_state, config=config)

        # Extract final answer - should be in 'final_answer' or the last message
        final_answer = final_state.get("final_answer")
        if not final_answer and final_state.get("messages"):
             last_message = final_state["messages"][-1]
             if isinstance(last_message, AIMessage):
                 final_answer = last_message.content

        # Default if no answer found
        if not final_answer:
            final_answer = "Sorry, I wasn't able to generate a response for that."
            print("⚠️ Graph finished without a final_answer or AIMessage.")

    except Exception as e:
        print(f"❌ Error invoking LangGraph: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

    # --- Add Assistant Response to History ---
    assistant_message_record = {"role": "assistant", "content": final_answer, "timestamp": datetime.now().isoformat()}
    conversations[session_id].append(assistant_message_record)

    # --- Return Response ---
    end_time = time.time()
    print(f"Responding (took {end_time - start_time:.2f}s): '{final_answer[:100]}...'")

    return ChatResponse(
        answer=final_answer,
        session_id=session_id,
        # metadata= # Add metadata if needed from final_state
    )

# get_history and clear_history remain largely the same
# ... [get_history and clear_history code from previous step] ...
@router.get("/chat/history/{session_id}", response_model=List[Dict[str, Any]])
async def get_history(session_id: str):
    """Retrieve the conversation history for a given session ID."""
    if session_id not in conversations:
        raise HTTPException(status_code=404, detail=f"Session ID '{session_id}' not found.")
    return conversations[session_id]


@router.delete("/chat/history/{session_id}", status_code=200)
async def clear_history(session_id: str):
    """Clear the conversation history for a given session ID."""
    if session_id in conversations:
        del conversations[session_id]
        # Add logic here to clear LangGraph checkpoints if you implement persistence.
        print(f"Cleared in-memory chat history for session ID: {session_id}")
        return {"message": "Chat history cleared successfully.", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail=f"Session ID '{session_id}' not found.")