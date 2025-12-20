import os
import pickle


class VectorMemoryStore(BaseStore):
    def __init__(self, index_path="data/vectors/index.pkl"):
        if hasattr(self, "_initialized"):
            return

        self.index_path = index_path
        self.index = {}
        self._initialized = True

    def initialize(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        if os.path.exists(self.index_path):
            with open(self.index_path, "rb") as f:
                self.index = pickle.load(f)
        else:
            self.index = {}

    def shutdown(self):
        with open(self.index_path, "wb") as f:
            pickle.dump(self.index, f)


    
