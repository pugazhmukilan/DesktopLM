# from base_store import BaseStore
import uuid
from pymongo import MongoClient


class NoSQLMemoryStore():
    def __init__(self, uri="mongodb://localhost:27017", db_name="memory_db"):
        if hasattr(self, "_initialized"):
            return

        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self._initialized = True

    def initialize(self):
        # MongoDB creates DB/collections lazily
        self.db.memories.create_index("memory_id", unique=True)
        

    def shutdown(self):
        self.client.close()


    def insert(self,data):
        if "memory_id" not in data:
            data["memory_id"] = str(uuid.uuid4())

        self.db.memories.insert_one(data)
        print("inserted ",data," in mongodb successfully")

    def showdata(self):
        result = self.db.memories.find()
        print("PRINTING ALL THE DATA FROM THE DATABASE")
        for doc in result:
            print(doc)

    def deletebyID(self,id):
        self.db.memories.delete_one({"memory_id": id})
        
    def deleteAllData(self):
        self.db.memories.delete_many({})

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