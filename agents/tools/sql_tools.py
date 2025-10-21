# agents/tools/sql_tools.py
# --- PASTE YOUR PROVIDED CustomSQLDatabaseToolkit and related Tool classes HERE ---
# Make sure imports are correct (e.g., from langchain_core, langchain_community)
# Example Start:
import re
from typing import Any, Dict, List, Optional, Sequence, Type, Union
import datetime
import logging

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.engine import Result
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from langchain_core.tools.base import BaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.tools.sql_database.prompt import QUERY_CHECKER
from langchain.chains.llm import LLMChain

logger = logging.getLogger(__name__)

# --- BaseSQLDatabaseTool ---
class BaseSQLDatabaseTool(BaseModel):
    # ... (rest of BaseSQLDatabaseTool code from your text2sql_tools.py)
    db: SQLDatabase = Field(exclude=True)
    model_config = ConfigDict(arbitrary_types_allowed=True)

# --- QuerySQLDataBaseTool ---
class QuerySQLDataBaseToolInput(BaseModel):
    # ... (rest of QuerySQLDataBaseToolInput code from your text2sql_tools.py)
    query: str = Field(..., description="A detailed and correct SQL query.")

class QuerySQLDataBaseTool(BaseSQLDatabaseTool, BaseTool):
    # ... (rest of QuerySQLDataBaseTool code from your text2sql_tools.py)
    name: str = "sql_db_query"
    description: str = (
        "Execute a SQL query against the database and get back the result. "
        "Only SELECT statements are allowed."
    )
    args_schema: Type[BaseModel] = QuerySQLDataBaseToolInput

    def _is_dml_command(self, sql_query: str) -> bool:
        dml_pattern = r"^\s*(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER)\b"
        return bool(re.match(dml_pattern, sql_query.strip(), re.IGNORECASE))

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[str, Sequence[Dict[str, Any]], Result]:
        """Execute the query, return the results or an error message."""
        logger.debug(f"[DEBUG] sql_db_query executing query: >>>{query}<<<")

        if self._is_dml_command(query):
            return (
                "Error: Prohibited DML/DDL command detected. "
                "This tool can only execute SELECT statements."
            )
        else:
            # Use run_no_throw for safety
            result = self.db.run_no_throw(query)
            logger.debug(f"[DEBUG] sql_db_query result: {str(result)[:500]}...")
            # You might want to format the result slightly here or handle errors more explicitly
            if isinstance(result, str) and ("Error" in result or "error" in result):
                 print(f"SQL Execution Error reported by db.run_no_throw: {result}")
                 # Return the error string so the agent knows it failed
            return result

# --- InfoSQLDatabaseTool ---
class _InfoSQLDatabaseToolInput(BaseModel):
    # ... (rest of _InfoSQLDatabaseToolInput code from your text2sql_tools.py)
     table_names: str = Field(
        ...,
        description=(
            "A comma-separated list of the table names for which to return the schema. "
            "Example input: 'table1, table2, table3'"
        ),
    )

class InfoSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
    # ... (rest of InfoSQLDatabaseTool code from your text2sql_tools.py)
    name: str = "sql_db_schema"
    description: str = "Get the schema and sample rows for the specified SQL tables."
    args_schema: Type[BaseModel] = _InfoSQLDatabaseToolInput
    # metadata: Dict = Field(default_factory=dict) # Metadata might not be needed if loaded in agent

    def _run(
        self,
        table_names: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for tables in a comma-separated list."""
        # Use get_table_info_no_throw for safety
        return self.db.get_table_info_no_throw(
            [t.strip() for t in table_names.split(",")]
        )

# --- ListSQLDatabaseTool ---
class _ListSQLDataBaseToolInput(BaseModel):
     # Input is not really used by the underlying method, can simplify
     tool_input: str = Field("", description="An empty string. This tool lists tables.")


class ListSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
    # ... (rest of ListSQLDatabaseTool code from your text2sql_tools.py)
    name: str = "sql_db_list_tables"
    description: str = "Input is an empty string, output is a comma-separated list of tables in the database."
    args_schema: Type[BaseModel] = _ListSQLDataBaseToolInput
    # metadata: Dict = Field(default_factory=dict) # Agent handles metadata loading

    def _run(
        self,
        tool_input: str = "", # Default to empty string
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get a comma-separated list of table names."""
        # Directly return the list of usable table names
        return ", ".join(self.db.get_usable_table_names())


# --- QuerySQLCheckerTool ---
class QuerySQLCheckerToolInput(BaseModel):
    # ... (rest of QuerySQLCheckerToolInput code from your text2sql_tools.py)
    query: str = Field(..., description="A detailed SQL query to be checked.")

class QuerySQLCheckerTool(BaseSQLDatabaseTool, BaseTool):
    # ... (rest of QuerySQLCheckerTool code from your text2sql_tools.py, ensure LLMChain uses correct LLM)
    template: str = QUERY_CHECKER
    llm: BaseLanguageModel # Expect LLM to be passed during init
    llm_chain: LLMChain = Field(init=False)
    name: str = "sql_db_query_checker"
    description: str = (
        "Use this tool to double check if your query is syntactically correct "
        "and likely to succeed BEFORE executing it. Checks against the database dialect. "
        "Always use this tool before executing a query with sql_db_query!" # Emphasize importance
    )
    args_schema: Type[BaseModel] = QuerySQLCheckerToolInput

    @model_validator(mode="before")
    @classmethod
    def initialize_llm_chain(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the LLMChain for the tool."""
        if "llm_chain" not in values:
            if "llm" not in values:
                raise ValueError("LLM must be provided to QuerySQLCheckerTool")

            prompt = PromptTemplate(
                template=values.get("template", QUERY_CHECKER),
                input_variables=["dialect", "query"],
            )
            values["llm_chain"] = LLMChain(
                 llm=values["llm"], # Use the passed LLM
                 prompt=prompt
            )

        # Validate input variables
        if values["llm_chain"].prompt.input_variables != ["dialect", "query"]:
            raise ValueError(
                "LLM chain for QuerySQLCheckerTool must have input variables ['query', 'dialect']"
            )
        return values

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the LLM chain to check the query."""
        # Ensure the llm_chain is initialized
        if not hasattr(self, 'llm_chain'):
             # This might happen if validation runs after instantiation in some frameworks
             # Re-initialize here if necessary, though the validator should handle it
             raise RuntimeError("LLM Chain not initialized for QuerySQLCheckerTool")

        return self.llm_chain.invoke(
            input={"query": query, "dialect": self.db.dialect},
            config={"callbacks": run_manager.get_child() if run_manager else None},
        )['text'] # Assuming invoke returns a dict with 'text' key

    # Add async version if needed
    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
         """Use the LLM chain to check the query asynchronously."""
         result = await self.llm_chain.ainvoke(
             input={"query": query, "dialect": self.db.dialect},
             config={"callbacks": run_manager.get_child() if run_manager else None}
         )
         return result['text']


# --- CustomSQLDatabaseToolkit ---
class CustomSQLDatabaseToolkit(BaseToolkit):
    # ... (rest of CustomSQLDatabaseToolkit code from your text2sql_tools.py, ensure LLM passed correctly)
    db: SQLDatabase = Field(exclude=True)
    llm: BaseLanguageModel = Field(exclude=True) # Expect LLM during init
    # metadata: Dict = Field(exclude=True) # Metadata is loaded by agent now

    @property
    def dialect(self) -> str:
        """Return string representation of SQL dialect to use."""
        return self.db.dialect

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_tools(self) -> List[BaseTool]:
        """Get the tools in the toolkit."""
        # Instantiate tools, passing the LLM where needed
        list_sql_database_tool = ListSQLDatabaseTool(db=self.db)
        info_sql_database_tool = InfoSQLDatabaseTool(db=self.db)
        query_sql_database_tool = QuerySQLDataBaseTool(db=self.db)
        query_sql_checker_tool = QuerySQLCheckerTool(db=self.db, llm=self.llm) # Pass LLM here

        # Adjust descriptions if necessary
        info_sql_database_tool.description = (
            "Input to this tool is a comma-separated list of tables, output is the "
            "schema and sample rows for those tables. Use sql_db_list_tables first "
            "to get the names of the tables. Example Input: table1, table2"
        )
        query_sql_database_tool.description = (
            "Input is a detailed and correct SQL query. Executes the query and returns the result. "
            "If the query is incorrect, an error message is returned. "
            "ALWAYS use sql_db_query_checker first to validate the query before execution!"
        )

        return [
            query_sql_database_tool,
            info_sql_database_tool,
            list_sql_database_tool,
            query_sql_checker_tool,
        ]

    # get_context method might not be needed if schema is passed in prompt
    # def get_context(self) -> dict: ...