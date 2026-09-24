import os
import sys

# Ensure the app package is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import engine, Base
from app.db.models import CadastralRecord

print("Initializing SQLite Database...")
Base.metadata.create_all(bind=engine)
print("Database initialized successfully at ./ksiti_local.db")
