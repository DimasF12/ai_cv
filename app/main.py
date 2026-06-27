from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn # Tambahkan import ini
from app.api.v1.router import api_router

app = FastAPI(title="AI Portal Backend")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "AI Portal Backend is running!"}

# Tambahkan blok ini di baris paling bawah
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8000, reload=True)