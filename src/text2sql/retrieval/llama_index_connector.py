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


class LlamaIndexConnector:
    """Connector for LlamaIndex-based SQL retrieval and querying.
    
    Provides methods to query SQL databases using natural language
    with LlamaIndex and LLM integration.
    """

    def __init__(self, sql_database, llm, embed_model):
        """Initialize the connector with database and model instances.
        
        Args:
            sql_database: SQLDatabase instance
            llm: Language model instance
            embed_model: Embedding model instance
        """
        self.sql_database = sql_database
        self.llm = llm
        self.embed_model = embed_model

    def user_query_basic(self, tables: list, query_str: str):
        """Run a query against the SQL database and LLM.

        This query function should be used in any case where you can specify the tables you want to query over beforehand, 
        or the total size of all the table schema plus the rest of the prompt fits your context window.
        
        Args:
            tables: List of table names to query over
            query_str: Natural language query string
            
        Returns:
            Query response from the LLM
        """
        if NLSQLTableQueryEngine is None:
            raise RuntimeError("llama_index is not available. Install `llama-index` to use `user_query_basic`.")

        query_engine = NLSQLTableQueryEngine(
            sql_database=self.sql_database, 
            tables=tables, 
            llm=self.llm,
            embed_model=self.embed_model
        )
        return query_engine.query(query_str)

    def user_query_with_retrieval(self, query_str: str):
        """Run a query against the SQL database and LLM with retrieval.

        If we don't know ahead of time which table we would like to use, 
        and the total size of the table schema overflows your context window size, 
        we store the table schema in an index so that during query time we can retrieve the right schema.
        
        Args:
            query_str: Natural language query string
            
        Returns:
            Query response from the LLM with retrieval
        """
        from llama_index.core import Settings
        
        # CRITICAL: Set global settings to prevent OpenAI fallback
        Settings.embed_model = self.embed_model  # Your FireworksEmbedding instance
        Settings.llm = self.llm  # Also good practice
        table_node_mapping = SQLTableNodeMapping(sql_database=self.sql_database)

        table_schema_objs = [
            (SQLTableSchema(table_name="city_stats", context_str=city_stats_text)),
            (SQLTableSchema(table_name="average_income", context_str=average_income_text)),
        ]
        from llama_index.core.base.embeddings.base import BaseEmbedding

        # print("Embed model:", self.embed_model)
        print("Is BaseEmbedding?", isinstance(self.embed_model, BaseEmbedding))

        obj_index = ObjectIndex.from_objects(
            objects = table_schema_objs,
            object_mapping=table_node_mapping,
            index_cls = VectorStoreIndex,
            embed_model=self.embed_model,
        )

        query_engine = SQLTableRetrieverQueryEngine(sql_database=self.sql_database,
                                                    table_retriever=obj_index.as_retriever(similarity_top_k=1),
                                                    llm=self.llm,
                                                    )
        
        return query_engine.query(query_str)

    def build_index(self, docs):
        """Build an index from a list of documents.
        Not implemented yet.
        """
        raise NotImplementedError

    def query(self, query_str):
        """Query the index with a string.
        Not implemented yet.
        """
        raise NotImplementedError



# Legacy function wrappers for backward compatibility
def user_query_basic(sql_database, llm, embed_model, tables : list, query_str: str):
    """Run a query against the provided SQL database and LLM.

    This query function should be used in any case where you can specify the tables you want to query over beforehand, 
    or the total size of all the table schema plus the rest of the prompt fits your context window.
    
    Deprecated: Use LlamaIndexConnector.user_query_basic() instead.
    """
    connector = LlamaIndexConnector(sql_database, llm, embed_model)
    return connector.user_query_basic(tables, query_str)

def user_query_with_retrieval(sql_database, llm, embed_model, query_str: str):
    """Run a query against the provided SQL database and LLM with retrieval.

    If we don't know ahead of time which table we would like to use, 
    and the total size of the table schema overflows your context window size, 
    we store the table schema in an index so that during query time we can retrieve the right schema.
    
    Deprecated: Use LlamaIndexConnector.user_query_with_retrieval() instead.
    """
    connector = LlamaIndexConnector(sql_database, llm, embed_model)
    return connector.user_query_with_retrieval(query_str)



if __name__ == "__main__":
    from llama_index.core import SQLDatabase
    from text2sql.models.llm_models import llama_index_llm, fireworks_embed_model
    sql_database = SQLDatabase(engine, include_tables=["average_income","city_stats"])
    
    # Create connector instance
    connector = LlamaIndexConnector(
        sql_database=sql_database,
        llm=llama_index_llm,
        embed_model=fireworks_embed_model
    )
    
    # Basic query
    basic_response = connector.user_query_basic(
        tables=["average_income","city_stats"], 
        query_str="What is the average income in cities with population over 1 million?"
    )
    print(f"Response from basic query: {basic_response}")

    # Query with retrieval
    response_with_retrieval = connector.user_query_with_retrieval(
        query_str="Create a report of average income for cities with population over 1 million."
    )
    print(f"Response from query with retrieval: {response_with_retrieval}")
