# Crawl and Chat: AI-Powered Web Content Interaction 🕷️🤖💬

This project provides a system to crawl websites, store their content in a ChromaDB vector database, and interact with that content using an AI agent through a chat interface.

It combines:
*   **Web Crawling:** Using `crawl4ai` to efficiently scrape websites.
*   **Vector Storage:** Using `ChromaDB` for persistent semantic storage and retrieval.
*   **API Layer:** A `FastAPI` backend to manage crawling tasks and querying.
*   **AI Agent:** A `Phidata` agent powered by Google `Gemini` to understand natural language commands and interact with the API.
*   **Chat UI:** A `Streamlit` application for easy user interaction with the agent.

## Features ✨

*   **Asynchronous Web Crawling:** Start crawling jobs via API, running in the background.
*   **Configurable Crawling:** Specify start URL, URL patterns to include, and maximum crawl depth.
*   **Content Storage:** Automatically extracts, cleans (markdown conversion), and stores content in ChromaDB collections.
*   **Task Management:** Check the status of ongoing or completed crawl tasks.
*   **Collection Management:** List available ChromaDB collections.
*   **Semantic Search:** Query stored content using natural language through the AI agent.
*   **AI-Powered Interaction:** Use the Phidata agent to crawl sites, check status, list collections, and ask questions about the content.
*   **Simple Chat Interface:** Interact with the agent via a user-friendly Streamlit web app.

## Architecture 🏗️

1.  **Streamlit UI (`streamlit_app.py`):** Provides the chat interface for the user.
2.  **Phidata Agent (`agent.py`):** Receives user input from Streamlit, interprets the command, and decides which tool (API wrapper function) to use. Uses Google Gemini for language understanding and reasoning.
3.  **FastAPI Backend (`main.py`):** Exposes endpoints for:
    *   Starting crawl tasks (`/crawl`)
    *   Checking crawl task status (`/crawl/{task_id}`)
    *   Listing all tasks (`/crawls`)
    *   Listing ChromaDB collections (`/collections`)
    *   Querying a collection (`/query`)
4.  **Crawler Logic (`crawler.py`):** Contains the core functions using `crawl4ai` to perform the crawl and `chromadb` to interact with the database (saving content, listing collections, executing queries).
5.  **ChromaDB (`./chroma` directory):** Persistent vector database storing the crawled website content and metadata.

```mermaid
graph LR
    User --> StreamlitUI[Streamlit UI (streamlit_app.py)];
    StreamlitUI <--> Agent[Phidata Agent (agent.py)];
    Agent -- API Calls --> FastAPI[FastAPI Backend (main.py)];
    FastAPI -- Crawl Logic --> Crawler[Crawler Logic (crawler.py)];
    FastAPI -- DB Operations --> Crawler;
    Crawler -- Save/Query --> ChromaDB[(ChromaDB ./chroma)];
```

## Prerequisites 🛠️

- Python 3.8+
- Pip (Python package installer)
- Google Gemini API Key:
  - Obtain an API key from Google AI Studio.
  - Set it as an environment variable:
    ```bash
    export GOOGLE_API_KEY='YOUR_API_KEY'
    ```

## Setup & Installation ⚙️

Clone the repository:
```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install dependencies:
```bash
# Example: Create requirements.txt if needed
# pip freeze > requirements.txt
pip install -r requirements.txt
# Or install manually:
# pip install fastapi uvicorn pydantic httpx phi-llm[google] crawl4ai chromadb-client streamlit lxml beautifulsoup4
```

Note: Ensure you have compatible versions. Check the documentation for phi-llm, crawl4ai, and chromadb-client if you encounter issues.

Set the GOOGLE_API_KEY environment variable (as shown in Prerequisites).

## Running the Application ▶️

You need to run two components separately: the FastAPI backend and the Streamlit UI.

Start the FastAPI Backend:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000. You can access the interactive API documentation at http://localhost:8000/docs.

Start the Streamlit Chat UI:
```bash
streamlit run streamlit_app.py
```

Streamlit will typically open the chat interface automatically in your web browser (usually at http://localhost:8501).

## Usage Example 🚀

Open the Streamlit App in your browser.

Start a Crawl:

User: Crawl https://docs.phidata.com/ with pattern /concepts/ and save it to a collection named phidata_concepts

Agent: (Calls sync_crawl_website) "Crawling started for https://docs.phidata.com/... with task ID: <task_id>. The content will be saved to collection 'phidata_concepts'. You can check the status using the task ID."

Check Status:

User: Check status for task <task_id>

Agent: (Calls check_crawl_status) "Crawl task <task_id> is in_progress..." (or completed/failed)

List Collections:

User: What collections are available?

Agent: (Calls list_collections) "Available collections:\nCollection name: phidata_concepts\n..."

Query Content:

User: Summarize what agents are in the phidata_concepts collection

Agent: (Calls query_chromadb) "Query results for 'what agents are' in collection 'phidata_concepts':\n\nResult #1 (Score: ...)\nTitle: Agents\nURL: https://docs.phidata.com/concepts/agents\n\nContent: Phidata Agents are AI assistants..."

## File Structure 📁
```
.
├── main.py           # FastAPI application defining API endpoints
├── agent.py          # Phidata agent logic, tools (API wrappers), instructions
├── crawler.py        # Core crawling logic (crawl4ai) and ChromaDB interaction
├── streamlit_app.py  # Streamlit chat UI application
├── README.md         # This file
└── chroma/           # Directory where ChromaDB stores its persistent data (created automatically)
# (Optional: requirements.txt) # Python dependencies
```

## Key Technologies Used 📚

- FastAPI: Web framework for building APIs.
- Uvicorn: ASGI server for running FastAPI.
- Phidata: Framework for building AI agents.
- Google Gemini: LLM used by the Phidata agent.
- crawl4ai: Library for asynchronous web crawling and content extraction.
- ChromaDB: Open-source vector database.
- Streamlit: Framework for building interactive web applications (the chat UI).
- Pydantic: Data validation and settings management.
- httpx: Asynchronous HTTP client used by the agent to call the API.
