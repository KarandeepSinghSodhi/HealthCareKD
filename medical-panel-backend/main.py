import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Always load the .env relative to this file, not cwd.
# This fixes the uvicorn --reload subprocess not finding .env.
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Medical Panel Agent API")

# Configure CORS for the frontend Vite application
origins = [
    "http://localhost:5173", # Default Vite Port
    "http://127.0.0.1:5173",
    # Vite may pick another port if 5173 is busy (e.g. 5174). Allow common localhost dev ports.
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Medical Panel API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
