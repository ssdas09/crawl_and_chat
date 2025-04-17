import json
import httpx
import asyncio
from phi.agent import Agent, AgentKnowledge
from phi.model.google import Gemini
from typing import Dict, Optional, List
import time

# API endpoint configuration
API_BASE_URL = "http://localhost:8000"  # Change this to your actual API host if different


# Create wrapper functions that use the API endpoints instead of direct function calls
async def api_crawl_website(url: str, pattern: str = '*', max_depth: int = 2,
                            collection_name: str = "web_content") -> str:
    """
    Initiates website crawling via the API endpoint and monitors the status.

    Args:
        url (str): The starting URL to begin crawling from. Should include http:// or https://.
        pattern (str, optional): A pattern to filter URLs. Only URLs containing this pattern will be crawled.
            Use '*' to crawl all pages. Default is '*'.
        max_depth (int, optional): The maximum depth to crawl from the starting URL. Default is 2.
        collection_name (str, optional): The name of the ChromaDB collection to store the results.
            Default is "web_content".

    Returns:
        str: A message about the crawl process and its completion status.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Start the crawl
        crawl_request = {
            "url": url,
            "pattern": pattern,
            "max_depth": max_depth,
            "collection_name": collection_name
        }

        try:
            # Initiate the crawl
            start_response = await client.post(f"{API_BASE_URL}/crawl", json=crawl_request)
            start_response.raise_for_status()

            start_data = start_response.json()
            task_id = start_data.get("task_id")

            if not task_id:
                return f"Failed to start crawling: No task ID returned from the API"

            # Return immediate response that crawling has started
            return (
                f"Crawling started for {url} with task ID: {task_id}.\n"
                f"The content will be saved to collection '{collection_name}'.\n"
                f"You can check the status using the task ID."
            )

        except httpx.HTTPError as e:
            return f"Failed to start crawling: {str(e)}"
        except Exception as e:
            return f"An error occurred: {str(e)}"


def sync_crawl_website(url: str, pattern: str = '*', max_depth: int = 2, collection_name: str = "web_content") -> str:
    """
    Initiates website crawling via the API endpoint (synchronous wrapper).

    Args:
        url (str): The starting URL to begin crawling from. Should include http:// or https://.
        pattern (str, optional): A pattern to filter URLs. Only URLs containing this pattern will be crawled.
            Use '*' to crawl all pages. Default is '*'.
        max_depth (int, optional): The maximum depth to crawl from the starting URL. Default is 2.
        collection_name (str, optional): The name of the ChromaDB collection to store the results.
            Default is "web_content".

    Returns:
        str: A message about the crawl process and its completion status.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(
        api_crawl_website(url=url, pattern=pattern, max_depth=max_depth, collection_name=collection_name))
    loop.close()
    return result


def check_crawl_status(task_id: str) -> str:
    """
    Checks the status of a crawl task using its ID.

    Args:
        task_id (str): The ID of the crawl task to check.

    Returns:
        str: Information about the crawl task status.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/crawl/{task_id}")
            response.raise_for_status()

            status_data = response.json()
            status = status_data.get("status", "unknown")

            if status == "completed":
                pages = status_data.get("pages_crawled", "unknown number of")
                return (
                    f"Crawl task {task_id} completed successfully.\n"
                    f"Crawled {pages} pages from {status_data.get('url')}.\n"
                    f"Content saved to collection '{status_data.get('collection_name')}'."
                )
            elif status == "failed":
                return f"Crawl task {task_id} failed: {status_data.get('error', 'Unknown error')}"
            else:
                return f"Crawl task {task_id} is {status}. Started at {status_data.get('start_time')}."

    except Exception as e:
        return f"Failed to check crawl status: {str(e)}"


def list_crawl_tasks() -> str:
    """
    Lists all crawl tasks and their statuses.

    Returns:
        str: Information about all crawl tasks.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/crawls")
            response.raise_for_status()

            tasks_data = response.json()
            if not tasks_data.get("tasks"):
                return "No crawl tasks found."

            tasks_info = []
            for task in tasks_data.get("tasks", []):
                task_info = (
                    f"Task ID: {task.get('task_id')}\n"
                    f"URL: {task.get('url')}\n"
                    f"Status: {task.get('status')}\n"
                    f"Collection: {task.get('collection_name')}\n"
                )
                if task.get("pages_crawled") is not None:
                    task_info += f"Pages crawled: {task.get('pages_crawled')}\n"

                tasks_info.append(task_info)

            return "Current crawl tasks:\n\n" + "\n".join(tasks_info)

    except Exception as e:
        return f"Failed to list crawl tasks: {str(e)}"


