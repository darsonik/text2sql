from llama_index.core.query_engine import NLSQLTableQueryEngine
from text2sql.database.toy_data import engine

def user_query_basic(sql_database, llm, embed_model, tables : list, query_str: str):
    """Run a query against the provided SQL database and LLM.

    This query function should be used in any case where you can specify the tables you want to query over beforehand, 
    or the total size of all the table schema plus the rest of the prompt fits your context window.
    """
    if NLSQLTableQueryEngine is None:
        raise RuntimeError("llama_index is not available. Install `llama-index` to use `user_query`.")

    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database, 
        tables=tables, 
        llm=llm,
        embed_model=embed_model
    )
    return query_engine.query(query_str)


if __name__ == "__main__":
    from llama_index.core import SQLDatabase
    from text2sql.models.llm_models import llama_index_llm, llama_index_embed_model
    sql_database = SQLDatabase(engine, include_tables=["average_income","city_stats"])
    response = user_query_basic(sql_database=sql_database, 
                          llm=llama_index_llm, 
                          embed_model=llama_index_embed_model,
                          tables=["average_income","city_stats"], 
                          query_str="What is the average income in cities with population over 1 million?")
    print(response)