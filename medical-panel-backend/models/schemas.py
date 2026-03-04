from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Message(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    messages: List[Message]
    active_specialists: List[str]

class SpecialistConfig(BaseModel):
    id: str
    name: str
    theme: str
    colors: Dict[str, str]
    avatar: str
    prompt: str

class ChatResponse(BaseModel):
    response: str
    active_specialists: List[str]
    dropped_specialists: List[str]
