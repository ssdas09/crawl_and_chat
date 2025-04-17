import streamlit as st
from agent import agent
import uuid

# Initialize the assistant

# Initialize chat session state
if "chats" not in st.session_state:
    st.session_state.chats = {}  # {session_id: [{"role": "...", "content": "..."}]}
if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())[:8]
    st.session_state.current_chat_id = new_id
    st.session_state.chats[new_id] = []

# Sidebar section for managing chats
st.sidebar.title("💬 Your Chats")
new_chat_btn = st.sidebar.button("➕ New Chat")

if new_chat_btn:
    new_id = str(uuid.uuid4())[:8]
    st.session_state.current_chat_id = new_id
    st.session_state.chats[new_id] = []

# Show all chat sessions in sidebar
for chat_id in st.session_state.chats.keys():
    label = f"Chat {chat_id}"
    if st.sidebar.button(label):
        st.session_state.current_chat_id = chat_id

# Display chat messages
st.title("🧠 Chat with Phidata Agent")

chat_id = st.session_state.current_chat_id
messages = st.session_state.chats[chat_id]

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input box
user_input = st.chat_input("Ask something...")

if user_input:
    # Show user message
    st.session_state.chats[chat_id].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get assistant response
    with st.chat_message("assistant"):
        response = agent.run(user_input).content
        st.markdown(response)
        st.session_state.chats[chat_id].append({"role": "assistant", "content": response})
