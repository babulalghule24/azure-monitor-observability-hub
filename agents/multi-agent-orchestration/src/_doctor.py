"""Run this FIRST. It tells you exactly what your installed version exposes.

    python src/_doctor.py

The Microsoft Agent Framework is moving fast and names have changed across the Foundry
rebrand. Rather than guess, this prints what YOUR environment actually has, so you can
match the lab code to it in seconds.
"""

import importlib
import sys


def probe(module_name: str, wanted: list[str]) -> None:
    try:
        mod = importlib.import_module(module_name)
    except ImportError as exc:
        print(f"  [MISSING] {module_name:45} -> {exc}")
        return

    have = {n for n in dir(mod) if not n.startswith("_")}
    print(f"  [OK]      {module_name}")
    for name in wanted:
        mark = "yes" if name in have else " NO"
        print(f"              {mark}  {name}")

    # Anything client/builder-shaped we did not ask about
    extra = sorted(n for n in have
                   if (n.endswith("Client") or n.endswith("Builder") or n.endswith("Agent"))
                   and n not in wanted)
    if extra:
        print(f"              also: {', '.join(extra[:12])}")


def main() -> None:
    print(f"\nPython {sys.version.split()[0]}\n")

    try:
        import agent_framework
        print(f"agent-framework version: {getattr(agent_framework, '__version__', 'unknown')}\n")
    except ImportError:
        print("agent-framework is NOT installed. Run: pip install -r requirements.txt\n")
        return

    print("CLIENTS -------------------------------------------------------------")
    probe("agent_framework.foundry", ["FoundryChatClient", "FoundryAgent"])
    probe("agent_framework.azure", ["AzureAIClient", "AzureAIAgentClient", "AzureOpenAIChatClient"])

    print("\nORCHESTRATION BUILDERS ----------------------------------------------")
    probe("agent_framework.orchestrations",
          ["SequentialBuilder", "ConcurrentBuilder", "HandoffBuilder",
           "GroupChatBuilder", "MagenticBuilder"])

    print("\nA2A -----------------------------------------------------------------")
    probe("a2a.types", ["AgentCard", "AgentSkill", "AgentCapabilities", "Message", "Part", "TextPart"])
    probe("a2a.server.apps", ["A2AStarletteApplication"])
    probe("a2a.client", ["A2ACardResolver", "ClientFactory"])

    print("""
--------------------------------------------------------------------------
WHAT TO DO WITH THIS

* If agent_framework.foundry shows FoundryChatClient  -> you are on the current
  (post-rebrand) SDK. common.py will use it automatically. Nothing to change.

* If only agent_framework.azure shows AzureAIClient / AzureAIAgentClient -> you
  are on an older build. common.py falls back to it automatically.

* If a builder shows NO, check the exact name in the 'also:' line and adjust the
  import in that step file. The official samples are the ground truth:
  https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations
--------------------------------------------------------------------------
""")


if __name__ == "__main__":
    main()
