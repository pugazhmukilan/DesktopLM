import datetime
import os
import pickle
import uuid
import chromadb

class VectorMemoryStore():
    def __init__(self, index_path="data/vectordb",collectionname = "data"):
        if hasattr(self, "_initialized"):
            return

        self.index_path = index_path
        self.index = {}
        self.client = None
        self.collection_name = collectionname
        self.collection= None
        self._initialized = True

    def initilize(self):
        

        self.client = chromadb.PersistentClient(path = self.index_path)
        self.collection = self.client.get_or_create_collection(name = self.collection_name)
        print("VECTOR DB INITILIZED")


    def shutdown(self):
        with open(self.index_path, "wb") as f:
            pickle.dump(self.index, f)


    def insert(self,data):
        if "memory_id" not in data:
            data["memory_id"] = str(uuid.uuid4())

        ## TODO: Add the data in the SQL or NOSQL then get the id and use it here

        # Use 'interpreted_meaning' as text if 'text' is missing
        text_content = data.get("interpreted_meaning", data.get("text", ""))
        print("the text which is stored in the vectorDB")
        print(text_content)

        metad = data.copy()
        metad.pop("text",None)
        metad.pop("interpreted_meaning", None) # Remove content from metadata
        metad.pop("memory_id",None)
        
        # Ensure metadata values are strings (Chroma requirement)
        for key,value in metad.items():
            # print(key, value)
            metad[key] = str(value)


        self.collection.add(
            ids = data["memory_id"],
            documents = text_content,
            metadatas = metad
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

    
if __name__ == "__main__":
    print("starting the vectorDB")

    database = VectorMemoryStore()
    database.initilize()

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
