# from base_store import BaseStore
import logging
import re
import uuid
from pymongo import MongoClient

from MemoryManager.settings import mongo_db_name, mongo_uri

logger = logging.getLogger(__name__)


class NoSQLMemoryStore:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, uri=None, db_name=None):
        if hasattr(self, "_initialized"):
            return

        uri = uri if uri is not None else mongo_uri()
        db_name = db_name if db_name is not None else mongo_db_name()
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self._initialized = True

    def initialize(self):
        if getattr(self, "_mongo_init_done", False):
            return
        self.db.memories.create_index("memory_id", unique=True)
        self._mongo_init_done = True
        logger.info("MongoDB memory store ready (db=%s)", self.db.name)
        

    def shutdown(self):
        self.client.close()


    def insert(self,data):
        if "memory_id" not in data:
            data["memory_id"] = str(uuid.uuid4())

        self.db.memories.insert_one(data)
        logger.debug("MongoDB insert memory_id=%s", data.get("memory_id"))

    def showdata(self):
        result = self.db.memories.find()
        print("PRINTING ALL THE DATA FROM THE DATABASE")
        for doc in result:
            print(doc)

    def deletebyID(self,id):
        self.db.memories.delete_one({"memory_id": id})
        
    def deleteAllData(self):
        self.db.memories.delete_many({})

    def search_memories(
        self,
        query: str,
        *,
        categories: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Text search over stored memory documents (preferences, facts, etc.)."""
        lim = max(1, min(limit, 100))
        qstrip = (query or "").strip()
        filters = []

        if categories:
            filters.append({"category": {"$in": categories}})

        if qstrip:
            esc = re.escape(qstrip)
            filters.append(
                {
                    "$or": [
                        {"interpreted_meaning": {"$regex": esc, "$options": "i"}},
                        {"text": {"$regex": esc, "$options": "i"}},
                        {"category": {"$regex": esc, "$options": "i"}},
                    ]
                }
            )

        mongo_filter = {"$and": filters} if len(filters) > 1 else (filters[0] if filters else {})

        cursor = self.db.memories.find(mongo_filter).limit(lim)
        out: list[dict] = []
        for doc in cursor:
            d = dict(doc)
            d.pop("_id", None)
            d["source"] = "mongo"
            out.append(d)
        return out

if __name__ == "__main__":
    database = NoSQLMemoryStore()
    database.initialize()

    database.insert({"name" :"pugazh mukilan","number":3})

    database.showdata()

    print("deleting some data")
    database.deletebyID("9fd44b14-1c00-4eab-927c-f4cb8de72bbb")
    database.showdata()


    database.deleteAllData()
    database.showdata()