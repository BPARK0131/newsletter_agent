"""LLM API 키·게이트웨이 연결 진단."""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage

from ipn_agent.core.openai_chat_llm import (
    create_chat_openai,
    resolve_openai_api_base,
    resolve_openai_api_key,
    resolve_openai_model,
)


def mask_secret(value: str, *, visible: int = 4) -> str:
    text = (value or "").strip()
    if not text:
        return "(미설정)"
    if len(text) <= visible * 2:
        return "*" * len(text)
    return f"{text[:visible]}...{text[-visible:]}"


@dataclass
class LlmConfigSnapshot:
    api_key: str
    api_base: str | None
    model: str
    api_key_source: str = "OPENAI_API_KEY"
    model_source: str = "default"

    def as_display_dict(self) -> dict[str, str]:
        return {
            "api_key": mask_secret(self.api_key),
            "api_base": self.api_base or "(미설정, OpenAI 직접 호출)",
            "model": self.model,
            "api_key_source": self.api_key_source,
            "model_source": self.model_source,
        }


def snapshot_llm_config() -> LlmConfigSnapshot:
    api_key = resolve_openai_api_key()
    api_base = resolve_openai_api_base()

    model = resolve_openai_model()
    model_source = "default"
    if os.environ.get("OPENAI_CHAT_MODEL", "").strip():
        model_source = "OPENAI_CHAT_MODEL"
    elif os.environ.get("OPENAI_MODEL_PRIMARY", "").strip():
        model_source = "OPENAI_MODEL_PRIMARY"

    return LlmConfigSnapshot(
        api_key=api_key,
        api_base=api_base,
        model=model,
        model_source=model_source,
    )


@dataclass
class LlmTestResult:
    ok: bool
    mode: str
    latency_ms: int | None = None
    response_preview: str = ""
    error_type: str = ""
    error_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def _preview_text(text: str, limit: int = 200) -> str:
    cleaned = (text or "").strip().replace("\n", " ")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def test_llm_invoke(
    *,
    streaming: bool = False,
    prompt: str = "Reply with exactly: OK",
    max_completion_tokens: int = 256,
    timeout: float = 60.0,
) -> LlmTestResult:
    """단일 LLM 호출로 API 키·게이트웨이·모델명을 검증한다."""
    import time

    mode = "stream" if streaming else "invoke"
    messages = [HumanMessage(content=prompt)]

    try:
        llm = create_chat_openai(
            streaming=streaming,
            max_completion_tokens=max_completion_tokens,
            timeout=timeout,
            max_retries=1,
        )
    except ValueError as exc:
        return LlmTestResult(
            ok=False,
            mode=mode,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    started = time.perf_counter()
    try:
        if streaming:
            chunks: list[str] = []
            for chunk in llm.stream(messages):
                if chunk.content:
                    chunks.append(str(chunk.content))
            text = "".join(chunks)
        else:
            response = llm.invoke(messages)
            text = str(getattr(response, "content", response))

        latency_ms = int((time.perf_counter() - started) * 1000)
        preview = _preview_text(text)
        if not preview:
            return LlmTestResult(
                ok=False,
                mode=mode,
                latency_ms=latency_ms,
                error_type="EmptyResponse",
                error_message="LLM 응답 본문이 비어 있습니다.",
            )
        return LlmTestResult(
            ok=True,
            mode=mode,
            latency_ms=latency_ms,
            response_preview=preview,
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LlmTestResult(
            ok=False,
            mode=mode,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
            error_message=str(exc),
            details={"traceback": traceback.format_exc()},
        )


def run_llm_api_tests(*, include_stream: bool = False) -> dict[str, Any]:
    """설정 스냅샷 + invoke(+선택 stream) 테스트 결과."""
    config = snapshot_llm_config()
    invoke_result = test_llm_invoke(streaming=False)
    stream_result: LlmTestResult | None = None
    if include_stream:
        stream_result = test_llm_invoke(streaming=True)

    ok = invoke_result.ok and (stream_result.ok if stream_result else True)
    return {
        "ok": ok,
        "config": config.as_display_dict(),
        "invoke": invoke_result,
        "stream": stream_result,
    }
