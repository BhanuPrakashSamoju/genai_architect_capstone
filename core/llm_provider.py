# core/llm_provider.py
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from .constants import (
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_EMBEDDING_DEPLOYMENT
)

_chat_llm_instance = None
_embedding_llm_instance = None

def get_llm(temperature: float = 0.1) -> AzureChatOpenAI:
    """Gets a singleton instance of the AzureChatOpenAI model."""
    global _chat_llm_instance
    if _chat_llm_instance is None:
        if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT]):
            raise ValueError("Azure OpenAI credentials not found in environment variables.")
        _chat_llm_instance = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_CHAT_DEPLOYMENT,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_version=AZURE_OPENAI_API_VERSION,
            openai_api_key=AZURE_OPENAI_API_KEY,
            temperature=temperature,
            max_retries=3,
        )
        print(f"Initialized AzureChatOpenAI (Deployment: {AZURE_OPENAI_CHAT_DEPLOYMENT})")
    # Update temperature if requested for a specific call (though singleton makes this tricky)
    # For simplicity, we'll use the initial temperature. Consider separate instances if needed.
    # _chat_llm_instance.temperature = temperature
    return _chat_llm_instance

def get_embedding_model() -> AzureOpenAIEmbeddings:
    """Gets a singleton instance of the AzureOpenAIEmbeddings model."""
    global _embedding_llm_instance
    if _embedding_llm_instance is None:
        if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT]):
            raise ValueError("Azure OpenAI credentials not found in environment variables.")
        _embedding_llm_instance = AzureOpenAIEmbeddings(
            azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_key=AZURE_OPENAI_API_KEY,
            chunk_size=16 # Recommended chunk size for Azure embeddings
        )
        print(f"Initialized AzureOpenAIEmbeddings (Deployment: {AZURE_OPENAI_EMBEDDING_DEPLOYMENT})")
    return _embedding_llm_instance