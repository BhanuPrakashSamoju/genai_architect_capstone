#!/usr/bin/env python3
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import AzureOpenAIEmbeddings
from langchain_chroma import Chroma
from core.constants import ( # Use constants
    POLICY_DOCS_DIR, VECTOR_STORE_DIR, CHROMA_COLLECTION_NAME,
    POLICY_DOCS_CHUNK_SIZE, POLICY_DOCS_CHUNK_OVERLAP, MIN_DOCUMENT_LENGTH
)
from core.llm_provider import get_embedding_model # Use provider

def setup_embeddings(): # Function name change optional
    """Initialize and return Azure OpenAI embeddings via provider."""
    return get_embedding_model() # Call provider function

def load_pdf_documents(data_dir: Path): # Use constant
    # ... (rest of loading logic) ...
    print(f"Found {len(valid_docs)} valid documents in {data_dir}")
    return valid_docs

def split_documents(docs: List[Document]):
    # ... (use constants for chunk size/overlap) ...
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=POLICY_DOCS_CHUNK_SIZE,
        chunk_overlap=POLICY_DOCS_CHUNK_OVERLAP
    )
    # ... (rest of splitting logic) ...

def create_vector_store(splits: List[Document], embeddings):
    # ... (use constants for VECTOR_STORE_DIR, CHROMA_COLLECTION_NAME) ...
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=str(VECTOR_STORE_DIR),
        collection_name=CHROMA_COLLECTION_NAME,
        # collection_metadata=... # Add if needed
    )
    # ... (rest of creation logic) ...

def process_documents():
    """Main function using constants and provider."""
    docs = load_pdf_documents(POLICY_DOCS_DIR) # Use constant
    # ... (rest of process logic) ...
    create_vector_store(splits, setup_embeddings())

if __name__ == "__main__":
    print("Starting document embedding process...")
    process_documents()
    print("Document embedding process finished.")
