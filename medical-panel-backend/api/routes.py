
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional
import asyncio
from core.agent_manager import AgentManager
from models.schemas import ChatRequest, ChatResponse, SpecialistConfig, RAGStats

logger = logging.getLogger(__name__)
router = APIRouter()

# Instantiated on startup (in main.py)
manager: Optional[AgentManager] = None
rag_manager: Optional['RAGManager'] = None

def set_manager(agent_manager: AgentManager):
    """Set the AgentManager instance (called from main.py)."""
    global manager
    manager = agent_manager

def set_rag_manager(rag_mgr):
    """Set the RAGManager instance (called from main.py)."""
    global rag_manager
    rag_manager = rag_mgr

@router.get("/specialists", response_model=List[SpecialistConfig])
async def get_specialists():
    """Returns the list of all available specialists."""
    logger.info("GET /specialists called")
    if not manager:
        raise HTTPException(status_code=500, detail="AgentManager not initialized")
    result = manager.get_all_specialists()
    logger.info(f"Returning {len(result)} specialists")
    return result

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handles a chat message from the user with RAG context retrieval."""
    logger.info("POST /chat called")
    try:
        if not manager:
            raise HTTPException(status_code=500, detail="AgentManager not initialized")
        
        # Extract user query from messages (last user message)
        user_query = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_query = msg.content
                break
        
        logger.info(f"User query: {user_query}")
        
        # 1. Retrieve relevant context from RAG if available
        rag_context = ""
        if rag_manager and rag_manager.collection.count() > 0:
            logger.info("Retrieving context from RAG system")
            rag_context = rag_manager.retrieve_context(user_query, top_k=3)
            logger.info(f"Retrieved RAG context (length: {len(rag_context)})")
        else:
            logger.info("RAG system not available or no documents loaded")
        
        # 2. Get all active specialists
        active_specialists = [spec.id for spec in manager.get_all_specialists()]
        logger.info(f"Active specialists: {active_specialists}")
        
        # 3. Generate responses from all active specialists with RAG context
        dict_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        logger.info(f"Generating responses from {len(active_specialists)} specialists")
        
        specialist_responses = await manager.generate_all_responses_with_rag(
            active_specialists, dict_messages, rag_context
        )
        logger.info(f"Generated {len(specialist_responses)} responses")
        
        # 3. Use primary specialist (CMO if available, else first) as main response
        primary_specialist = "cmo" if "cmo" in active_specialists else active_specialists[0]
        primary_response = specialist_responses.get(primary_specialist, "Unable to generate response")
        
        return ChatResponse(
            response=primary_response,
            specialist_responses=specialist_responses
        )
    except Exception as e:
        import traceback
        logger.error("Exception in /chat endpoint", exc_info=True)
        # If the error is a quota/RESOURCE_EXHAUSTED, return a helpful message
        err_str = str(e)
        if 'RESOURCE_EXHAUSTED' in err_str or 'quota' in err_str.lower():
            logger.warning("Quota or rate limit exceeded in /chat endpoint")
            return ChatResponse(
                response=(f"{err_str} Please try again later or contact support if the issue persists."),
                specialist_responses=None
            )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat-stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint with intelligent specialist selection (triage).
    
    1. CMO performs triage (1 call) to select relevant specialists
    2. Call selected specialists in parallel (typically 2-4 calls)
    3. Stream responses as Server-Sent Events (Real-time UI updates)
    
    Reduces typical 9 API calls → 1 + 3 = ~67% cost reduction.
    """
    logger.info("POST /chat-stream called")
    
    async def event_generator():
        try:
            if not manager:
                yield f"data: {{'error': 'AgentManager not initialized'}}\n\n"
                return
            
            # Convert request messages to dict format
            dict_messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            # Retrieve RAG context if available
            rag_context = ""
            if rag_manager and rag_manager.collection.count() > 0:
                user_query = ""
                for msg in reversed(dict_messages):
                    if msg['role'] == "user":
                        user_query = msg['content']
                        break
                if user_query:
                    rag_context = rag_manager.retrieve_context(user_query, top_k=3)
                    logger.info(f"Retrieved RAG context (length: {len(rag_context)})")
            
            # Step 1: Triage - select relevant specialists (1 LLM call)
            logger.info("Step 1: Performing triage...")
            yield "data: {\"event\": \"triage_start\"}\n\n"
            
            selected_specialists = await manager.triage_patient(dict_messages, rag_context)
            logger.info(f"Step 1 complete: Selected {len(selected_specialists)} specialists")
            
            yield f"data: {{'event': 'triage_complete', 'specialists': {selected_specialists}}}\n\n"
            
            # Step 2: Generate responses from selected specialists in parallel
            logger.info(f"Step 2: Generating responses from {len(selected_specialists)} specialists...")
            yield "data: {\"event\": \"generation_start\"}\n\n"
            
            specialist_responses = {}
            async for specialist_id, response_text in manager.generate_responses_streaming(
                selected_specialists, dict_messages, rag_context
            ):
                specialist_responses[specialist_id] = response_text
                # Send response as it arrives
                import json
                event_data = {
                    "event": "specialist_response",
                    "specialist_id": specialist_id,
                    "response": response_text
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                logger.info(f"Streamed response from {specialist_id}")
            
            # Step 3: Send final summary
            primary_specialist = "cmo" if "cmo" in specialist_responses else selected_specialists[0]
            primary_response = specialist_responses.get(primary_specialist, "Unable to generate response")
            
            final_event = {
                "event": "complete",
                "primary_response": primary_response,
                "specialist_responses": specialist_responses,
                "total_calls": len(selected_specialists) + 1  # +1 for triage
            }
            import json
            yield f"data: {json.dumps(final_event)}\n\n"
            logger.info(f"Stream complete: {len(specialist_responses)} responses, {len(selected_specialists) + 1} total LLM calls")
            
        except Exception as e:
            import json
            logger.error("Exception in /chat-stream endpoint", exc_info=True)
            error_event = {"event": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/reload-documents")
async def reload_documents():
    """Reload documents from the documents folder into RAG system."""
    logger.info("POST /reload-documents called")
    try:
        if not rag_manager:
            raise HTTPException(status_code=500, detail="RAG system not initialized")
        
        result = rag_manager.reload_documents()
        logger.info(f"Documents reloaded: {result}")
        return result
    except Exception as e:
        logger.error("Exception in /reload-documents endpoint", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rag-stats", response_model=RAGStats)
async def get_rag_stats():
    """Get statistics about RAG system (loaded documents and embeddings)."""
    logger.info("GET /rag-stats called")
    try:
        if not rag_manager:
            raise HTTPException(status_code=500, detail="RAG system not initialized")
        
        result = rag_manager.get_stats()
        return RAGStats(
            total_chunks=result["total_chunks"],
            documents_loaded=result["documents_loaded"],
            documents=result["documents"]
        )
    except Exception as e:
        logger.error("Exception in /rag-stats endpoint", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
