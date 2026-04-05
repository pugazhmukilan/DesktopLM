import datetime
import logging
import os
import pickle
import uuid
import chromadb

from MemoryManager.settings import chroma_persist_path

logger = logging.getLogger(__name__)

class VectorMemoryStore:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, index_path=None, collectionname="data"):
        if hasattr(self, "_initialized"):
            return

        self.index_path = index_path if index_path is not None else chroma_persist_path()
        self.index = {}
        self.client = None
        self.collection_name = collectionname
        self.collection = None
        self._initialized = True

    def initialize(self):
        if self.client is not None:
            return

        self.client = chromadb.PersistentClient(path=self.index_path)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        logger.info("Chroma vector store ready (%s)", self.index_path)


    def shutdown(self):
        with open(self.index_path, "wb") as f:
            pickle.dump(self.index, f)


    def insert(self,data):
        if "memory_id" not in data:
            data["memory_id"] = str(uuid.uuid4())

        ## TODO: Add the data in the SQL or NOSQL then get the id and use it here

        # Use 'interpreted_meaning' as text if 'text' is missing
        text_content = data.get("interpreted_meaning", data.get("text", ""))
        logger.debug("Chroma document: %s", (text_content or "")[:300])

        metad = data.copy()
        metad.pop("text",None)
        metad.pop("interpreted_meaning", None) # Remove content from metadata
        metad.pop("memory_id",None)
        
        # Ensure metadata values are strings (Chroma requirement)
        for key,value in metad.items():
            # print(key, value)
            metad[key] = str(value)


        mid = str(data["memory_id"])
        doc = str(text_content) if text_content is not None else ""
        self.collection.add(
            ids=[mid],
            documents=[doc],
            metadatas=[metad],
        )

    def showdata(self):

        all_data = self.collection.get(
            include=["metadatas", "documents", "embeddings"] 
        )
        print(f"--- Total Records: {len(all_data['ids'])} ---")
        
        # Iterate through the results
        for i in range(len(all_data['ids'])):
            print(f"ID: {all_data['ids'][i]}")
            print(f"Text: {all_data['documents'][i]}")
            print(f"Metadata: {all_data['metadatas'][i]}")
            # Embeddings are long lists of numbers, usually you don't print the whole thing
            print(f"Embedding Length: {len(all_data['embeddings'][i])}") 
            print("-" * 20)

    def semantic_search(self, query: str, limit: int = 10) -> list[dict]:
        """Chroma semantic search over episodic / vector-backed memories."""
        if not self.collection:
            raise RuntimeError("Vector store not initialized. Call initialize() first.")

        n = max(1, min(limit, 50))
        raw = self.collection.query(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        ids_batch = raw.get("ids") or []
        docs_batch = raw.get("documents") or []
        meta_batch = raw.get("metadatas") or []
        dist_batch = raw.get("distances") or []

        ids = ids_batch[0] if ids_batch and isinstance(ids_batch[0], list) else ids_batch
        docs = docs_batch[0] if docs_batch and isinstance(docs_batch[0], list) else docs_batch
        metas = meta_batch[0] if meta_batch and isinstance(meta_batch[0], list) else meta_batch
        dists = dist_batch[0] if dist_batch and isinstance(dist_batch[0], list) else dist_batch

        out: list[dict] = []
        for i, mid in enumerate(ids or []):
            out.append(
                {
                    "source": "vector",
                    "memory_id": mid,
                    "text": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if dists is not None and i < len(dists) else None,
                }
            )
        return out

    
if __name__ == "__main__":
    print("starting the vectorDB")

    database = VectorMemoryStore()
    database.initialize()

    fake_json_data = {
        "uuid": str(uuid.uuid4()),
        "category": "user_preference",
        "text": "The user prefers dark mode in VS Code.",
        "created_at": datetime.datetime.now(),
        "event_time": datetime.datetime.now(),
        "confidence": 0.95,
        "importance": 0.8
    }
    database.insert(fake_json_data)

    database.showdata()
