"""Run: streamlit run streamlit_chain_app.py --server.port 8503"""
import httpx
import streamlit as st

from session_tools import sign_in

CHAT_API_URL = "https://hopscotch-chat-chain.vercel.app"

st.title("Hopscotch Chat")

# Save this browser session's login.
if "login" not in st.session_state:
    st.session_state.login = None

# Keep messages for display only; they are not sent to the chat API.
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.session_state.login is None:
    email = st.text_input("Email")
    if st.button("Sign in"):
        st.session_state.login = sign_in(email)
        st.rerun()
else:
    st.write("Signed in as:", st.session_state.login["customer"]["email"])

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ask a question")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)
        # The shopping API gave us this token at sign-in.
        login_token = st.session_state.login["access_token"]

        # Send only the new question, not the display transcript.
        response = httpx.post(
            f"{CHAT_API_URL}/chat",
            headers={"Authorization": f"Bearer {login_token}"},
            json={"query": question},
            timeout=180,
        )
        response.raise_for_status()
        answer = response.json()["answer"]
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)
