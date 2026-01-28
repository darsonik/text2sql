from langchain.agents import create_agent
from text2sql.models.llm_models import langchain_llm
from text2sql.agents.agent_tools import sql_query_tool
from pydantic import BaseModel
from langchain.agents.structured_output import ToolStrategy
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "3"}}

class SQLAgentResponseFormat(BaseModel):
    user_query: str
    answer: str

agent = create_agent(
    model=langchain_llm,
    tools=[sql_query_tool],
    response_format = ToolStrategy(SQLAgentResponseFormat),
    checkpointer=checkpointer,
    system_prompt=" You are an expert SQL agent that can help users query a SQL database. "
                  "Use the provided tool to answer user questions. The tool allows you to query the database directly. " \
                  "The tools take a single input which is the user's query string in natural language, and return the answer from the database.",
                  )

if __name__ == "__main__":
    response = agent.invoke({"messages": [{"role": "user", "content": "What is the average income in cities with population over 2.5 million?"}]}, 
                            config=config)
    print(response["structured_response"])