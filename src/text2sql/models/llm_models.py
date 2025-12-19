# For Fireworks AI (like your example)
from llama_index.llms.fireworks import Fireworks
from langchain_fireworks import ChatFireworks

import os
from dotenv import load_dotenv
load_dotenv()

llama_index_llm = Fireworks(model=os.getenv("FIREWORKS_MODEL_LLAMAINDEX"), 
                         api_key=os.getenv("FIREWORKS_API_KEY"),
                         api_base=os.getenv("FIREWORKS_API_BASE"))
# stream = llama_index_llm.complete("Tell me a joke about programmers.")
# print(stream.text)

llama_index_embed_model = Fireworks(model=os.getenv("FIREWORKS_EMBEDDING_MODEL"),
                                   api_key=os.getenv("FIREWORKS_API_KEY"),
                                   api_base=os.getenv("FIREWORKS_API_BASE"))

langchain_llm = ChatFireworks(
    base_url=os.getenv("FIREWORKS_API_BASE"),
    api_key=os.getenv("FIREWORKS_API_KEY"),
    model=os.getenv("FIREWORKS_MODEL_LANGCHAIN"),
)

# response = langchain_llm.invoke(["Tell me a joke about computers."])
# print(response.content)