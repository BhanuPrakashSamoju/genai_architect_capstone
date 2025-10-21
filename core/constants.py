# core/constants.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the project root
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# --- Data Paths ---
DATABASE_DIR = BASE_DIR / "database"
DATASET_DIR = BASE_DIR / "dataset"
VECTOR_STORE_DIR = DATABASE_DIR / "vector_store"
LOAN_DB_PATH = DATABASE_DIR / "loan_data" / "LoanDB_BlueLoans4all.sqlite"
SQLITE_DB_URI = f"sqlite:///{LOAN_DB_PATH}"
DB_METADATA_PATH = BASE_DIR / "data" / "metadata.json" # Required by Text2SQL logic
POLICY_DOCS_DIR = DATASET_DIR / "policy_docs"

# --- Azure OpenAI Credentials ---
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# --- Model Names ---
# Ensure these deployments exist in your Azure OpenAI resource
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini") # Primary model for chat/reasoning
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002") # Model for embeddings

# --- Vector Store Config ---
CHROMA_COLLECTION_NAME = "loan_policy_docs"

# --- RAG Config ---
POLICY_DOCS_CHUNK_SIZE = 1000
POLICY_DOCS_CHUNK_OVERLAP = 150
POLICY_SIMILARITY_THRESHOLD = 0.75 # Threshold for policy retrieval relevance
POLICY_SEARCH_K = 3 # Number of documents to retrieve

# --- Agent Settings ---
SQL_AGENT_MAX_RETRIES = 2
SUPERVISOR_ROUTING_CONFIDENCE_THRESHOLD = 0.6 # Minimum confidence for direct routing