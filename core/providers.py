"""
QA Agent - Provedores de IA Multiplos
======================================

Suporte a:
- Anthropic Claude
- OpenAI GPT-4 / GPT-4o
- Google Gemini
Permite alternar entre provedores dinamicamente.
"""

import os
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Classe base abstrata para provedores de IA"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = "base"

    @abstractmethod
    def create_message(self, messages: List[Dict], tools: List[Dict] = None,
                       system: str = "", max_tokens: int = 4096) -> Any:
        pass

    @abstractmethod
    def parse_response(self, response: Any) -> Dict:
        pass


class AnthropicProvider(AIProvider):
    """Provedor Anthropic Claude"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "anthropic"
        self.api_key = config.get("api_key", os.getenv("ANTHROPIC_API_KEY", ""))
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def create_message(self, messages: List[Dict], tools: List[Dict] = None,
                       system: str = "", max_tokens: int = 4096) -> Any:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        return self.client.messages.create(**kwargs)

    def parse_response(self, response: Any) -> Dict:
        result = {
            "content": [],
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": getattr(response, 'usage', {}).get('input_tokens', 0),
                "output_tokens": getattr(response, 'usage', {}).get('output_tokens', 0)
            }
        }
        for block in response.content:
            if block.type == "text":
                result["content"].append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                result["content"].append({
                    "type": "tool_use",
                    "name": block.name,
                    "input": block.input,
                    "id": block.id
                })
        return result


class OpenAIProvider(AIProvider):
    """Provedor OpenAI GPT"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "openai"
        self.api_key = config.get("api_key", os.getenv("OPENAI_API_KEY", ""))
        self.model = config.get("model", "gpt-4o")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def create_message(self, messages: List[Dict], tools: List[Dict] = None,
                       system: str = "", max_tokens: int = 4096) -> Any:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["messages"].insert(0, {"role": "system", "content": system})
        if tools:
            openai_tools = []
            for tool in tools:
                if tool.get("type") == "custom":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("input_schema", {})
                        }
                    })
            if openai_tools:
                kwargs["tools"] = openai_tools
        return self.client.chat.completions.create(**kwargs)

    def parse_response(self, response: Any) -> Dict:
        result = {
            "content": [],
            "stop_reason": response.choices[0].finish_reason if response.choices else "stop",
            "usage": {
                "input_tokens": getattr(response, 'usage', {}).get('prompt_tokens', 0),
                "output_tokens": getattr(response, 'usage', {}).get('completion_tokens', 0)
            }
        }
        msg = response.choices[0].message
        if msg.content:
            result["content"].append({"type": "text", "text": msg.content})
        if msg.tool_calls:
            for tc in msg.tool_calls:
                result["content"].append({
                    "type": "tool_use",
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                    "id": tc.id
                })
        return result


class GeminiProvider(AIProvider):
    """Provedor Google Gemini"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "gemini"
        self.api_key = config.get("api_key", os.getenv("GEMINI_API_KEY", ""))
        self.model = config.get("model", "gemini-2.0-flash")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def create_message(self, messages: List[Dict], tools: List[Dict] = None,
                       system: str = "", max_tokens: int = 4096) -> Any:
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] in ("user", "tool_result") else "model"
            content = msg.get("content", "")
            if isinstance(content, list):
                texts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            texts.append(part["text"])
                        elif part.get("type") == "tool_result":
                            texts.append(str(part.get("content", "")))
                    else:
                        texts.append(str(part))
                content = "\n".join(texts)
            gemini_messages.append({"role": role, "parts": [content]})

        genai_tools = []
        for tool in (tools or []):
            if tool.get("type") == "custom":
                genai_tools.append({
                    "function_declarations": [{
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }]
                })

        kwargs = {
            "contents": gemini_messages,
        }
        if genai_tools:
            kwargs["tools"] = genai_tools
        if system:
            kwargs["system_instruction"] = system
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": 0.7,
        }
        kwargs["generation_config"] = generation_config
        return self.client.generate_content(**kwargs)

    def parse_response(self, response: Any) -> Dict:
        result = {
            "content": [],
            "stop_reason": "stop" if response.candidates else "error",
            "usage": {"input_tokens": 0, "output_tokens": 0}
        }
        try:
            if hasattr(response, 'usage_metadata'):
                result["usage"] = {
                    "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                    "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0)
                }
            text = response.text if hasattr(response, 'text') else str(response)
            if text:
                result["content"].append({"type": "text", "text": text})
        except Exception as e:
            result["content"].append({"type": "text", "text": f"Erro ao processar resposta: {e}"})
        return result


PROVIDER_REGISTRY = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}

PROVIDER_MODELS = {
    "anthropic": {
        "claude-3-haiku-20240307": "Haiku (Rapido)",
        "claude-sonnet-4-20250514": "Sonnet (Equilibrado)",
        "claude-opus-4-20250514": "Opus (Poderoso)",
    },
    "openai": {
        "gpt-4o-mini": "GPT-4o Mini (Rapido)",
        "gpt-4o": "GPT-4o (Equilibrado)",
        "gpt-4-turbo": "GPT-4 Turbo (Poderoso)",
    },
    "gemini": {
        "gemini-2.0-flash": "Gemini 2.0 Flash (Rapido)",
        "gemini-2.0-pro": "Gemini 2.0 Pro (Equilibrado)",
    }
}


def get_provider(provider_name: str = "anthropic", config: Dict[str, Any] = None) -> AIProvider:
    """Factory: retorna instancia do provedor"""
    provider_class = PROVIDER_REGISTRY.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Provedor desconhecido: {provider_name}. Disponiveis: {list(PROVIDER_REGISTRY.keys())}")
    return provider_class(config or {})


def check_provider_key(provider_name: str) -> bool:
    """Verifica se a chave de API do provedor esta configurada"""
    env_keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    key = env_keys.get(provider_name.lower())
    if key and os.getenv(key):
        return True
    return False
