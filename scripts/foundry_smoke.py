"""Foundry smoke test (decision 2): can this account call its models, and how fast?

``uv run --extra agents python scripts/foundry_smoke.py``

Reads ``.env`` (git-ignored). Auth is keyless: the az login or managed identity, through
``DefaultAzureCredential``. Prints the model each deployment answers as, the region, the
deployment's capacity and the account quota (from the az CLI), and latency over three calls.
Never prints endpoints or tokens.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
SCOPE = "https://cognitiveservices.azure.com/.default"
API_VERSION = "2024-12-01-preview"


def load_env(path: Path = ENV) -> None:
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def az(*args: str) -> list | dict | None:
    try:
        cmd = ["az", *args, "-o", "json"]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return json.loads(out.stdout)


def quota() -> dict[str, tuple[float, float]]:
    """Deployment name -> (capacity in thousands of tokens per minute, account limit)."""
    rg, name, loc = (os.environ[k] for k in ("AZURE_RESOURCE_GROUP", "AZURE_AI_RESOURCE",
                                              "AZURE_LOCATION"))  # fmt: skip
    deployments = az("cognitiveservices", "account", "deployment", "list", "-g", rg, "-n", name)
    usage = az("cognitiveservices", "usage", "list", "-l", loc) or []
    limits = {u["name"]["value"]: u["limit"] for u in usage}
    out = {}
    for d in deployments or []:
        model, sku = d["properties"]["model"]["name"], d["sku"]["name"]
        key = f"OpenAI.{sku}.{model.replace('gpt-4.1', 'gpt4.1')}"
        out[d["name"]] = (d["sku"]["capacity"], limits.get(key, float("nan")))
    return out


def main() -> int:
    load_env()
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    token = get_bearer_token_provider(
        DefaultAzureCredential(exclude_interactive_browser_credential=True), SCOPE
    )
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token,
        api_version=API_VERSION,
        timeout=60,
    )
    caps = quota()
    print(f"region {os.environ['AZURE_LOCATION']}")
    failed = False
    models = [os.environ["MODEL_MAIN"], os.environ.get("MODEL_FAST")]
    for deployment in dict.fromkeys(filter(None, models)):
        times, model, tokens = [], None, 0
        try:
            for _ in range(3):
                start = time.perf_counter()
                r = client.chat.completions.create(
                    model=deployment,
                    messages=[{"role": "user", "content": "Reply with the single word: ready"}],
                    max_completion_tokens=400,
                )
                times.append(time.perf_counter() - start)
                model, tokens = r.model, tokens + r.usage.total_tokens
                answer = (r.choices[0].message.content or "").strip()
        except Exception as e:  # report and go on to the next deployment
            print(f"{deployment}: FAILED {type(e).__name__}: {str(e)[:200]}")
            failed = True
            continue
        cap, limit = caps.get(deployment, (float("nan"), float("nan")))
        print(
            f"{deployment}: model {model}, answer {answer!r}, latency median "
            f"{statistics.median(times):.2f} s (min {min(times):.2f}, max {max(times):.2f}), "
            f"{tokens} tokens in 3 calls; deployed {cap:g}k tokens/min of a {limit:g}k quota"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
