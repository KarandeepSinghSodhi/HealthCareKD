
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import asyncio
from core.agent_manager import AgentManager
from models.schemas import ChatRequest, ChatResponse, SpecialistConfig

logger = logging.getLogger(__name__)
router = APIRouter()
manager = AgentManager() # Instantiated on startup

@router.get("/specialists", response_model=List[SpecialistConfig])
async def get_specialists():
    """Returns the list of all available specialists on startup."""
    logger.info("GET /specialists called")
    result = manager.get_all_specialists()
    logger.info(f"Returning {len(result)} specialists")
    return result

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handles a new chat message from the user."""
    logger.info("POST /chat called")
    try:
        # Extract chat history to a string for the whisper protocol evaluation
        chat_history = "\n".join([f"{m.role}: {m.content}" for m in request.messages])
        logger.info(f"Chat history: {chat_history}")

        # 1. Evaluate who drops out
        logger.info(f"Evaluating dropout for specialists: {request.active_specialists}")
        new_active = await manager.evaluate_dropout(request.active_specialists, chat_history)
        logger.info(f"Active specialists after dropout: {new_active}")

        dropped = [spec for spec in request.active_specialists if spec not in new_active]
        logger.info(f"Dropped specialists: {dropped}")

        # 2. Get the response from the primary active agent
        dict_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        logger.info(f"Sending messages to generate_response: {dict_messages}")
        reply_content = await manager.generate_response(new_active, dict_messages)
        logger.info(f"LLM reply: {reply_content}")

        return ChatResponse(
            response=reply_content,
            active_specialists=new_active,
            dropped_specialists=dropped
        )
    except Exception as e:
        import traceback
        logger.error("Exception in /chat endpoint", exc_info=True)
        # If the error is a quota/RESOURCE_EXHAUSTED, return a helpful message
        err_str = str(e)
        if 'RESOURCE_EXHAUSTED' in err_str or 'quota' in err_str.lower():
            logger.warning("Quota or rate limit exceeded in /chat endpoint")
            return ChatResponse(
                response=("The LLM service has exceeded its quota or rate limit. "
                          "Please wait a moment or switch to a different model."),
                active_specialists=request.active_specialists,
                dropped_specialists=[]
            )
        raise HTTPException(status_code=500, detail=str(e))
