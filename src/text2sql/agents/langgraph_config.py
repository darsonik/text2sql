from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from text2sql.agents.agent_tools import sql_query_tool
from text2sql.models.llm_models import langchain_llm

checkpointer = InMemorySaver()

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "3"}}

system_prompt = (
    "You are an expert SQL agent that can help users query a SQL database. "
    "Use the provided tool to answer user questions. The tool allows you to "
    "query the database directly. "
)

agent = create_react_agent(
    model=langchain_llm,
    tools=[sql_query_tool],
    checkpointer=checkpointer,
    prompt=system_prompt,
)

if __name__ == "__main__":
    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is the average income in cities with population over 2.5 million?",
                }
            ]
        },
        config=config,
    )
    for message in response["messages"]:
        message.pretty_print()
