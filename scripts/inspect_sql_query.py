import inspect
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine
src = inspect.getsource(SQLTableRetrieverQueryEngine.__init__)
print('\n'.join(src.split('\n')[:400]))
