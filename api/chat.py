# api/chat.py
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from api.auth import authenticate
from datetime import datetime

# Import the compiled graph and state definition
from agents.graph import app_graph
from core.state import AgentGraphState # Use the state definition
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
import sqlite3
import os
from core.constants import BASE_DIR
import bcrypt
import jwt

router = APIRouter()

# Paths
USER_DB = os.path.join(BASE_DIR, 'database', 'customer_data', 'loan_user_db.sqlite')
JWT_SECRET_FILE = os.path.join(BASE_DIR, 'database', 'customer_data', '.jwt_secret')


def _load_jwt_secret():
    if os.path.exists(JWT_SECRET_FILE):
        with open(JWT_SECRET_FILE, 'r') as fh:
            return fh.read().strip()
    return None


def _get_user_by_username(username: str):
    try:
        with sqlite3.connect(USER_DB) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT * FROM customer_data WHERE user_name = ? LIMIT 1', (username,))
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error querying user DB: {e}")
        return None


# --- Conversation Storage (Simple in-memory) ---
conversations: Dict[str, List[Dict[str, Any]]] = {}

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    # Optional customer_id (admin can act on behalf of a customer)
    customer_id: Optional[int] = None


class LoginRequest(BaseModel):
    username: str
    password: str

class ChatResponse(BaseModel):
    answer: str
    session_id: str
    # metadata: Optional[Dict[str, Any]] = None # Keep if graph adds useful metadata

# --- API Endpoints ---
@router.post("/chat/", response_model=ChatResponse)
async def chat(request: ChatRequest, ctx: dict = Depends(authenticate)):
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

    # Attach user context based on auth
    caller_role = ctx.get('role')
    caller_sub = ctx.get('sub')

    # If admin provided customer_id override, use that for customer-scoped operations
    acting_customer_ids = None
    if caller_role == 'admin' and request.customer_id:
        acting_customer_ids = [request.customer_id]
    elif caller_role == 'user':
        try:
            acting_customer_ids = [int(caller_sub)]
        except Exception:
            acting_customer_ids = None

    initial_state = AgentGraphState(
        query=request.message,
        context_str=context_str,
        session_id=session_id,
        messages=[HumanMessage(content=request.message)], # Start graph with only the user message
        intent=None,
        needs_customer_data=None,
        customer_ids=acting_customer_ids,
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


@router.post('/auth/login')
async def login(credentials: LoginRequest):
    """Username/password exchange for JWT token."""
    username = credentials.username
    password = credentials.password or ''
    # Look up user
    user = _get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid credentials')

    stored_hash = user.get('password_hash')
    if not stored_hash:
        raise HTTPException(status_code=401, detail='Invalid credentials')

    # stored_hash comes from sqlite as bytes; ensure proper type
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode('utf-8')

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')

    # Load secret and issue token
    secret = _load_jwt_secret()
    if not secret:
        raise HTTPException(status_code=500, detail='Server misconfiguration: JWT secret missing')

    import datetime
    payload = {
        'sub': str(user.get('customer_id')),
        'iat': int(datetime.datetime.utcnow().timestamp()),
        'exp': int((datetime.datetime.utcnow() + datetime.timedelta(days=30)).timestamp())
    }
    token = jwt.encode(payload, secret, algorithm='HS256')
    return {'token': token, 'user': {'customer_id': user.get('customer_id'), 'user_name': user.get('user_name')}}


@router.get('/admin/users')
async def admin_list_users(ctx: dict = Depends(authenticate)):
    """Return list of users for admin. Admin-only endpoint."""
    if ctx.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin access required')
    try:
        with sqlite3.connect(USER_DB) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT customer_id, user_name, email, created_at FROM customer_data')
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail='Error listing users')


@router.get('/customer/loans')
async def customer_loans(customer_id: Optional[int] = None, ctx: dict = Depends(authenticate)):
    """Return loans for the authenticated user (role=user) or for admin if customer_id is provided."""
    # Determine acting customer
    if ctx.get('role') == 'user':
        cid = ctx.get('sub')
    else:
        # Admin can provide customer_id as query param
        cid = customer_id

    if not cid:
        return []

    # Use the existing fetch_customer_data util
    from core.utils import fetch_customer_data
    try:
        data = fetch_customer_data([int(cid)])
        return data
    except Exception as e:
        print(f"Error fetching loans: {e}")
        raise HTTPException(status_code=500, detail='Error fetching loans')

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