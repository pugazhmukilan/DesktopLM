class MemoryManager():
    _instance = None
    def __new__(self,*args,**kwargs):
        if self._instance == None:
            self._instance = super(MemoryManager,self).__new__(self)

        return self._instance
    
    def __init__(self):
        if hasattr(self,"_initialized"):
            return
        

        self.sql_store = None
        self.nosql_store = None
        self.vector_store = None

        self._initialized = True


        


    
    
        