from llama_index.core.query_engine import NLSQLTableQueryEngine
from text2sql.database.toy_data import engine
from text2sql.database.table_schemas import city_stats_text, average_income_text

from llama_index.core.indices.struct_store.sql_query import (
    SQLTableRetrieverQueryEngine,
)
from llama_index.core.objects import (
    SQLTableNodeMapping,
    ObjectIndex,
    SQLTableSchema,
)
from llama_index.core import VectorStoreIndex
# from llama_index.core.embeddings.loading

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

def user_query_with_retrieval(sql_database, llm, embed_model, query_str: str):
    """Run a query against the provided SQL database and LLM with retrieval.

    If we don't know ahead of time which table we would like to use, 
    and the total size of the table schema overflows your context window size, 
    we store the table schema in an index so that during query time we can retrieve the right schema.
    """
    from llama_index.core import Settings
    
    # CRITICAL: Set global settings to prevent OpenAI fallback
    Settings.embed_model = embed_model  # Your FireworksEmbedding instance
    Settings.llm = llm  # Also good practice
    table_node_mapping = SQLTableNodeMapping(sql_database=sql_database)

    table_schema_objs = [
        (SQLTableSchema(table_name="city_stats", context_str=city_stats_text)),
        (SQLTableSchema(table_name="average_income", context_str=average_income_text)),
    ]
    from llama_index.core.base.embeddings.base import BaseEmbedding

    # print("Embed model:", embed_model)
    print("Is BaseEmbedding?", isinstance(embed_model, BaseEmbedding))

    obj_index = ObjectIndex.from_objects(
        objects = table_schema_objs,
        object_mapping=table_node_mapping,
        index_cls = VectorStoreIndex,
        embed_model=embed_model,
    )

    query_engine = SQLTableRetrieverQueryEngine(sql_database=sql_database,
                                                table_retriever=obj_index.as_retriever(similarity_top_k=1),
                                                llm=llm,
                                                )
    
    return query_engine.query(query_str)


if __name__ == "__main__":
    from llama_index.core import SQLDatabase
    from text2sql.models.llm_models import llama_index_llm, fireworks_embed_model
    sql_database = SQLDatabase(engine, include_tables=["average_income","city_stats"])
    basic_response = user_query_basic(sql_database=sql_database, 
                          llm=llama_index_llm, 
                          embed_model=fireworks_embed_model,
                          tables=["average_income","city_stats"], 
                          query_str="What is the average income in cities with population over 1 million?")
    print(f"Response from basic query: {basic_response}")

    response_with_retrieval = user_query_with_retrieval(sql_database=sql_database,
                                                        llm=llama_index_llm,
                                                        embed_model=fireworks_embed_model,
                                                        query_str="Create a report of average income for cities with population over 1 million.")
    print(f"Response from query with retrieval: {response_with_retrieval}")
