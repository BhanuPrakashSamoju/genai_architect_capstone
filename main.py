# main.py
import os
import sys
from pathlib import Path

# --- Centralized Pycache Setup ---
# (Keep the pycache setup from loan-navigator-assistant/main.py)
# ... [pycache setup code] ...
project_root = Path(__file__).parent
cache_dir = project_root / ".pycache"
cache_dir.mkdir(exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(cache_dir)
if hasattr(sys, "pycache_prefix"):
    if not sys.pycache_prefix:
        sys.pycache_prefix = str(cache_dir)
        print(f"✅ Set sys.pycache_prefix to: {sys.pycache_prefix}")
    else:
        print(f"✅ sys.pycache_prefix already set to: {sys.pycache_prefix}")
else:
    print(f"✅ PYTHONPYCACHEPREFIX set to: {cache_dir}")


from dotenv import load_dotenv

# --- Load Environment Variables ---
# Load .env file from the project root
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print(f"✅ Loaded environment variables from: {dotenv_path}")
else:
    print(f"⚠️ Warning: .env file not found at {dotenv_path}. Azure credentials might be missing.")


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Import API Router ---
# Adjust the import path based on your structure
from api.chat import router as chat_router # Correct import path

# --- App Initialization ---
app = FastAPI(
    title="Loan Navigator Agent API",
    description="Multi-agent system for handling loan queries.",
    version="1.1.0", # Increment version
    docs_url="/docs", # Enable Swagger UI
    redoc_url="/redoc" # Enable ReDoc
)

# --- CORS Middleware ---
# Allow requests from Streamlit frontend (and potentially others)
# Adjust origins as needed for your deployment
origins = [
    "http://localhost:8501", # Streamlit default
    "http://127.0.0.1:8501",
    # Add other origins if needed, e.g., your deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"], # Allows all headers
)

# --- Include API Routers ---
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"]) # Add prefix and tags

# --- Root Endpoint ---
@app.get("/", tags=["Status"])
async def read_root():
    """Root endpoint providing basic status."""
    return {"status": "Loan Navigator API is running."}

# --- Startup Event (Optional) ---
@app.on_event("startup")
async def startup_event():
    """Actions to perform on application startup."""
    print("🚀 Loan Navigator API starting up...")
    # You could pre-load models or check connections here if needed
    # Example: Check if Azure credentials are loaded
    from core.constants import AZURE_OPENAI_API_KEY
    if not AZURE_OPENAI_API_KEY:
         print("🚨 WARNING: Azure OpenAI API key is missing!")
    print("✅ API ready.")

# --- Run with Uvicorn (for local development) ---
if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    # Use reload=True for development to auto-reload on code changes
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)