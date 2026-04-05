import json
import logging
import os
from typing import Any

from LLMS.local_llm import LocalLLM
from LLMS.provider import LLMProvider
from MemoryManager.Database.SQLmemory import SQLMemoryStore
from MemoryManager.Database.nosqlmemory import NoSQLMemoryStore
from MemoryManager.Database.vectormemeorystore import VectorMemoryStore

logger = logging.getLogger("desktoplm.memory")
_CYAN = "\033[36m"
_RESET = "\033[0m"

# Categories routed to SQL (time-bound / structured items)
SQL_SCHEDULE_CATEGORIES = frozenset(
    {"constraint", "reminder", "todo", "commitment"}
)
# Categories routed to document store
MONGO_PREFERENCE_CATEGORIES = frozenset({"preference", "fact"})


class MemoryOrchestrator:
    """Singleton: memory writes (extract + route) and reads (intent-based retrieval for tools)."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.sql_store = SQLMemoryStore()
        self.nosql_store = NoSQLMemoryStore()
        self.vector_store = VectorMemoryStore()

        self.sql_store.initialize()
        self.nosql_store.initialize()
        self.vector_store.initialize()

        self._llm = LocalLLM()

        self.category_to_store_map = {
            "preference": self.nosql_store,
            "fact": self.nosql_store,
            "constraint": self.sql_store,
            "reminder": self.sql_store,
            "todo": self.sql_store,
            "commitment": self.sql_store,
            "episodic": self.vector_store,
        }

        logger.info("MemoryOrchestrator initialized (stores + LocalLLM for extraction)")
        self._initialized = True

    def store_memory_from_prompt(self, prompt: str) -> dict[str, Any]:
        """Extract memory JSON (sys_prompt_slm) and persist each item to the correct store."""
        logger.info("store_memory_from_prompt user_prompt_chars=%s", len(prompt))
        logger.debug("store_memory_from_prompt user_prompt=\n%s", prompt)

        information = self._llm.memory_extract(prompt)
        logger.info(
            "memory_extract JSON (full):\n%s",
            json.dumps(information, ensure_ascii=False, default=str, indent=2),
        )

        for memory in information.get("memory_items", []):
            category = memory.get("category")
            store = self.category_to_store_map.get(category)
            if store:
                logger.info(
                    "Routing memory category=%s to %s payload=%s",
                    category,
                    type(store).__name__,
                    json.dumps(memory, ensure_ascii=False, default=str),
                )
                store.insert(memory)
            else:
                logger.warning("Invalid or unsupported category %r; skipping store", category)

        return information

    def retrieve_for_agent(self, query: str, limit: int = 10) -> str:
        """
        AI-driven retrieval. Uses the active LLM to parse dates and keywords,
        then queries all backends (SQL, Mongo, Vector) intelligently.
        Returns a JSON string (possibly truncated) for the chat context.
        """
        logger.info("retrieve_for_agent request query=%r limit=%s", query, limit)
        lim = max(1, min(int(limit), 50))
        
        # 1. AI Parse
        from datetime import datetime
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        from LLMS.provider import LLMProvider
        
        current_time_str = datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
        prompt = PromptTemplate(
            template="""You are an AI query translator for a memory database.
User query: "{query}"
Current exact date/time: {current_time}

Extract the temporal bounds and semantic keywords into JSON.
If the query mentions "today", use the boundaries of today. 
If "tomorrow", use tomorrow's bounds.

