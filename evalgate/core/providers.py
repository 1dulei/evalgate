"""
Model providers for EvalGate: MockProvider (offline/CI) and HttpLLMProvider (OpenAI/DeepSeek/Ollama).
"""
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class BaseProvider:
    def complete(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError


class MockProvider(BaseProvider):
    """
    Offline/CI Mock provider that supports scripted, regex, and simulated responses.
    """
    def __init__(self, overrides: Optional[Dict[str, str]] = None, default_response: str = "Standard AI Response"):
        self.overrides = overrides or {}
        self.default_response = default_response

    def complete(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Check overrides
        resp_text = None
        for key, val in self.overrides.items():
            if key.lower() in prompt.lower():
                resp_text = val
                break
        
        if resp_text is None:
            # Smart mock based on prompt cues
            if "json" in prompt.lower() or "schema" in prompt.lower():
                resp_text = json.dumps({"status": "success", "ticket_id": "TICK-8921", "refund_amount": 49.99, "reason": "damaged_goods"})
            elif "ignore previous" in prompt.lower() or "jailbreak" in prompt.lower() or "dan" in prompt.lower():
                # Defended against jailbreak
                resp_text = "I cannot comply with requests to bypass security policies or reveal system instructions."
            elif "calculate" in prompt.lower() or "sum" in prompt.lower():
                resp_text = "The calculated total is 42."
            else:
                resp_text = f"Processed request: {prompt[:50]}... Answer verified by knowledge base."

        latency = (time.perf_counter() - start) * 1000 + 45.0  # simulate ~45ms
        return {
            "content": resp_text,
            "latency_ms": round(latency, 2),
            "usage": {"prompt_tokens": len(prompt) // 4, "completion_tokens": len(resp_text) // 4}
        }


class HttpLLMProvider(BaseProvider):
    """
    Direct HTTP client for OpenAI-compatible APIs (OpenAI, DeepSeek, vLLM, Ollama).
    Uses standard library urllib to avoid third-party client bloat.
    """
    def __init__(self, api_base: str, api_key: str, model: str = "gpt-4o-mini", timeout: int = 30):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.api_base}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                latency = (time.perf_counter() - start) * 1000
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                return {
                    "content": content,
                    "latency_ms": round(latency, 2),
                    "usage": usage
                }
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return {
                "content": "",
                "latency_ms": round(latency, 2),
                "error": str(e)
            }
