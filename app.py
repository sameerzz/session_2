"""Simple local teaching example. Run: uvicorn app:app --port 8001"""
from fastapi import FastAPI, Header
from langchain_core.messages import HumanMessage, AIMessage

from shop_chain import chain

app = FastAPI()

# One conversation per login token, kept in this backend process.
chat_history = {}


@app.post("/chat")
def chat(user_input: dict, authorization: str = Header()):
    # Streamlit sends: Authorization: Bearer <shopping login token>
    # This is the token Streamlit received when you signed in.
    login_token = authorization.removeprefix("Bearer ")

    # For this demo, use the login token as the user's history ID.
    user_id = login_token
    if user_id not in chat_history:
        chat_history[user_id] = []

    history = chat_history[user_id]

    # Send the question, history, and login token to our chain.
    response = chain.invoke(
        {"query": user_input["query"], "history": history},
        config={"configurable": {"user_id": user_id, "login_token": login_token}},
    )

    # Save the question and answer for the next request.
    history.append(HumanMessage(content=user_input["query"]))
    history.append(AIMessage(content=response.content))

    return {"answer": response.content}
