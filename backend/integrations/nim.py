"""NIM-compatible structured proposal boundary. Live service unverified.

A model proposes bounded experiments; it cannot execute arbitrary tools. A caller
must inspect and approve the exact proposal hash before execution. No endpoint
or credentials are selected implicitly, and credentials are never persisted.
"""
import hashlib
import json
from urllib.parse import urlparse

import httpx
from backend.experiments.models import ExperimentRequest


class NimPlanner:
    def __init__(self, endpoint: str, model: str, api_key: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        url = urlparse(endpoint)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Endpoint must not contain credentials, query or fragment")
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1"}):
            raise ValueError("Use HTTPS, or HTTP on localhost for a local NIM server")
        self.endpoint, self.model = endpoint.rstrip("/"), model
        self._key, self._transport = api_key, transport

    def propose(self, objective: str) -> ExperimentRequest:
        if not 1 <= len(objective) <= 4000:
            raise ValueError("Objective must be 1-4000 characters")
        headers = {"Authorization": f"Bearer {self._key}"} if self._key else {}
        with httpx.Client(timeout=30, transport=self._transport, follow_redirects=False) as client:
            response = client.post(self.endpoint + "/chat/completions", headers=headers, json={
                "model": self.model, "temperature": 0,
                "messages": [
                    {"role": "system", "content": "Propose a bounded warehouse experiment. Return JSON only matching this schema: " + json.dumps(ExperimentRequest.model_json_schema())},
                    {"role": "user", "content": objective}],
            })
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        return ExperimentRequest.model_validate_json(content)


def proposal_hash(proposal: ExperimentRequest) -> str:
    return hashlib.sha256(proposal.model_dump_json().encode()).hexdigest()


def require_approval(proposal: ExperimentRequest, approved_hash: str):
    if approved_hash != proposal_hash(proposal):
        raise ValueError("Approval must match the exact validated experiment proposal")
