import sys
import os

from LLMS.SLM import SLM
from MemoryManager.Database.SQLmemory import SQLMemoryStore
from MemoryManager.Database.nosqlmemory import NoSQLMemoryStore
from MemoryManager.Database.vectormemeorystore import VectorMemoryStore


class MemoryManager():
    _instance = None
    def __new__(self,*args,**kwargs):
        if self._instance == None:
            self._instance = super(MemoryManager,self).__new__(self)

        return self._instance
    
    def __init__(self):
        if hasattr(self,"_initialized"):
            return
        

        self.sql_store = SQLMemoryStore()
        self.sql_store.initilize()
        self.nosql_store = NoSQLMemoryStore()
        self.nosql_store.initilize()
        self.vector_store = VectorMemoryStore()
        self.vector_store.initilize()
        

        print("Booted database successfully")
        self._initialized = True

    def start (self,prompt):
        slm = SLM()
        infromation = slm.generate(prompt)
        print(infromation)

        ##TODO CREATE A CONDITIONAL RULES TO STORE IN THE APPROPRIATE DATABASE
        for memory in infromation['memory_items']:
            print(memory)

            if memory["category"] in  ["preference" , "fact"]:
                print("The memory will be store in NOSQL")
                self.nosql_store.insert(memory)
                break
            elif memory["category"] in ["constraint" , "reminder" , "todo" , "commitment"]:
                print("The memory will be store in SQL")
                self.sql_store.insert(memory)
                break
            elif memory["category"] in ["episodic"]:
                print("The memory will be stored in  vector")
                self.vector_store.insert(memory)
                break

            else:
                print("the category is ivalid")   
                
if __name__ == "__main__":
    mem = MemoryManager()
    prompt = "i have meetong at 10 pm  today and i always wanted to wear coat for every meeting"
    mem.start(prompt)






        


    
    
        