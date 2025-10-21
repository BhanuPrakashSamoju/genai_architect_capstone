"""
Base agent interface and types for the loan-navigator-suite.
Defines the contract that all agents must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List # Added List
from dataclasses import dataclass, field
from core.prompt_loader import prompt_loader
from core.factory import get_chat_llm


@dataclass
class AgentResponse:
    """Simplified response from any agent."""
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list) # Corrected type hint
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all agents in the system."""

    def __init__(self, agent_name: str, temperature: float = 0.1): # Changed prompt_source to agent_name
        """
        Initialize the base agent with prompt loading and LLM setup.

        Args:
            agent_name: Name of the agent, used to load prompts (e.g., 'sql_agent').
            temperature: Temperature setting for the chat LLM (default: 0.1).
        """
        self.agent_name = agent_name
        # Use absolute path from constants
        from core.constants import PROMPTS_DIR
        # Pass the directory path to PromptLoader
        self.prompts = prompt_loader.load_prompts(agent_name) # prompt_loader needs the directory path
        self.llm = get_chat_llm(temperature=temperature)
        print(f"Initialized {self.__class__.__name__} with prompts for '{agent_name}'")

    @abstractmethod
    def process(self, query_input: Union[str, Dict[str, Any]], retry_count: int = 0) -> AgentResponse: # Added retry_count
        """
        Process a user query (string or dict) and return a structured response.
        Added retry_count for fallback logic.
        """
        pass

    def handle_error(self, error_message: str, query_input: Optional[Any] = None) -> AgentResponse: # Added query_input context
        """Handle errors that occur during processing."""
        print(f"❌ Error in {self.agent_name}: {error_message}")
        # Try to get a specific error message prompt, otherwise use a default
        error_template = self.prompts.get(
            "error_response", # Consistent key
            "Apologies, I encountered an internal error trying to process your request: '{error_message}'. Please try rephrasing or contact support."
        )
        # Add more context if available
        # context_str = f" Query context: {query_input}" if query_input else ""
        return AgentResponse(answer=error_template.format(error_message=error_message)) # Removed context_str for simplicity