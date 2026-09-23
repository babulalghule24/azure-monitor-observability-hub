"""Run this BEFORE step 1. It checks your setup and explains failures in plain English.

    python src/_preflight.py

Four checks, in the order things actually break:
  1. Environment variables present and well-formed
  2. Entra ID credential can get a token
  3. The Foundry client builds
  4. A minimal model call succeeds (no tools, no orchestration)

If check 4 passes, every step in this lab will run.
"""

import asyncio
import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()

OK, BAD, WARN = "  [OK]  ", "  [FAIL]", "  [WARN]"


def fail(msg: str, fix: str) -> None:
    print(f"{BAD} {msg}")
    print(f"\n  HOW TO FIX:\n{fix}\n")
    sys.exit(1)


def check_env() -> tuple[str, str]:
    print("\n1. ENVIRONMENT ------------------------------------------------------")

    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip()
    model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "").strip()

    if not endpoint:
        fail("AZURE_AI_PROJECT_ENDPOINT is not set.",
             "  Copy .env.example to .env and fill in your Foundry project endpoint.")

    print(f"{OK} AZURE_AI_PROJECT_ENDPOINT = {endpoint}")

    if "/api/projects/" not in endpoint:
        print(f"{WARN} That endpoint has no '/api/projects/<name>' path segment.")
        print("         A bare resource URL authenticates but then fails on the call.")
        print("         Expected shape:")
        print("           https://<resource>.services.ai.azure.com/api/projects/<project-name>")
        print("         Find it in the Foundry portal: your project -> Overview -> "
              "'Azure AI Foundry project endpoint'.\n")

    if not model:
        fail("AZURE_AI_MODEL_DEPLOYMENT_NAME is not set.",
             "  Set it to your DEPLOYMENT name (not the model name).\n"
             "  Foundry portal -> your project -> Models + endpoints -> the Name column.")

    print(f"{OK} AZURE_AI_MODEL_DEPLOYMENT_NAME = {model}")
    print("         ^ this must match the DEPLOYMENT name in Models + endpoints,")
    print("           which is often not the same as the model name.")
    return endpoint, model


async def check_credential():
    print("\n2. CREDENTIAL -------------------------------------------------------")
    from azure.identity.aio import AzureCliCredential, DefaultAzureCredential

    from common import get_credential
    tenant = os.environ.get("AZURE_TENANT_ID", "").strip()
    cred = get_credential()
    print(f"{OK} Using {type(cred).__name__}")
    if tenant:
        print(f"{OK} Tenant pinned to {tenant}")
    else:
        print(f"{WARN} AZURE_TENANT_ID not set. If you are signed in to more than one")
        print("         Entra directory, the token may come from the wrong one and you")
        print("         will see: 'Token tenant <guid> does not match resource tenant.'")

    try:
        token = await cred.get_token("https://ai.azure.com/.default")
        print(f"{OK} Got a token (expires in "
              f"{int(token.expires_on - __import__('time').time())}s)")
    except Exception as exc:
        fail(f"Could not get a token: {type(exc).__name__}: {exc}",
             "  Run:  az login\n"
             "  If you have several accounts, force the CLI credential:\n"
             "    PowerShell:  $env:LAB_USE_CLI_CREDENTIAL=1\n"
             "    bash:        export LAB_USE_CLI_CREDENTIAL=1")
    return cred


def check_client():
    print("\n3. FOUNDRY CLIENT ---------------------------------------------------")
    try:
        from common import get_client, sdk_flavour
    except ImportError as exc:
        fail(f"Could not import common.py: {exc}",
             "  Run from the repo root:  python src/_preflight.py\n"
             "  And check:  python src/_doctor.py")

    print(f"{OK} SDK: {sdk_flavour()}")
    try:
        client = get_client()
    except Exception as exc:
        fail(f"Client construction failed: {type(exc).__name__}: {exc}",
             "  Run:  python src/_doctor.py\n"
             "  If FoundryChatClient is missing:  pip install agent-framework-foundry")
    print(f"{OK} Client built")
    return client


