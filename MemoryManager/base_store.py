class BaseStore:


    _instance = None

    def  __new__(self,*args,**kwargs):
        if self._instance is None:
            self._instance = super(BaseStore,self).__new__(self)

        return self._instance
    

    def initilize(self):
        raise NotImplementedError
    def shutdown(self):
        raise NotImplementedError