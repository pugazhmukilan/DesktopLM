import logging
import concurrent.futures
from typing import Annotated

from langchain_core.tools import tool
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

logger = logging.getLogger("desktoplm.tools.web_search")
_CYAN = "\033[36m"
_RESET = "\033[0m"

def _fetch_page_content(url: str, max_chars: int = 1800) -> str:
    """Fetch URL and extract main text content efficiently."""
    try:
        # Use a generic User-Agent to avoid early blocks from basic scraping protection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Kill script, style, and navigation noise
        for useless in soup(["script", "style", "nav", "header", "footer", "aside"]):
            useless.extract()
            
        text = soup.get_text(separator=" ", strip=True)
        # Collapse multiple spaces
        text = " ".join(text.split())
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return f"[Failed to fetch content: {e}]"

@tool
def search_and_read_web(
    query: Annotated[str, "The search query to look up on DuckDuckGo."],
    max_results: Annotated[int, "Number of websites to load and read (1-15 recommended)."] = 10
) -> str:
    """Search the web and read the actual content of the top result pages. Use this to get live facts, documentation, or news."""
    try:
        raw_results = []
        with DDGS() as ddgs:
            # Get search results
            raw_results = list(ddgs.text(query, max_results=max_results))
            
        if not raw_results:
            return f"No results found for '{query}'."

        # Fetch contents concurrently for max efficiency
        formatted_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_results) as executor:
            future_to_raw = {
                executor.submit(_fetch_page_content, r.get("href", "")): r 
                for r in raw_results if r.get("href")
            }
            
            print(f"\n      {_CYAN}[_] Found {len(raw_results)} link(s), downloading content...{_RESET}", flush=True)
            for future in concurrent.futures.as_completed(future_to_raw):
                r = future_to_raw[future]
                content = future.result()
                title = r.get("title", "Unknown Title")
                url = r.get("href", "")
                snippet = r.get("body", "")
                
                print(f"      {_CYAN}[-] Parsed: {title[:40]}...{_RESET}", flush=True)
                
                block = f"SOURCE TITLE: {title}\nURL: {url}\nSEARCH SNIPPET: {snippet}\nFULL CONTENT STRIPPED:\n{content}\n"
                formatted_results.append(block)

        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Web search failed: {e}"
