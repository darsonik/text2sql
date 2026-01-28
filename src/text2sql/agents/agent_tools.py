from text2sql.retrieval.llama_index_connector import LlamaIndexConnector
from llama_index.core import SQLDatabase
from text2sql.models.llm_models import llama_index_llm, fireworks_embed_model
from text2sql.database.toy_data import engine
from langchain.tools import tool

sql_database = SQLDatabase(engine, include_tables=["average_income","city_stats"])

# Create connector instance
connector = LlamaIndexConnector(
    sql_database=sql_database,
    llm=llama_index_llm,
    embed_model=fireworks_embed_model
)

# Define tools
@tool
def sql_query_tool(user_query_str: str) -> str:
    """Use this tool to answer questions from querying the SQL database.
     Args:
         user_query_str (str): The user's query string.
     
     Returns:
         str: The answer from the SQL database.
     """
    return connector.user_query_with_retrieval(user_query_str)