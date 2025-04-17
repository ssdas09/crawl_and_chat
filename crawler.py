import asyncio
import os
from urllib.parse import urljoin
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import chromadb
import datetime
import hashlib
import json
import asyncio

# Initialize ChromaDB client



async def save_result(result, index, chroma_client, collection_name="web_content"):
    """Process and save an individual result to ChromaDB"""
    # Extract content
    try:
        if result.markdown is not None:
            content = result.markdown.fit_markdown
        else:
            content = "No markdown content available"
    except Exception as e:
        content = f"Error extracting markdown: {str(e)}\nFalling back to plain text."
        # Try to get any available content as fallback
        if hasattr(result, 'content') and result.content is not None:
            try:
                content += "\n\n" + result.content.get_text()
            except:
                pass

    # Save to ChromaDB
    try:
        # Get or create collection
        collection = chroma_client.get_or_create_collection(name=collection_name)

        # Prepare metadata
        metadata = {
            "url": result.url,
            "depth": result.metadata.get('depth', 0),
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Add title to metadata if available
        if hasattr(result, 'content') and hasattr(result.content, 'get_title'):
            metadata["title"] = result.content.get_title()

        # Generate a document ID based on URL
        doc_id = f"doc_{index:03d}_{hashlib.md5(result.url.encode()).hexdigest()[:12]}"

        # Add document to collection
        collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        print(f"Added content from {result.url} to ChromaDB collection '{collection_name}'")
    except Exception as e:
        print(f"Error saving to ChromaDB: {str(e)}")


async def crawl_website(url: str, pattern: str = '*', max_depth: int = 2, collection_name: str = "web_content") -> str:
    # Initialize ChromaDB client
    """
       Crawls a website and stores the content in a ChromaDB collection for later retrieval.

       This function performs a breadth-first search crawl of a website, starting from the provided URL.
       It extracts content from each page, converts it to markdown format, and stores it in ChromaDB
       with appropriate metadata for vector search and retrieval.

       Args:
           url (str): The starting URL to begin crawling from. Should include http:// or https://.
           pattern (str, optional): A pattern to filter URLs. Only URLs containing this pattern will be crawled.
               Use '*' to crawl all pages. Default is '*'.
           max_depth (int, optional): The maximum depth to crawl from the starting URL. Default is 2.
           collection_name (str, optional): The name of the ChromaDB collection to store the results.
               Default is "web_content".

       Returns:
           str: A confirmation message indicating the number of pages crawled and where they were saved.

       Example:
           # >>> result = await crawl_website("https://docs.example.com", pattern="guide", max_depth=3)
           # >>> print(result)
           "Successfully crawled 42 pages and saved to ChromaDB collection 'web_content'"

       Note:
           This function requires the ChromaDB client to be properly configured and accessible.
           The crawled content is stored only in ChromaDB and not saved as files to the filesystem.
    """
    chroma_client = chromadb.PersistentClient(path='./chroma')

    # Configure URL filters to focus on documentation
    url_filter = URLPatternFilter(patterns=[f"*{pattern}*"])

    # Configure the crawler
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
            filter_chain=FilterChain([url_filter])
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.6),
            options={"ignore_links": True}
        ),
        stream=True  # Enable streaming mode
    )

    # Run the crawler in streaming mode
    async with AsyncWebCrawler() as crawler:
        # Get the async iterator
        results_iterator = await crawler.arun(f"{url}", config=config)

        # Process each result as it becomes available
        counter = 0
        async for result in results_iterator:
            counter += 1
            await save_result(result, counter, chroma_client, collection_name)

        print(f"Crawled and processed {counter} pages in total")
        print(f"Documentation saved to ChromaDB collection '{collection_name}'")

        return f"Successfully crawled {counter} pages and saved to ChromaDB collection '{collection_name}'"


def list_collections() -> dict:
    """
    List all available collections in ChromaDB.

    Returns:
        str: A JSON string containing the list of available collections.
    """
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient('./chroma')

        # Get all collections
        collections = chroma_client.list_collections()
        print(collections)

        # Extract collection names and sizes
        collection_info = []
        for collection in collections:


            collection_info.append({
                "name": collection,
                        })
        print(collection_info)
        return json.dumps({
            "collections": collection_info
        }, indent=2)

    except Exception as e:
        print(e)
        return json.dumps({
            "error": str(e),
            "message": "Failed to list collections."
        }, indent=2)


def query_chromadb(collection_name: str, query: str, n_results: int = 5) -> str:
    """
    Query a ChromaDB collection for relevant documents based on semantic similarity.

    This function performs a semantic search in the specified ChromaDB collection,
    retrieving documents that are most relevant to the provided query.

    Args:
        collection_name (str): The name of the ChromaDB collection to query.
        query (str): The search query to find relevant content.
        n_results (int, optional): The number of results to return. Default is 5.

    Returns:
        str: A JSON string containing the search results with documents and their metadata.
    """
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient('./chroma')

        # Get the collection
        collection = chroma_client.get_collection(name=collection_name)

        # Query the collection
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )

        # Process results
        response_data = []
        if results and "documents" in results and results["documents"]:
            documents = results["documents"][0]  # First query results
            metadatas = results["metadatas"][0]  # Corresponding metadata
            distances = results["distances"][0]  # Relevance scores (lower is better)

            for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
                # Truncate document content if too long
                doc_preview = doc[:300] + "..." if len(doc) > 300 else doc

                # Create result entry
                result_entry = {
                    "rank": i + 1,
                    "relevance_score": 1 - dist,  # Convert distance to similarity score
                    "metadata": meta,
                    "content_preview": doc_preview,
                    "full_content": doc
                }
                response_data.append(result_entry)

        # Return formatted results
        if response_data:
            return json.dumps({
                "collection": collection_name,
                "query": query,
                "num_results": len(response_data),
                "results": response_data
            }, indent=2)
        else:
            return json.dumps({
                "collection": collection_name,
                "query": query,
                "num_results": 0,
                "message": "No results found for this query in the collection."
            }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": f"Failed to query collection '{collection_name}'. Make sure the collection exists and contains documents."
        }, indent=2)
