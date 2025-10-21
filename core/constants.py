# core/constants.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the project root
load_dotenv()

# --- Base Directory ---
BASE_DIR = Path(__file__).parent.parent

# --- Data Paths (Keep as before) ---
DATABASE_DIR = BASE_DIR / "database"
DATASET_DIR = BASE_DIR / "dataset"
VECTOR_STORE_DIR = DATABASE_DIR / "vector_store"
LOAN_DB_PATH = DATABASE_DIR / "loan_data" / "LoanDB_BlueLoans4all.sqlite"
SQLITE_DB_URI = f"sqlite:///{LOAN_DB_PATH}"
DB_METADATA_PATH = BASE_DIR / "data" / "metadata.json" # If still needed by Text2SQL
POLICY_DOCS_DIR = DATASET_DIR / "policy_docs"

# --- Azure OpenAI Credentials (Chat LLM) ---
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
# OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE", "azure") # Loaded directly in llm_provider

# --- Azure OpenAI Credentials (Embedding LLM) ---
AZURE_OPENAI_EMBEDDING_KEY = os.getenv("AZURE_OPENAI_EMBEDDING_KEY", AZURE_OPENAI_API_KEY) # Fallback to main key if specific one isn't set
AZURE_OPENAI_EMBEDDING_ENDPOINT = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT", AZURE_OPENAI_ENDPOINT) # Fallback to main endpoint
AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", AZURE_OPENAI_API_VERSION) # Fallback to main version
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-small")
# AZURE_OPENAI_EMBEDDING_BASE_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_BASE_MODEL", "text-embedding-ada-002") # Optional base model name

# --- Vector Store Config (Keep as before) ---
CHROMA_COLLECTION_NAME = "loan_policy_docs"

# Vector store settings
COLLECTION_METADATA = {"use_type": "PRODUCTION"}

# Document processing settings
MIN_DOCUMENT_LENGTH = 100


# Azure OpenAI settings
EMBEDDING_MODEL = "text-embedding-3-small"
MODEL_NAME = "gpt4o"  # Using GPT-4 for complex reasoning and calculations

# Retrieval settings
SEARCH_K = 2

# --- RAG Config (Keep as before) ---
POLICY_DOCS_CHUNK_SIZE = 1000
POLICY_DOCS_CHUNK_OVERLAP = 150
POLICY_SIMILARITY_THRESHOLD = 0.75
POLICY_SEARCH_K = 3

# --- Agent Settings (Keep as before) ---
SQL_AGENT_MAX_RETRIES = 2
SUPERVISOR_ROUTING_CONFIDENCE_THRESHOLD = 0.6