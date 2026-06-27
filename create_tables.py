import sys
import os

# Menambahkan root project ke sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine, Base
from app.db.models import *

print("Mencoba membuat tabel di database ai_cv...")
try:
    Base.metadata.create_all(bind=engine)
    print("Semua tabel berhasil dibuat!")
except Exception as e:
    print(f"Error: {e}")
