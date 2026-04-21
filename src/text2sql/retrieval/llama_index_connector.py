from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.indices.struct_store.sql_query import (
    SQLTableRetrieverQueryEngine,
)
from llama_index.core.objects import (
    ObjectIndex,
    SQLTableNodeMapping,
    SQLTableSchema,
)

from text2sql.database.table_schemas import average_income_text, city_stats_text
from text2sql.database.toy_data import engine

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

    def user_query_with_retrieval(self, query_str: str):
        """Run a query against the SQL database and LLM with retrieval.

        If we don't know ahead of time which table we would like to use,
        and the total size of the table schema overflows your context window size,
        we store the table schema in an index so that during query time we can retrieve the right schema.

        Args:
            query_str: Natural language query string, this is not an SQL Query

        Returns:
            Query response from the LLM with retrieval
        """
        # CRITICAL: Set global settings to prevent OpenAI fallback
        Settings.embed_model = self.embed_model  # Your FireworksEmbedding instance
        Settings.llm = self.llm  # Also good practice
        table_node_mapping = SQLTableNodeMapping(sql_database=self.sql_database)

        table_schema_objs = [
            SQLTableSchema(table_name="city_stats", context_str=city_stats_text),
            SQLTableSchema(table_name="average_income", context_str=average_income_text),
        ]

        obj_index = ObjectIndex.from_objects(
            objects=table_schema_objs,
            object_mapping=table_node_mapping,
            index_cls=VectorStoreIndex,
            embed_model=self.embed_model,
        )

        query_engine = SQLTableRetrieverQueryEngine(
            sql_database=self.sql_database,
            table_retriever=obj_index.as_retriever(similarity_top_k=1),
            llm=self.llm,
        )

        return query_engine.query(query_str)

if __name__ == "__main__":
    from llama_index.core import SQLDatabase
    from text2sql.models.llm_models import llama_index_llm, fireworks_embed_model

    sql_database = SQLDatabase(engine, include_tables=["average_income", "city_stats"])

    # Create connector instance
    connector = LlamaIndexConnector(
        sql_database=sql_database,
        llm=llama_index_llm,
        embed_model=fireworks_embed_model,
    )

    # Query with retrieval
    response_with_retrieval = connector.user_query_with_retrieval(
        query_str="Create a report of average income for cities with population over 1 million."
    )
    print(f"Response from query with retrieval: {response_with_retrieval}")