def list_collections() -> str:
    """
    Lists all available collections in ChromaDB via the API.

    Returns:
        str: Information about available collections.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/collections")
            response.raise_for_status()

            collections_data = response.json()
            collections = collections_data.get("collections", [])

            if not collections:
                return "No collections found. You need to crawl a website first."

            collection_info = []
            for collection in collections:
                collection_info.append(f"Collection name: {collection.get('name')}")

            return "Available collections:\n" + "\n".join(collection_info)

    except Exception as e:
        return f"Failed to list collections: {str(e)}"


def query_chromadb(collection_name: str, query: str, n_results: int = 5) -> str:
    """
    Queries a ChromaDB collection for relevant documents via the API.

    Args:
        collection_name (str): The name of the ChromaDB collection to query.
        query (str): The search query to find relevant content.
        n_results (int, optional): The number of results to return. Default is 5.

    Returns:
        str: Search results with documents and their metadata.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            query_request = {
                "collection_name": collection_name,
                "query": query,
                "n_results": n_results
            }

            response = client.post(f"{API_BASE_URL}/query", json=query_request)
            response.raise_for_status()

            results_data = response.json()

            if "error" in results_data:
                return f"Query error: {results_data.get('message')}"

            results = results_data.get("results", [])

            if not results:
                return f"No results found for '{query}' in collection '{collection_name}'."

            formatted_results = []

            for result in results:
                # Extract relevant information
                rank = result.get("rank", "N/A")
                score = result.get("relevance_score", 0)
                metadata = result.get("metadata", {})
                url = metadata.get("url", "Unknown URL")
                title = metadata.get("title", "Untitled")
                content = result.get("content_preview", "No content preview available")

                # Format the result
                formatted_result = (
                    f"Result #{rank} (Score: {score:.2f})\n"
                    f"Title: {title}\n"
                    f"URL: {url}\n\n"
                    f"Content: {content}\n"
                )
                formatted_results.append(formatted_result)

            return (
                    f"Query results for '{query}' in collection '{collection_name}':\n\n"
                    + "\n---\n".join(formatted_results)
            )

    except Exception as e:
        return f"Failed to query collection: {str(e)}"


# Create the agent with the API-based tools
agent = Agent(
    model=Gemini(id="gemini-2.0-flash"),
    tools=[
        sync_crawl_website,
        query_chromadb,
        list_collections,
        check_crawl_status,
        list_crawl_tasks
    ],
    description="You are a specialized webscraping agent that can extract, store, and analyze web content based on user request",
    instructions=[
        "You are a specialized web content assistant that can crawl websites, store content, and retrieve information.",
        "Help users through these main operations:",

        "1. WEBSITE CRAWLING:",
        "   - When a user wants to crawl a website, ask for these essential details if not provided:",
        "     * Starting URL (required): The website address to begin crawling from",
        "     * Pattern (optional): Keywords to filter which URLs to include (e.g., 'docs', 'blog', 'product')",
        "     * Crawl depth (optional, default=2): How many links to follow (1-3 recommended)",
        "     * Collection name (optional): Where to store the results (suggest domain name if user doesn't specify)",
        "   - After gathering details, use sync_crawl_website() to perform the crawl",
        "   - Explain that crawling happens asynchronously and provide the task ID to check status",
        "   - Suggest using check_crawl_status() to monitor progress",

        "2. COLLECTION AND TASK MANAGEMENT:",
        "   - Use list_collections() to show what content collections are available",
        "   - Use list_crawl_tasks() to show ongoing and completed crawl operations",
        "   - Use check_crawl_status() with a task ID to get detailed status of a specific crawl",
        "   - If no collections exist, suggest crawling a website first",
        "   - Help users organize their collections with meaningful names",

        "3. CONTENT RETRIEVAL:",
        "   - When a user asks questions about crawled content, use query_chromadb() to search",
        "   - Ask which collection to search if not specified",
        "   - Transform user questions into effective search queries",
        "   - Present search results in a readable format with source URLs",
        "   - Summarize the key information from retrieved documents",

        "Be conversational but efficient. Guide users through the workflow from crawling to querying.",
        "Proactively suggest next steps based on user needs without being overly verbose.",
        "If users provide incomplete information, ask clarifying questions rather than making assumptions."
    ],
    markdown=True,
    add_datetime_to_instructions=True,
    add_history_to_messages=True,
    # Number of historical responses to add to the messages.
    num_history_responses=10,
    # debug_mode=True,
)


def run_agent(message: str):
    return agent.run(message, stream=True)