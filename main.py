from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import json
from typing import Dict, List, Optional
import uuid
import asyncio
from datetime import datetime

# Import functions from the existing code file
# Assuming the code you provided is in a file called "crawler_module.py"
from crawler import crawl_website, list_collections, query_chromadb

app = FastAPI(
    title="Web Crawler and ChromaDB API",
    description="API for crawling websites and querying the stored content using ChromaDB",
    version="1.0.0"
)

# In-memory storage for tracking crawl tasks
crawl_tasks: Dict[str, Dict] = {}


# Define request and response models
class CrawlRequest(BaseModel):
    url: HttpUrl
    pattern: str = "*"
    max_depth: int = 2
    collection_name: str = "web_content"


class CrawlResponse(BaseModel):
    task_id: str
    message: str
    status: str


class QueryRequest(BaseModel):
    collection_name: str
    query: str
    n_results: int = 5


class CrawlStatus(BaseModel):
    task_id: str
    url: str
    collection_name: str
    status: str
    start_time: str
    finish_time: Optional[str] = None
    pages_crawled: Optional[int] = None
    error: Optional[str] = None


# Background task for crawling
async def crawl_task(task_id: str, url: str, pattern: str, max_depth: int, collection_name: str):
    try:
        # Update task status to "in_progress"
        crawl_tasks[task_id]["status"] = "in_progress"
        print('crawl started')
        # Run the crawl function
        result = await crawl_website(url, pattern, max_depth, collection_name)
        print(f'completed extraction with {result}')
        # Extract page count from result message
        import re
        pages_match = re.search(r"Successfully crawled (\d+) pages", result)
        pages_crawled = int(pages_match.group(1)) if pages_match else None

        # Update task status to "completed"
        crawl_tasks[task_id].update({
            "status": "completed",
            "finish_time": datetime.now().isoformat(),
            "pages_crawled": pages_crawled
        })
    except Exception as e:
        # Update task status to "failed"
        crawl_tasks[task_id].update({
            "status": "failed",
            "finish_time": datetime.now().isoformat(),
            "error": str(e)
        })


@app.post("/crawl", response_model=CrawlResponse, tags=["Crawling"])
async def start_crawl(crawl_request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Start crawling a website and store the content in ChromaDB.

    The crawling process runs in the background and may take some time depending on the website size and max_depth.
    Returns a task_id that can be used to check the status of the crawl.
    """
    try:
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        print(crawl_request.json())
        # Store task information
        crawl_tasks[task_id] = {
            "url": str(crawl_request.url),
            "collection_name": crawl_request.collection_name,
            "status": "pending",
            "start_time": datetime.now().isoformat()
        }

        # Add crawling task to background tasks
        background_tasks.add_task(
            crawl_task,
            task_id,
            str(crawl_request.url),
            crawl_request.pattern,
            crawl_request.max_depth,
            crawl_request.collection_name
        )

        return {
            "task_id": task_id,
            "message": f"Crawling started for {crawl_request.url} with max depth {crawl_request.max_depth}. Results will be saved to collection '{crawl_request.collection_name}'.",
            "status": "pending"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start crawling: {str(e)}")


@app.get("/crawl/{task_id}", response_model=CrawlStatus, tags=["Crawling"])
async def get_crawl_status(task_id: str):
    """
    Get the status of a crawl task by its ID.
    """
    if task_id not in crawl_tasks:
        raise HTTPException(status_code=404, detail=f"Crawl task with ID {task_id} not found")

    task_info = crawl_tasks[task_id]
    return {
        "task_id": task_id,
        **task_info
    }


@app.get("/crawls", tags=["Crawling"])
async def list_crawl_tasks():
    """
    List all crawl tasks and their statuses.
    """
    return {
        "tasks": [
            {"task_id": task_id, **task_info}
            for task_id, task_info in crawl_tasks.items()
        ]
    }


@app.get("/collections", tags=["ChromaDB"])
async def get_collections():
    """
    List all available collections in ChromaDB.
    """
    try:
        collections_json = list_collections()
        collections_data = json.loads(collections_json)
        return collections_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@app.post("/query", tags=["ChromaDB"])
async def query_collection(query_request: QueryRequest):
    """
    Query a ChromaDB collection for relevant documents based on semantic similarity.
    """
    try:
        results_json = query_chromadb(
            query_request.collection_name,
            query_request.query,
            query_request.n_results
        )
        results_data = json.loads(results_json)

        # Check if there was an error in the query
        if "error" in results_data:
            raise HTTPException(status_code=400, detail=results_data["message"])

        return results_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query collection: {str(e)}")


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "name": "Web Crawler and ChromaDB API",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "This information"},
            {"path": "/crawl", "method": "POST", "description": "Start crawling a website"},
            {"path": "/crawl/{task_id}", "method": "GET", "description": "Get status of a specific crawl task"},
            {"path": "/crawls", "method": "GET", "description": "List all crawl tasks"},
            {"path": "/collections", "method": "GET", "description": "List all available collections"},
            {"path": "/query", "method": "POST", "description": "Query a collection"}
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)