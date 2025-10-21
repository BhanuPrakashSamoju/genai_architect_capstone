#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from typing import List
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
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
    """Load and filter PDF documents from the data directory."""
    docs = []
    for pdf_file in data_dir.glob("*.pdf"):
        try:
            print(f"Processing {pdf_file.name}")
            loader = PyPDFLoader(str(pdf_file), extract_images=False)
            docs.extend(loader.load())
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
            continue

    # Filter out empty or very short documents
    valid_docs = [
        doc for doc in docs if len(doc.page_content.strip()) > MIN_DOCUMENT_LENGTH
    ]

    print(f"Found {len(valid_docs)} valid documents in {data_dir}")
    return valid_docs

def split_documents(docs: List[Document]):
    """Split documents into smaller chunks."""
    if not docs:
        print("No valid documents to split")
        return []
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=POLICY_DOCS_CHUNK_SIZE,
        chunk_overlap=POLICY_DOCS_CHUNK_OVERLAP
    )
    splits = text_splitter.split_documents(docs)
    print(f"Created {len(splits)} text chunks")
    return splits

def create_vector_store(splits: List[Document], embeddings):
    """Create a fresh vector store, removing any existing one."""
    # Remove existing vector store if it exists
    if VECTOR_STORE_DIR.exists():
        import shutil

        shutil.rmtree(VECTOR_STORE_DIR)

    # Create vector store directory
    VECTOR_STORE_DIR.parent.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir()

    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=str(VECTOR_STORE_DIR),
        collection_name=CHROMA_COLLECTION_NAME,
        # collection_metadata=... # Add if needed
    )
    print(f"Successfully created vector store at {VECTOR_STORE_DIR}")
    return vectorstore

def process_documents():
    """Main function using constants and provider."""
    docs = load_pdf_documents(POLICY_DOCS_DIR) # Use constant
    if not docs:
        return

    splits = split_documents(docs)
    if not splits:
        return
    create_vector_store(splits, setup_embeddings())

if __name__ == "__main__":
    print("Starting document embedding process...")
    process_documents()
    print("Document embedding process finished.")
