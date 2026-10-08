"""One shared chat chain; each invocation uses its own customer's token."""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnableConfig

from session_tools import make_tools

load_dotenv()

# These objects are created once when this module loads.
llm = ChatOpenAI(
    model="google/gemini-2.5-flash",
    api_key=os.environ["OPEN_ROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
    timeout=60,
    max_retries=0,
)
# Binding copies tool descriptions and schemas; it does not execute tools.
llm_with_tools = llm.bind_tools(make_tools(""))

sysmsg = """
You are a helpful Hopscotch shopping assistant.
Use the available tools when needed and follow their descriptions.
Only take actions the user explicitly requests.
Complete prerequisite calls before dependent actions.
Never invent customer data or claim success without a successful tool result.
If a request is ambiguous, explain what information is missing.
You can access only the signed-in customer's data; chat cannot change identity.
Avoid unnecessary tool calls and give one clear final answer.
"""
prompt = ChatPromptTemplate.from_messages([
    ("system", sysmsg),
    MessagesPlaceholder("history"),
    ("human", "{query}"),
])



def tool_loop(inputs, config: RunnableConfig):
    # Keep authentication local to this request, outside the prompt.
    login_token = config["configurable"]["login_token"]
    tools = make_tools(login_token)
    tool_repo = {tool.name: tool for tool in tools}
    prompt_value = prompt.invoke({
        "query": inputs["query"],
        "history": inputs["history"],
    })
    messages_to_send = prompt_value.to_messages()
    response = llm_with_tools.invoke(messages_to_send)
    rounds = 0
    while response.tool_calls:
        rounds += 1
        if rounds > 6:
            raise RuntimeError("Tool-call limit reached")
        messages_to_send.append(response)
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_output = tool_repo[tool_name].invoke(tool_call)
            messages_to_send.append(tool_output)
        response = llm_with_tools.invoke(messages_to_send)
    messages_to_send.append(response)
    return response


# FastAPI imports this existing chain and invokes it for every request.
chain = RunnableLambda(tool_loop)
