from dotenv import load_dotenv
load_dotenv(".env") 
from database.db import engine
from database.models import Base

Base.metadata.create_all(bind=engine)

print("Database initialized")
