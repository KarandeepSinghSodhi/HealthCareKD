from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Message(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    messages: List[Message]
    # Note: active_specialists removed - all enabled specialists always active
    # To specify which specialists respond, use agents_enabled.json configuration

class SpecialistConfig(BaseModel):
    id: str
    name: str
    theme: str
    colors: Dict[str, str]
    avatar: str
    prompt: str

class ChatResponse(BaseModel):
    response: str
    # For new architecture with multiple specialist responses
    specialist_responses: Optional[Dict[str, str]] = None  # specialist_id -> response text
    # Note: active_specialists and dropped_specialists removed
    # All enabled specialists in agents_enabled.json stay active throughout session

class RAGStats(BaseModel):
    total_chunks: int
    documents_loaded: int
    documents: List[str]