Output EXACTLY this JSON structure, and nothing else (no markdown ticks):
{{
  "start_date": "YYYY-MM-DDTHH:MM:SS" (or null if no time context),
  "end_date": "YYYY-MM-DDTHH:MM:SS" (or null if no time context),
  "keywords": "the singular root noun to search for (e.g. 'reminder' instead of 'reminders', 'book' instead of 'books')"
}}
""",
            input_variables=["query", "current_time"]
        )
        
        try:
            print(f"      {_CYAN}[_] Analyzing memory query using AI translator...{_RESET}", flush=True)
            model = LLMProvider().get_chat_model()
            chain = prompt | model | JsonOutputParser()
            parsed = chain.invoke({"query": query, "current_time": current_time_str})
            logger.info("AI Query Parser result: %s", parsed)
        except Exception as e:
            logger.error("AI Query Parser failed, checking raw query: %s", e)
            parsed = {"keywords": query}

        # Date parsing
        start_dt, end_dt = None, None
        try:
            if parsed.get("start_date"):
                start_dt = datetime.fromisoformat(parsed["start_date"].replace("Z", ""))
            if parsed.get("end_date"):
                end_dt = datetime.fromisoformat(parsed["end_date"].replace("Z", ""))
        except Exception as e:
            logger.warning("Could not parse AI dates: %s", e)

        search_kw = parsed.get("keywords") or query

        results: list[dict[str, Any]] = []
        errors: list[str] = []

        def _run_vector(n: int) -> None:
            try:
                print(f"      {_CYAN}[-] Searching semantic Episodic/Vector Memories...{_RESET}", flush=True)
                results.extend(self.vector_store.semantic_search(search_kw, limit=n))
            except Exception as e:
                errors.append(f"vector: {e!s}")

        def _run_sql(n: int) -> None:
            try:
                if start_dt or end_dt:
                    print(f"      {_CYAN}[-] Searching Time-bound SQL Memories ({start_dt.date() if start_dt else '...'} to {end_dt.date() if end_dt else '...'})...{_RESET}", flush=True)
                else:
                    print(f"      {_CYAN}[-] Searching SQL Commitments...{_RESET}", flush=True)
                sql_res = self.sql_store.search_memories(
                        search_kw, 
                        categories=None, 
                        limit=n,
                        start_date=start_dt,
                        end_date=end_dt
                    )
                
                # Fallback if time-bound yields nothing, search globally for the keyword
                if not sql_res and (start_dt or end_dt):
                    print(f"      {_CYAN}[-] Time-bound search returned empty, falling back to global SQL search...{_RESET}", flush=True)
                    sql_res = self.sql_store.search_memories(
                        search_kw,
                        categories=None,
                        limit=n,
                        start_date=None,
                        end_date=None
                    )
                    
                results.extend(sql_res)
            except Exception as e:
                errors.append(f"sql: {e!s}")

        def _run_mongo(n: int) -> None:
            try:
                print(f"      {_CYAN}[-] Searching Document Preferences...{_RESET}", flush=True)
                results.extend(
                    self.nosql_store.search_memories(search_kw, categories=None, limit=n)
                )
            except Exception as e:
                errors.append(f"mongo: {e!s}")

        # Run all stores simultaneously
        third = max(1, lim // 3)
        _run_vector(third)
        _run_sql(third)
        _run_mongo(third)

        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for item in results:
            mid = str(item.get("memory_id", item.get("id", "")))
            src = str(item.get("source", ""))
            key = (src, mid)
            if mid and key in seen:
                continue
            if mid:
                seen.add(key)
            deduped.append(item)

        payload = {"parser_keywords": search_kw, "query": query, "results": deduped, "errors": errors}
        text = json.dumps(payload, ensure_ascii=False, default=str)

        max_chars = int(os.getenv("DESKTOPLM_MAX_TOOL_CHARS", "12000"))
        logger.info(
            "retrieve_for_agent raw payload (pre-truncate) chars=%s errors=%s",
            len(text),
            errors,
        )
        logger.debug("retrieve_for_agent raw JSON:\n%s", text)

        if len(text) > max_chars:
            text = text[: max_chars - 80] + "\n... [truncated for context limit]"

        logger.info("retrieve_for_agent returning to tool chars=%s", len(text))
        logger.debug("retrieve_for_agent return body:\n%s", text)
        return text


if __name__ == "__main__":
    try:
        from agent.run_logging import configure_logging

        configure_logging()
    except ImportError:
        logging.basicConfig(level=logging.INFO)
    print("Use: desktoplm demo-memory   or   desktoplm chat \"your message\"")
