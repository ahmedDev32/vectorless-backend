import json

import requests
from django.conf import settings

# One pooled session per process: reuses TCP + TLS connections to OpenRouter
# across requests instead of paying a fresh handshake on every LLM call.
_session = requests.Session()


class LLMError(RuntimeError):
    pass


class OpenRouterClient:
    """Thin JSON-mode chat client for OpenRouter."""

    def __init__(self, model: str | None = None, timeout: float = 60.0):
        self.api_key = settings.OPENROUTER_API_KEY
        self.api_base = settings.OPENROUTER_API_BASE
        self.model = model or settings.OPENROUTER_MODEL
        self.timeout = timeout

    def chat_json(self, messages: list[dict]) -> dict:
        """Send a chat completion request and parse the reply as JSON."""
        if not self.api_key:
            raise LLMError('OPENROUTER_API_KEY is not configured.')

        payload = {
            'model': self.model,
            'messages': messages,
            'response_format': {'type': 'json_object'},
        }
        try:
            response = _session.post(
                f'{self.api_base}/chat/completions',
                json=payload,
                timeout=self.timeout,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'HTTP-Referer': settings.OPENROUTER_SITE_URL or '',
                    'X-Title': settings.OPENROUTER_SITE_NAME or '',
                },
            )
            response.raise_for_status()
            body = response.json()
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise LLMError(f'OpenRouter request failed ({exc.response.status_code}): {detail}') from exc
        except requests.RequestException as exc:
            raise LLMError(f'OpenRouter request failed: {exc}') from exc

        try:
            content = body['choices'][0]['message']['content']
        except (KeyError, IndexError) as exc:
            raise LLMError(f'Unexpected OpenRouter response shape: {body}') from exc

        try:
            return json.loads(content)
        except ValueError as exc:
            raise LLMError(f'LLM did not return valid JSON: {content}') from exc
