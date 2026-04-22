import os
from pathlib import Path
from dotenv import load_dotenv
import logging
import asyncio

# Always load the .env relative to this file, not cwd.
# This fixes the uvicorn --reload subprocess not finding .env.
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import routes
from core.agent_manager import AgentManager
from rag.rag_manager import RAGManager


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

# Initialize managers
logger.info("Initializing AgentManager...")
agent_manager = AgentManager()
routes.set_manager(agent_manager)

# Initialize RAG system (lazy loading - documents loaded on first /reload-documents call)
logger.info("Initializing RAG system...")
documents_dir = Path(__file__).parent / "rag" / "documents"
embeddings_dir = Path(__file__).parent / "rag" / "embeddings"
rag_manager = None
try:
    rag_manager = RAGManager(str(documents_dir), str(embeddings_dir))
    logger.info("RAG Manager created (documents will be loaded on demand via /reload-documents endpoint)")
    routes.set_rag_manager(rag_manager)
except Exception as e:
    logger.warning(f"RAG Manager initialization failed (backend will continue without RAG): {e}")
    rag_manager = None
    # Continue - backend can work without RAG

app.include_router(routes.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Medical Panel API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
