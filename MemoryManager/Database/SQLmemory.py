import os
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
# from MemoryManager.memory import Memory
# from MemoryManager.base_store import BaseStore
import uuid
from datetime import datetime

# 1. Define the Base class for ORM models
Base = declarative_base()

# 2. Define the Table Schema as a Python Class
class MemoryModel(Base):
    __tablename__ = 'memories'

    memory_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, nullable=False)
    interpreted_meaning = Column(String, nullable=False)
    
    # Storing datetimes. SQLite doesn't have a specific TIMESTAMPTZ type, 
    # but SQLAlchemy handles conversion to Python datetime objects automatically.
    source_datetime = Column(DateTime, nullable=False)
    interpreted_datetime = Column(DateTime, nullable=True)

    datetime_confidence = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    importance = Column(Float, nullable=True)

    def __repr__(self):
        return f"<Memory(id='{self.memory_id}', category='{self.category}', text='{self.interpreted_meaning[:20]}...')>"

    # 2. to_dict converts the SQLAlchemy object to a clean dictionary
    def to_dict(self):
        return {
            "memory_id": self.memory_id,
            "category": self.category,
            "text": self.interpreted_meaning,
            "created_at": str(self.source_datetime), # Convert datetime to string for printing
            "confidence": self.confidence,
            "importance": self.importance
        }
    
    def __str__(self):
        return (
            f"----------------------------------------\n"
            f"ID:          {self.memory_id}\n"
            f"Category:    {self.category}\n"
            f"Meaning:     {self.interpreted_meaning}\n"
            f"Source Date: {self.source_datetime}\n"
            f"Event Date:  {self.interpreted_datetime}\n"
            f"Confidence:  {self.confidence}\n"
            f"Importance:  {self.importance}\n"
            f"----------------------------------------"
        )

class SQLMemoryStore():
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SQLMemoryStore, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path="data/sql/memory.db"):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.db_path = db_path
        self.engine = None
        self.Session = None
        self._initialized = True

    def initilize(self):
   
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

       
        connection_string = f"sqlite:///{self.db_path}"
        self.engine = create_engine(connection_string)

       
        Base.metadata.create_all(self.engine)

       
        self.Session = sessionmaker(bind=self.engine)
        print("DATABASE INITILIZED SUCCESSFULLY")

    def shutdown(self):
        if self.engine:
            self.engine.dispose()

    def insert(self, data: dict):
        if not self.Session:
            raise Exception("Database not initialized. Call initialize() first.")

        session = self.Session()
        try:
            # Helper to clean date values
            def clean_date(dt_val, default_val=None):
                if isinstance(dt_val, datetime):
                    return dt_val
                if isinstance(dt_val, str) and dt_val.strip():
                    # Check for garbage template strings
                    if dt_val.startswith("$") or "{" in dt_val or "get_curr" in dt_val:
                        return default_val
                    try:
                        return datetime.fromisoformat(dt_val)
                    except ValueError:
                        return default_val
                return default_val

            # Handle flexible keys and date cleaning
            src_dt = clean_date(data.get("source_datetime", data.get("created_at")), default_val=datetime.now())
            interp_dt = clean_date(data.get("interpreted_datetime", data.get("event_time")), default_val=None)
            meaning = data.get("interpreted_meaning", data.get("text", ""))

            # 6. Create a Model Instance (Row)
            new_memory = MemoryModel(
                memory_id=str(uuid.uuid4()), 
                category=data.get("category"),
                interpreted_meaning=meaning,
                source_datetime=src_dt,
                interpreted_datetime=interp_dt,
                datetime_confidence=data.get("datetime_confidence", 0.0),
                confidence=data.get("confidence", 0.0),
                importance=data.get("importance", 0.0)
            )

            # 7. Add and Commit
            session.add(new_memory)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error inserting memory: {e}")
            raise e
        finally:
            session.close()

    def deletebyId(self,id):
        session = self.Session()

        user = session.query(MemoryModel).filter(memory_id= id).first()
        if user:
            print(user)
            print(" Deleting this data from the database")
            session.delete(user)
            session.commit()

    def showdata(self):
        session = self.Session()
        result = session.query(MemoryModel).all()
        print(result)
        for i in result:
            print(i.__str__())
        

        print("ALL DATA DISPLAYED")

    def deletebyId(self,id):
        session = self.Session()
        user = session.query(MemoryModel).filter(MemoryModel.memory_id == id).first()
        if user:
            session.delete(user)
            session.commit()

        print("SUCESSFULLY DELETED THE DATA")

    def deleteAllData(self):
        session = self.Session()
        try:
         
            num_rows_deleted = session.query(MemoryModel).delete(synchronize_session=False)
            session.commit()
            print(f"Deleted {num_rows_deleted} rows from User table.")
        except:
            session.rollback()
        finally:
            session.close()

if __name__ == "__main__":
    # print("startinf the SQL database")


    # fake_json_data = {
    #     "uuid": str(uuid.uuid4()),
    #     "category": "user_preference",
    #     "text": "The user prefers dark mode in VS Code.",
    #     "created_at": datetime.now(),
    #     "event_time": datetime.now(),
    #     "confidence": 0.95,
    #     "importance": 0.8
    # }


    database = SQLMemoryStore()
    database.initilize()


    # database.insert(fake_json_data)
    database.showdata()




    # print("DELETING ALL THE DATA FROM THE USER")
    # database.deleteAllData()
    # database.showdata()

    



