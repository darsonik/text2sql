from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from text2sql.agents.agent_tools import sql_query_tool
from text2sql.models.llm_models import langchain_llm

checkpointer = InMemorySaver()

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "5"}}

system_prompt = (
    "You are an expert analyst that can help users by providing answers from database. "
    "Use the provided tool to answer user questions. The tool allows you to "
    "query the database directly. "
    "The tools take a single input which is the user's query string in natural language, and return the answer from the database."
)

agent = create_agent(
    model=langchain_llm,
    tools=[sql_query_tool],
    checkpointer=checkpointer,
    system_prompt=system_prompt,
)

if __name__ == "__main__":
    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is the average income in cities with population over 1.5 million?",
                }
            ]
        },
        config=config,
    )
    for message in response["messages"]:
        message.pretty_print()