async def check_call(client, model: str):
    print("\n4. MODEL CALL -------------------------------------------------------")
    print("     Sending a minimal prompt (no tools, no orchestration)...")

    from common import make
    agent = make(client, "Preflight", "Reply with exactly the word: pong")

    try:
        result = await agent.run("ping")
    except Exception as exc:
        diagnose(exc, model)
        return

    print(f"{OK} Model responded: {str(result).strip()[:120]}")
    print("\n" + "=" * 70)
    print("  ALL CHECKS PASSED. Run:  python src/step1_signal_agent.py")
    print("=" * 70 + "\n")


def diagnose(exc: Exception, model: str) -> None:
    """Turn an SDK traceback into a sentence you can act on."""
    text = f"{type(exc).__name__}: {exc}".lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)

    print(f"{BAD} The call failed.")
    print(f"\n  Raw error: {type(exc).__name__}: {exc}\n")
    print("  MOST LIKELY CAUSE:\n")

    if "does not match resource tenant" in text or "token tenant" in text:
        print("  * WRONG TENANT. Your token came from a different Entra directory than")
        print("    the one that owns the Foundry resource. Common on corporate/AVD")
        print("    machines signed in to more than one directory.")
        print("\n    Find the owning tenant:")
        print("      az account list --query \"[?id=='<your-sub-id>'].{sub:name, tenant:tenantId}\" -o table")
        print("    Then:")
        print("      az login --tenant <TENANT_ID>")
        print("      az account set --subscription <SUB_ID>")
        print("    And add to .env:")
        print("      AZURE_TENANT_ID=<TENANT_ID>")
        print("      LAB_USE_CLI_CREDENTIAL=1")

    elif status in (401, 403) or "permission" in text or "unauthor" in text or "forbidden" in text:
        print("  * RBAC. You authenticated, but your account has no role on the project.")
        print("    Foundry portal -> your project -> Access control (IAM) -> Add role")
        print("    assignment -> 'Azure AI User' (or Contributor) -> your account.")
        print("    Role changes can take a few minutes to take effect.")

    elif status == 404 or "not found" in text or "deploymentnotfound" in text:
        print(f"  * The deployment '{model}' does not exist in this project.")
        print("    Foundry portal -> Models + endpoints -> copy the exact Name column value")
        print("    into AZURE_AI_MODEL_DEPLOYMENT_NAME. It is often NOT the model name.")
        print("    Also confirm the endpoint ends with /api/projects/<your-project>.")

    elif "responses" in text or "unsupported" in text or "not supported" in text or status == 400:
        print("  * The deployment may not support the Responses API, which this SDK uses.")
        print("    Deploy a current gpt-4o or gpt-4o-mini in your project and point")
        print("    AZURE_AI_MODEL_DEPLOYMENT_NAME at it. Older deployments and some model")
        print("    versions only support Chat Completions.")

    elif status == 429 or "rate" in text or "quota" in text:
        print("  * Rate limited or out of quota on that deployment.")
        print("    Raise the TPM quota in Models + endpoints, or wait and retry.")

    elif "getaddrinfo" in text or "connect" in text or "ssl" in text or "timeout" in text:
        print("  * Network. DNS, proxy or TLS interception is blocking the call.")
        print("    Check corporate proxy settings and that the endpoint host resolves.")

    else:
        print("  * Not a pattern I recognise. Full traceback below - the LAST few lines")
        print("    are the ones that matter.")
        print()
        traceback.print_exc()

    print()
    sys.exit(1)


async def main():
    print("\n" + "=" * 70)
    print("  SfMC Operations Desk - preflight check")
    print("=" * 70)

    endpoint, model = check_env()
    await check_credential()
    client = check_client()
    await check_call(client, model)


if __name__ == "__main__":
    asyncio.run(main())
