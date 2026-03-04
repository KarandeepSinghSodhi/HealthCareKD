import logging
logger = logging.getLogger(__name__)
import os
import json
from pathlib import Path
from typing import List, Dict

# Load .env relative to this module file — works regardless of cwd or subprocess
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from core import config

from models.schemas import SpecialistConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

class AgentManager:
    def __init__(self, agents_dir: str = "agents"):
        self.agents_dir = agents_dir
        self.specialists: Dict[str, SpecialistConfig] = {}
        self._load_specialists()
        
        # Initialize the cheap router model (e.g. Gemini Flash)
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
            logger.info(f"Initializing real Gemini router model '{model_name}' with provided API key.")
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
            self.llm = FakeMessagesListChatModel(responses=[AIMessage(content="YES"), AIMessage(content="I am a mock response.")])
        
        # The prompt for the "Whisper Protocol"
        self.router_prompt = PromptTemplate(
            input_variables=["specialty", "symptoms"],
            template="""
Given the following patient symptoms/messages:
"{symptoms}"

You are evaluating if a {specialty} is still relevant to the patient's case.
If the symptoms are completely unrelated to {specialty}, respond with exactly the word "NO".
If the symptoms could be related to {specialty}, or if it's too early to tell, respond with exactly the word "YES".

Respond with only YES or NO.
"""
        )

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

    async def evaluate_dropout(self, active_specialist_ids: List[str], chat_history: str) -> List[str]:
        logger.info(f"Evaluating dropout for specialists: {active_specialist_ids} with chat_history: {chat_history}")
        """Runs the whisper protocol to determine who stays. Returns the list of IDs that are still active."""
        if len(active_specialist_ids) <= 1:
            return active_specialist_ids # Never drop the last one
            
        remaining = []
        # In a production app, we would run these concurrently via asyncio.gather
        for spec_id in active_specialist_ids:
            logger.info(f"Evaluating specialist: {spec_id}")
            if spec_id == "cmo": 
                # CMO always stays until the very end, or drops out as soon as another specialist takes over?
                # Actually, let's say CMO drops out when only 1 other specialist remains.
                remaining.append(spec_id)
                continue
                
            spec = self.specialists.get(spec_id)
            if not spec: continue

            # Ask the LLM if this specialty is still relevant
            chain = self.router_prompt | self.llm
            logger.info(f"Calling LLM for specialist '{spec_id}' with symptoms: {chat_history}")
            response = await chain.ainvoke({
                "specialty": spec.name,
                "symptoms": chat_history
            })
            logger.info(f"LLM response for '{spec_id}': {response.content}")
            
            # Robustly handle all possible LLM response types
            content = response.content
            logger.info(f"Raw LLM content for '{spec_id}': {content}")
            if isinstance(content, str):
                answer = content.strip().upper()
            elif isinstance(content, list):
                # List of dicts or strings
                if all(isinstance(item, dict) and 'text' in item for item in content):
                    answer = " ".join(item['text'] for item in content if 'text' in item).strip().upper()
                else:
                    answer = " ".join(str(item) for item in content).strip().upper()
            elif isinstance(content, dict) and 'text' in content:
                answer = content['text'].strip().upper()
            else:
                answer = str(content).strip().upper()
            logger.info(f"Processed answer for '{spec_id}': {answer}")
            if "YES" in answer:
                remaining.append(spec_id)
                
        # If CMO is the only one left besides 1 specialist, the CMO drops out to let the specialist take over.
        if len(remaining) == 2 and "cmo" in remaining:
            logger.info("CMO is one of two remaining, removing CMO.")
            remaining.remove("cmo")
            
        logger.info(f"Final remaining specialists: {remaining}")
        return remaining

    async def generate_response(self, active_specialist_ids: List[str], messages: List[Dict]) -> str:
        logger.info(f"Generating response for active_specialist_ids: {active_specialist_ids} with messages: {messages}")
        """Generates the actual response to the user based on who is currently active."""
        # If CMO is active, CMO answers. 
        # If only one specialist is active, that specialist answers.
        
        primary_agent_id = "cmo" if "cmo" in active_specialist_ids else active_specialist_ids[0]
        agent = self.specialists.get(primary_agent_id)
        
        sys_prompt = agent.prompt if agent else "You are a helpful medical assistant."
        
        # Format messages for Langchain
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        lc_messages = [SystemMessage(content=sys_prompt)]
        for msg in messages:
            if msg['role'] == "user":
                lc_messages.append(HumanMessage(content=msg['content']))
            else:
                lc_messages.append(AIMessage(content=msg['content']))
                
        logger.info(f"Calling LLM for primary agent '{primary_agent_id}'")
        response = await self.llm.ainvoke(lc_messages)
        logger.info(f"LLM raw response from '{primary_agent_id}': {response.content}")
        # Robustly extract string from LLM output
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
        logger.info(f"LLM processed reply from '{primary_agent_id}': {reply}")
        return reply
