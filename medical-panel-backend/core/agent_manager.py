import logging
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import sys

# Custom handler with auto-flush
class FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Setup detailed logging for LLM responses
logger = logging.getLogger(__name__)

# Create LLM logger that outputs to stdout directly
llm_logger = logging.getLogger("llm_responses")
llm_logger.setLevel(logging.DEBUG)
llm_logger.propagate = False  # Don't propagate to root logger

# Ensure we have a handler
if not llm_logger.handlers:
    handler = FlushingStreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s [LLM] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    llm_logger.addHandler(handler)

# Load .env relative to this module file — works regardless of cwd or subprocess
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from core import config

from models.schemas import SpecialistConfig
from langchain_google_genai import ChatGoogleGenerativeAI

class AgentManager:
    def __init__(self, agents_dir: str = "agents"):
        self.agents_dir = agents_dir
        self.specialists: Dict[str, SpecialistConfig] = {}
        self._load_specialists()
        
        # Initialize the LLM model (e.g. Gemini Flash)
        # use the cached value from the config module, which already triggered
        # dotenv.load_dotenv() during import.  Logging here helps diagnose if
        # the key was actually available at runtime.
        api_key = config.GOOGLE_API_KEY
        logger.info(f"AgentManager read GOOGLE_API_KEY={api_key[:4] + '...' if api_key else None}")
        # it's common during development to forget to restart the server
        # after adding the .env file.  the check below mirrors the one in
        # core/config.py so that we consistently decide whether to hit the
        # real Gemini API or fall back to our fake model.
        if api_key and api_key != "your_api_key_here":
            model_name = config.GOOGLE_MODEL
            logger.info(f"Initializing real Gemini model '{model_name}' with provided API key.")
            # note: ChatGoogleGenerativeAI will throw its own exception if the
            # model name isn't valid.  we choose an env-configurable value so
            # that the user can upgrade models without changing code.
            self.llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
        else:
            # log more detail so the user isn't left wondering why responses
            # look mocked even when they've "set" a key.
            print("WARNING: Using a mock LLM because GOOGLE_API_KEY is not set or is default.")
            from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
            from langchain_core.messages import AIMessage
            self.llm = FakeMessagesListChatModel(responses=[AIMessage(content="I am a mock response.")])

    def _load_specialists(self):
        """Dynamically loads all specialist configurations from the agents directory, respecting agents_enabled.json."""
        enabled_path = Path(__file__).parent.parent / "agents_enabled.json"
        enabled_agents = None
        if enabled_path.exists():
            with open(enabled_path, "r") as f:
                enabled_agents = json.load(f)
            logger.info(f"Loaded enabled agents config: {enabled_agents}")
        else:
            logger.warning("agents_enabled.json not found; all agents will be enabled by default.")

        for entry in os.scandir(self.agents_dir):
            if entry.is_dir():
                spec_id = entry.name
                if enabled_agents is not None and not enabled_agents.get(spec_id, True):
                    logger.info(f"Skipping disabled agent: {spec_id}")
                    continue
                config_path = os.path.join(entry.path, "config.json")
                prompt_path = os.path.join(entry.path, "prompt.txt")
                if os.path.exists(config_path) and os.path.exists(prompt_path):
                    with open(config_path, "r") as f:
                        config_data = json.load(f)
                    with open(prompt_path, "r") as f:
                        prompt_text = f.read()
                    self.specialists[spec_id] = SpecialistConfig(
                        id=spec_id,
                        name=config_data.get("name", spec_id.capitalize()),
                        theme=config_data.get("theme", spec_id),
                        colors=config_data.get("colors", {}),
                        avatar=config_data.get("avatar", f"{spec_id}.png"),
                        prompt=prompt_text
                    )
        logger.info(f"Loaded {len(self.specialists)} specialists: {list(self.specialists.keys())}")

    def get_all_specialists(self) -> List[SpecialistConfig]:
        return list(self.specialists.values())

    async def generate_response_with_rag(self, specialist_id: str, messages: List[Dict], rag_context: str = "") -> str:
        """Generates response from a specific specialist with RAG context augmentation.
        
        Args:
            specialist_id: ID of the specialist to generate response
            messages: Chat history as list of dicts with 'role' and 'content'
            rag_context: Retrieved medical document context from RAG system
            
        Returns:
            Generated response text from the specialist
        """
        start_time = datetime.now()
        print(f"\n>>> [ENTERING generate_response_with_rag] specialist_id={specialist_id}", flush=True)
        specialist = self.specialists.get(specialist_id)
        if not specialist:
            error_msg = "Specialist not found."
            print(f">>> [ERROR] Specialist {specialist_id} not found", flush=True)
            llm_logger.error(f"SPECIALIST_NOT_FOUND | specialist_id={specialist_id}")
            sys.stdout.flush()
            return error_msg
        
        # Augment system prompt with RAG context if available
        sys_prompt = specialist.prompt
        if rag_context:
            sys_prompt = f"{sys_prompt}\n\n--- MEDICAL DOCUMENT CONTEXT ---\n{rag_context}\n--- END CONTEXT ---\n\nUse the medical documents above to inform your response."
        
        # Format messages for Langchain
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        lc_messages = [SystemMessage(content=sys_prompt)]
        for msg in messages:
            if msg['role'] == "user":
                lc_messages.append(HumanMessage(content=msg['content']))
            else:
                lc_messages.append(AIMessage(content=msg['content']))
        
        # Log the request details
        user_content = ""
        for msg in messages:
            if msg['role'] == "user":
                user_content = msg['content']
                break
        
        llm_logger.info(f"REQUEST | specialist_id={specialist_id} | user_query={user_content[:100]}...")
        sys.stdout.flush()
        llm_logger.debug(f"PROMPT | specialist_id={specialist_id} | system_prompt={sys_prompt[:200]}...")
        sys.stdout.flush()
        
        print(f">>> [LLM_CALL] About to invoke LLM for {specialist_id}", flush=True)
        
        try:
            response = await self.llm.ainvoke(lc_messages)
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            # Extract response content
            content = response.content
            if isinstance(content, str):
                reply = content
            elif isinstance(content, list):
                # List of dicts or strings
                if all(isinstance(item, dict) and 'text' in item for item in content):
                    reply = "\n".join(item['text'] for item in content if 'text' in item)
                else:
                    reply = "\n".join(str(item) for item in content)
            elif isinstance(content, dict) and 'text' in content:
                reply = content['text']
            else:
                reply = str(content)
            
            # Try to extract token usage if available
            tokens_used = "N/A"
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                if usage:
                    tokens_used = f"input={usage.get('input_tokens', 'N/A')}, output={usage.get('output_tokens', 'N/A')}"
            
            response_length = len(reply)
            
            # Log the response details
            llm_logger.info(
                f"RESPONSE | specialist_id={specialist_id} | "
                f"timestamp={start_time.isoformat()} | "
                f"response_length={response_length} | "
                f"elapsed_time={elapsed:.2f}s | "
                f"tokens={tokens_used}"
            )
            sys.stdout.flush()
            llm_logger.debug(f"RESPONSE_TEXT | specialist_id={specialist_id} | text={reply[:500]}...")
            sys.stdout.flush()
            
            return reply
            
        except Exception as e:
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            error_msg = str(e)
            print(f">>> [EXCEPTION] {specialist_id}: {type(e).__name__}: {error_msg[:100]}", flush=True)
            llm_logger.error(
                f"ERROR | specialist_id={specialist_id} | "
                f"timestamp={start_time.isoformat()} | "
                f"elapsed_time={elapsed:.2f}s | "
                f"error_type={type(e).__name__} | "
                f"error_msg={error_msg[:200]}"
            )
            sys.stdout.flush()
            logger.error(f"Exception in /chat for specialist {specialist_id}", exc_info=True)
            
            return f"Error: {error_msg}"
    
    async def generate_all_responses_with_rag(self, active_specialist_ids: List[str], messages: List[Dict], rag_context: str = "") -> Dict[str, str]:
        """Generate responses from all active specialists with RAG context.
        
        Args:
            active_specialist_ids: List of specialist IDs to generate responses
            messages: Chat history as list of dicts with 'role' and 'content'
            rag_context: Retrieved medical document context from RAG system
            
        Returns:
            Dictionary mapping specialist_id -> response text
        """
        import asyncio
        
        # Generate all responses concurrently
        tasks = {
            spec_id: self.generate_response_with_rag(spec_id, messages, rag_context)
            for spec_id in active_specialist_ids
        }
        
        responses = {}
        for spec_id, task in tasks.items():
            responses[spec_id] = await task
        
        return responses
    
    async def triage_patient(self, messages: List[Dict], rag_context: str = "") -> List[str]:
        """Use CMO to determine which specialists should evaluate the patient.
        
        This reduces API calls from N to 1+M where M is number of relevant specialists.
        
        Args:
            messages: Chat history as list of dicts with 'role' and 'content'
            rag_context: Retrieved medical document context from RAG system
            
        Returns:
            List of specialist IDs that should respond
        """
        start_time = datetime.now()
        
        triage_prompt = """You are a Chief Medical Officer performing rapid triage.

A patient presents with the following symptoms. Analyze and determine which specialists should evaluate them.

Return ONLY a JSON list of specialist IDs, nothing else. Format:
["specialist1", "specialist2", ...]

Available specialists:
- cmo: Chief Medical Officer (always include for coordination)
- cardiologist: Heart and cardiovascular conditions
- dermatologist: Skin conditions
- neurologist: Brain and nervous system
- orthopedist: Bones and joints
- gastroenterologist: Digestive system
- pediatrician: Children's health
- psychiatrist: Mental health
- allergist: Allergies and immunology

Patient presentation:"""
        
        from langchain_core.messages import HumanMessage, SystemMessage
        
        # Get the user's last message (current symptoms)
        user_query = ""
        for msg in reversed(messages):
            if msg['role'] == "user":
                user_query = msg['content']
                break
        
        triage_messages = [
            SystemMessage(content=triage_prompt),
            HumanMessage(content=user_query)
        ]
        
        llm_logger.info(f"TRIAGE_REQUEST | user_query={user_query[:100]}...")
        sys.stdout.flush()
        llm_logger.debug(f"TRIAGE_PROMPT | {triage_prompt[:200]}...")
        sys.stdout.flush()
        
        try:
            response = await self.llm.ainvoke(triage_messages)
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            # Extract list from response
            import re
            response_text = response.content
            
            # Log raw triage response
            llm_logger.debug(f"TRIAGE_RESPONSE_RAW | response={response_text}")
            sys.stdout.flush()
            
            if isinstance(response_text, str):
                # Try to find JSON in response
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    specialist_ids = json.loads(json_match.group())
                    # Validate and filter to available specialists
                    available = set(self.specialists.keys())
                    selected = [s for s in specialist_ids if s in available]
                    
                    llm_logger.info(
                        f"TRIAGE_RESULT | "
                        f"timestamp={start_time.isoformat()} | "
                        f"elapsed_time={elapsed:.2f}s | "
                        f"selected_specialists={selected} | "
                        f"count={len(selected)}"
                    )
                    sys.stdout.flush()
                    return selected if selected else ["cmo"]  # Fallback to CMO
        except Exception as e:
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            llm_logger.error(
                f"TRIAGE_ERROR | "
                f"timestamp={start_time.isoformat()} | "
                f"elapsed_time={elapsed:.2f}s | "
                f"error_type={type(e).__name__} | "
                f"error_msg={str(e)[:200]}"
            )
            sys.stdout.flush()
            logger.warning(f"Failed to parse triage response: {e}")
        
        # Fallback: return all specialists if triage fails
        llm_logger.warning("TRIAGE_FALLBACK | Using all specialists")
        sys.stdout.flush()
        return list(self.specialists.keys())
    
    async def generate_responses_streaming(self, specialist_ids: List[str], messages: List[Dict], rag_context: str = ""):
        """Generate responses from specialists, yielding as they complete.
        
        Allows frontend to show responses in real-time as they arrive.
        
        Args:
            specialist_ids: List of specialist IDs
            messages: Chat history
            rag_context: Medical document context
            
        Yields:
            Tuples of (specialist_id, response_text) as they complete
        """
        import asyncio
        
        streaming_start = datetime.now()
        llm_logger.info(
            f"STREAMING_START | "
            f"timestamp={streaming_start.isoformat()} | "
            f"specialists={specialist_ids} | "
            f"specialist_count={len(specialist_ids)}"
        )
        
        # Create tasks for all specialists
        tasks = {
            spec_id: asyncio.create_task(self.generate_response_with_rag(spec_id, messages, rag_context))
            for spec_id in specialist_ids
        }
        
        completed_count = 0
        # Yield responses as they complete
        pending = set(tasks.values())
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                for spec_id, t in tasks.items():
                    if t == task:
                        completed_count += 1
                        try:
                            response = await t
                            response_preview = response[:100] if isinstance(response, str) else str(response)[:100]
                            llm_logger.info(
                                f"STREAMING_SPECIALIST_COMPLETE | "
                                f"specialist_id={spec_id} | "
                                f"response_preview={response_preview}... | "
                                f"batch_num={completed_count}"
                            )
                            yield (spec_id, response)
                        except Exception as e:
                            llm_logger.error(
                                f"STREAMING_SPECIALIST_ERROR | "
                                f"specialist_id={spec_id} | "
                                f"error_type={type(e).__name__} | "
                                f"error_msg={str(e)[:200]} | "
                                f"batch_num={completed_count}"
                            )
                            logger.error(f"Error with specialist {spec_id}: {e}")
                            yield (spec_id, f"Error: {str(e)}")
                        break
        
        streaming_end = datetime.now()
        elapsed = (streaming_end - streaming_start).total_seconds()
        
        llm_logger.info(
            f"STREAMING_COMPLETE | "
            f"timestamp={streaming_start.isoformat()} | "
            f"elapsed_time={elapsed:.2f}s | "
            f"total_specialists={len(specialist_ids)} | "
            f"batch_count={completed_count}"
        )
