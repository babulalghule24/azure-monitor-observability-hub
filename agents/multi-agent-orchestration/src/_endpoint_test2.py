"""Endpoint + client probe, verbose. Tries every client class x endpoint form.

    python src/_endpoint_test2.py

Prints the FULL error for each attempt - the message text is what tells us which
knob is wrong.
"""

import asyncio
import os
import re

from dotenv import load_dotenv

load_dotenv()

RAW = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip().rstrip("/")
MODEL = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "").strip()

if "/api/projects/" in RAW:
    root, project = RAW.split("/api/projects/", 1)
else:
    root, project = RAW, ""

# resource name, e.g. "ainstein" from https://ainstein.services.ai.azure.com
m = re.match(r"https://([^.]+)\.", root)
resource = m.group(1) if m else ""

ENDPOINTS = [
    ("foundry project path", f"{root}/api/projects/{project}" if project else None),
    ("services root", root),
    ("openai host", f"https://{resource}.openai.azure.com" if resource else None),
    ("cognitiveservices host", f"https://{resource}.cognitiveservices.azure.com" if resource else None),
]


def get_cred():
    from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
    if os.environ.get("LAB_USE_CLI_CREDENTIAL") == "1":
        return AzureCliCredential()
    return DefaultAzureCredential()


def list_clients():
    """Every client class actually present in this install."""
    found = []
    try:
        from agent_framework.foundry import FoundryChatClient
        found.append(("FoundryChatClient", FoundryChatClient, "project_endpoint", "model", "credential"))
    except ImportError:
        pass
    for mod, cls_name, ep_kw, model_kw, cred_kw in [
        ("agent_framework.azure", "AzureOpenAIChatClient", "endpoint", "deployment_name", "credential"),
        ("agent_framework.azure", "AzureAIClient", "project_endpoint", "model_deployment_name", "async_credential"),
        ("agent_framework.azure", "AzureAIAgentClient", "project_endpoint", "model_deployment_name", "async_credential"),
    ]:
        try:
            module = __import__(mod, fromlist=[cls_name])
            found.append((cls_name, getattr(module, cls_name), ep_kw, model_kw, cred_kw))
        except (ImportError, AttributeError):
            pass
    return found


async def attempt(cls_name, cls, ep_kw, model_kw, cred_kw, label, endpoint):
    cred = get_cred()
    try:
        kwargs = {ep_kw: endpoint, model_kw: MODEL, cred_kw: cred}
        client = cls(**kwargs)
        factory = getattr(client, "as_agent", None) or getattr(client, "create_agent", None)
        agent = factory(name="Probe", instructions="Reply with exactly: pong")
        result = await agent.run("ping")
        print(f"    *** SUCCESS *** -> {str(result).strip()[:80]}")
        return endpoint, cls_name
    except TypeError as exc:
        print(f"    signature mismatch: {str(exc)[:150]}")
    except Exception as exc:
        msg = str(exc)
        # pull the human-readable message out of the blob
        hit = re.search(r"'message':\s*'([^']{0,200})'", msg)
        code = re.search(r"Error code:\s*(\d+)", msg)
        if hit:
            print(f"    [{code.group(1) if code else '?'}] {hit.group(1)}")
        else:
            print(f"    {type(exc).__name__}: {msg[:220]}")
    finally:
        try:
            await cred.close()
        except Exception:
            pass
    return None


async def main():
    print("=" * 74)
    print(f"  model deployment = {MODEL}    resource = {resource}")
    print("=" * 74)

    clients = list_clients()
    print("\nClient classes available in this environment:")
    for c in clients:
        print(f"  - {c[0]}")
    if not clients:
        print("  NONE. Run: pip install agent-framework agent-framework-foundry")
        return

    winner = None
    for cls_name, cls, ep_kw, model_kw, cred_kw in clients:
        print(f"\n{'=' * 74}\n{cls_name}\n{'=' * 74}")
        for label, ep in ENDPOINTS:
            if not ep:
                continue
            print(f"\n  {label}\n    {ep}")
            got = await attempt(cls_name, cls, ep_kw, model_kw, cred_kw, label, ep)
            if got:
                winner = got
                break
        if winner:
            break

    print("\n" + "=" * 74)
    if winner:
        ep, cls_name = winner
        print(f"  WORKING COMBINATION: {cls_name}")
        print(f"  AZURE_AI_PROJECT_ENDPOINT={ep}")
    else:
        print("  Nothing worked. Send this whole output - the message text on each")
        print("  attempt says which knob is wrong.")
    print("=" * 74 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
