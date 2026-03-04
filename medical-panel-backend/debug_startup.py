import traceback
import sys
from core.agent_manager import AgentManager

try:
    print("Initializing AgentManager...")
    manager = AgentManager()
    print("Success!")
except Exception as e:
    print("Failed to initialize AgentManager:")
    traceback.print_exc()
