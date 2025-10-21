# agents/policy_guru.py
import numpy as np
from typing import Dict, Any, List, Tuple
from langchain_core.documents import Document

# Core components
from core.llm_provider import get_llm, get_embedding_model
from core.vector_store import get_retriever
from core.state import AgentGraphState
from core.constants import POLICY_SIMILARITY_THRESHOLD
from langchain_core.messages import AIMessage

# --- Helper Functions ---

def _calculate_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculates cosine similarity between two numpy vectors."""
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    vec1_norm = vec1 / np.linalg.norm(vec1)
    vec2_norm = vec2 / np.linalg.norm(vec2)
    similarity = np.dot(vec1_norm, vec2_norm)
    return float(np.clip(similarity, 0.0, 1.0))

def _format_docs_for_llm(docs: List[Document]) -> str:
    """Formats retrieved documents into a context string for the LLM."""
    if not docs:
        return "No relevant policy documents found."
    context = ""
    for i, doc in enumerate(docs):
        source = doc.metadata.get('source', f'Document {i+1}')
        context += f"--- Document Source: {source} ---\n"
        context += doc.page_content
        context += "\n-------------------------------------\n\n"
    return context.strip()

# --- LangGraph Node Function ---
def policy_guru_node(state: AgentGraphState) -> Dict[str, Any]:
    """Retrieves policy docs, filters by similarity, and generates an answer."""
    print("--- Policy Guru Node ---")
    query = state["query"]
    messages = list(state.get("messages", []))
    outcome = "error"
    final_answer = "Sorry, I couldn't retrieve the policy information."
    error_message = None
    enhancement_needed = False

    try:
        llm = get_llm(temperature=0.0) # Use 0 temp for factual RAG
        embedding_model = get_embedding_model()
        retriever = get_retriever() # Gets retriever with k from constants

        # 1. Retrieve Documents
        print(f"Policy Guru: Retrieving documents for: '{query[:100]}...'")
        retrieved_docs: List[Document] = retriever.invoke(query)
        print(f"Policy Guru: Retrieved {len(retrieved_docs)} documents initially.")

        # 2. Filter by Similarity (Optional but recommended)
        filtered_docs: List[Document] = []
        if retrieved_docs:
            query_embedding = np.array(embedding_model.embed_query(query))
            if query_embedding.size > 0:
                for doc in retrieved_docs:
                    try:
                        doc_embedding = np.array(embedding_model.embed_query(doc.page_content))
                        if doc_embedding.size > 0:
                            similarity = _calculate_cosine_similarity(query_embedding, doc_embedding)
                            if similarity >= POLICY_SIMILARITY_THRESHOLD:
                                doc.metadata['similarity_score'] = similarity # Store score
                                filtered_docs.append(doc)
                                print(f"  Including doc (Sim: {similarity:.4f}): {doc.metadata.get('source', 'Unknown')}")
                            # else:
                                # print(f"  Excluding doc (Sim: {similarity:.4f}): {doc.metadata.get('source', 'Unknown')}")
                    except Exception as embed_err:
                        print(f"  Skipping doc due to embedding/comparison error: {embed_err}")

            print(f"Policy Guru: {len(filtered_docs)} documents passed similarity threshold ({POLICY_SIMILARITY_THRESHOLD}).")
        else:
             print("Policy Guru: No documents retrieved.")


        # 3. Handle No Relevant Documents Found
        if not filtered_docs:
             # [cite_start]Based on Phase 3 Fallback: Supervisor retries if score low/no docs [cite: 503-505]
             outcome = "enhancement_needed"
             enhancement_needed = True
             final_answer = "I couldn't find specific policy documents matching your query. Could you provide more context or rephrase?" # Message for supervisor context
             print("Policy Guru: No relevant documents found after filtering. Signaling enhancement.")

        else:
            # 4. Generate Answer using LLM
            context_str = _format_docs_for_llm(filtered_docs)
            prompt = f"""You are the Policy Guru for BlueLoans4all. Answer the user's question based *only* on the provided policy document excerpts. Cite the source document mentioned in the context using [Source: <source_name>]. If the answer isn't in the excerpts, say so clearly.

Policy Document Excerpts:
{context_str}

User Question: {query}

Answer:"""

            print("Policy Guru: Generating answer from filtered documents...")
            ai_response = llm.invoke(prompt)
            final_answer = ai_response.content.strip()
            outcome = "success"
            print("Policy Guru: Answer generated successfully.")

    except Exception as e:
        print(f"❌ Policy Guru Node Error: {e}")
        error_message = f"Policy Guru failed: {str(e)}"
        outcome = "error"
        # Provide a generic error message
        final_answer = "Sorry, I encountered an error while retrieving policy information."


    # Update state
    # Only add AI message on success
    if outcome == "success":
        messages.append(AIMessage(content=final_answer))

    return {
        "messages": messages,
        "agent_outcome": outcome,
        "final_answer": final_answer if outcome == "success" else None,
        "error_message": error_message,
        "enhancement_needed": enhancement_needed,
        # Optionally add retrieved sources to state for logging/audit
        # "retrieved_sources": [d.metadata for d in filtered_docs] if 'filtered_docs' in locals() and filtered_docs else []
    }