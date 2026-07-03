"""LangChain ChatOpenAI factory — LiteLLM/a15t 게이트웨이 호환."""

from __future__ import annotations

import os
from typing import Any, Iterable

from langchain_openai import ChatOpenAI


def resolve_openai_model(model: str | None = None) -> str:
    """모델명 우선순위: 인자 → OPENAI_CHAT_MODEL → OPENAI_MODEL_PRIMARY → 기본값."""
    if model and model.strip():
        return model.strip()
    for env_key in ("OPENAI_CHAT_MODEL", "OPENAI_MODEL_PRIMARY"):
        value = os.environ.get(env_key, "").strip()
        if value:
            return value
    return "gpt-4o-mini"


def resolve_openai_api_key(openai_api_key: str | None = None) -> str:
    key = (openai_api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
    if not key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return key


def resolve_openai_api_base(openai_api_base: str | None = None) -> str | None:
    base = (openai_api_base or os.environ.get("OPENAI_API_BASE", "")).strip()
    return base.rstrip("/") if base else None


def resolve_openai_temperature(temperature: float | None = None) -> float | None:
    """temperature 미설정 시 API 요청에 포함하지 않음 (모델 기본값 사용)."""
    if temperature is not None:
        return temperature
    raw = os.environ.get("OPENAI_TEMPERATURE", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def resolve_openai_max_completion_tokens(
    max_completion_tokens: int | None = None,
    *,
    default: int | None = None,
    env_name: str = "OPENAI_MAX_COMPLETION_TOKENS",
) -> int | None:
    if max_completion_tokens is not None:
        return max_completion_tokens
    raw = os.environ.get(env_name, "").strip()
    if raw:
        try:
            val = int(raw)
            return val if val > 0 else default
        except ValueError:
            pass
    return default


def resolve_openai_timeout(
    timeout: float | None = None,
    *,
    default: float = 120.0,
) -> float:
    if timeout is not None:
        return timeout
    raw = os.environ.get("OPENAI_TIMEOUT", "").strip()
    if raw:
        try:
            val = float(raw)
            return val if val > 0 else default
        except ValueError:
            pass
    return default


def create_chat_openai(
    *,
    model: str | None = None,
    openai_api_key: str | None = None,
    openai_api_base: str | None = None,
    temperature: float | None = None,
    max_completion_tokens: int | None = None,
    streaming: bool = False,
    timeout: float | None = None,
    max_retries: int | None = None,
    callbacks: Iterable[Any] | None = None,
    model_kwargs: dict[str, Any] | None = None,
    **extra: Any,
) -> ChatOpenAI:
    """
    프로젝트 공통 ChatOpenAI 생성.

    환경변수:
      - OPENAI_API_KEY (필수)
      - OPENAI_API_BASE (선택, LiteLLM/a15t 게이트웨이)
      - OPENAI_CHAT_MODEL 또는 OPENAI_MODEL_PRIMARY (모델명)
      - OPENAI_TEMPERATURE (선택, gpt-5 등 일부 모델은 0 미지원)
      - OPENAI_MAX_COMPLETION_TOKENS (선택)
      - OPENAI_TIMEOUT (선택, 초)
    """
    kwargs: dict[str, Any] = {
        "model": resolve_openai_model(model),
        "api_key": resolve_openai_api_key(openai_api_key),
        "streaming": streaming,
    }

    resolved_temperature = resolve_openai_temperature(temperature)
    if resolved_temperature is not None:
        kwargs["temperature"] = resolved_temperature

    base_url = resolve_openai_api_base(openai_api_base)
    if base_url:
        kwargs["base_url"] = base_url

    if max_completion_tokens is not None:
        kwargs["max_completion_tokens"] = max_completion_tokens
    if timeout is not None:
        kwargs["timeout"] = timeout
    if max_retries is not None:
        kwargs["max_retries"] = max_retries
    if callbacks is not None:
        kwargs["callbacks"] = list(callbacks)
    if model_kwargs:
        kwargs["model_kwargs"] = model_kwargs
    kwargs.update(extra)
    return ChatOpenAI(**kwargs)


def create_review_chat_openai(**extra: Any) -> ChatOpenAI:
    """기사 리뷰·bias 분류용 LLM (structured output, reasoning 모델 토큰 여유)."""
    return create_chat_openai(
        max_completion_tokens=resolve_openai_max_completion_tokens(default=4096),
        timeout=resolve_openai_timeout(default=120.0),
        max_retries=2,
        **extra,
    )
