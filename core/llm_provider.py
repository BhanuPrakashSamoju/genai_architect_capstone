# core/llm_provider.py
import os
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
# Import constants to access environment variable names (though we load directly via os.getenv)
from .constants import (
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDING_KEY, AZURE_OPENAI_EMBEDDING_ENDPOINT, AZURE_OPENAI_EMBEDDING_API_VERSION,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME #, AZURE_OPENAI_EMBEDDING_BASE_MODEL
)

# Singleton instances
_chat_llm_instance = None
_embedding_llm_instance = None

def get_llm(temperature: float = 0.2) -> AzureChatOpenAI: # Default temperature from user code
    """Gets a singleton instance of the AzureChatOpenAI model using specific env vars."""
    global _chat_llm_instance
    if _chat_llm_instance is None:
        # Load directly using os.getenv as in user's example
        api_key = AZURE_OPENAI_API_KEY
        endpoint = AZURE_OPENAI_ENDPOINT
        api_version = AZURE_OPENAI_API_VERSION
        deployment = AZURE_OPENAI_DEPLOYMENT
        api_type = "azure"  

        if not all([api_key, endpoint, api_version, deployment]):
            raise ValueError("Required Azure OpenAI chat credentials (KEY, ENDPOINT, API_VERSION, DEPLOYMENT) not found in environment variables.")

        try:
            _chat_llm_instance = AzureChatOpenAI(
                azure_deployment=deployment,
                openai_api_version=api_version,
                openai_api_key=api_key,
                azure_endpoint=endpoint,
                openai_api_type=api_type,
                temperature=temperature, # Use passed temperature
                max_retries=3,
                # streaming=False, # Uncomment if needed
            )
            print(f"Initialized AzureChatOpenAI (Deployment: {deployment})")
        except Exception as e:
             print(f"❌ Error initializing AzureChatOpenAI: {e}")
             raise RuntimeError(f"Could not initialize Chat LLM: {e}")

    # Note: If temperature needs to change dynamically, managing singletons becomes complex.
    # For now, it uses the temperature from the first call.
    return _chat_llm_instance

def get_embedding_model() -> AzureOpenAIEmbeddings:
    """Gets a singleton instance of the AzureOpenAIEmbeddings model using specific env vars."""
    global _embedding_llm_instance
    if _embedding_llm_instance is None:
        # Load directly using os.getenv as in user's example
        api_key = AZURE_OPENAI_EMBEDDING_KEY
        endpoint = AZURE_OPENAI_EMBEDDING_ENDPOINT
        api_version = AZURE_OPENAI_EMBEDDING_API_VERSION
        deployment = AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        # base_model = os.getenv("AZURE_OPENAI_EMBEDDING_BASE_MODEL") # Optional base model

        # Fallback logic (use chat credentials if specific embedding ones aren't set)
        if not api_key: api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not endpoint: endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not api_version: api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        if not deployment: deployment = "text-embedding-ada-002" # Sensible default

        if not all([api_key, endpoint, api_version, deployment]):
            raise ValueError("Required Azure OpenAI embedding credentials (KEY, ENDPOINT, API_VERSION, DEPLOYMENT_NAME) not found in environment variables.")

        try:
            _embedding_llm_instance = AzureOpenAIEmbeddings(
                azure_endpoint=endpoint,
                # model=base_model, # Pass base model name if required by your setup/version
                azure_deployment=deployment,
                api_key=api_key,
                api_version=api_version,
                chunk_size=16 # Recommended for Azure embeddings
            )
            print(f"Initialized AzureOpenAIEmbeddings (Deployment: {deployment})")
        except Exception as e:
             print(f"❌ Error initializing AzureOpenAIEmbeddings: {e}")
             raise RuntimeError(f"Could not initialize Embedding LLM: {e}")

    return _embedding_llm_instance