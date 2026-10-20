"""Models on Microsoft Foundry through Agent Framework (decision 2; ``scripts/foundry_smoke.py``).

Settings come from ``.env`` (git-ignored): ``AZURE_OPENAI_ENDPOINT`` and ``MODEL_MAIN`` (every
agent and the Verifier's LLM pass). ``MODEL_FAST`` is only compared in
``scripts/foundry_smoke.py``: it passed "He looks absolutely shattered" (decision 18), so
nothing uses it. Auth is keyless: the az login or a managed
identity through ``DefaultAzureCredential``. Nothing here prints endpoints or tokens.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

ENV = Path(__file__).resolve().parents[3] / ".env"
API_VERSION = "2024-12-01-preview"


def load_env(path: Path = ENV) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def available() -> bool:
    load_env()
    return bool(os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("MODEL_MAIN"))


@cache
def _credential():
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


@cache
def client(model: str):
    from agent_framework.openai import OpenAIChatCompletionClient

    load_env()
    return OpenAIChatCompletionClient(
        model=model,
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        credential=_credential(),
        api_version=API_VERSION,
    )


def model(role: str = "main") -> str:
    """The deployment for ``role``; every role uses MODEL_MAIN (decision 18)."""
    load_env()
    return os.environ["MODEL_MAIN"]


def agent(name: str, instructions: str, role: str = "main", tools: Any = None):
    """An Agent Framework agent on the Foundry deployment for ``role``."""
    from agent_framework import Agent

    return Agent(client(model(role)), instructions, name=name, tools=tools)
