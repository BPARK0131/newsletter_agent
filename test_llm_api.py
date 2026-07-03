"""LLM API 키·게이트웨이 연결 테스트 CLI.

review_script 등 전체 파이프라인 없이, API 키·base URL·모델명만 빠르게 검증합니다.

실행:
  python test_llm_api.py
  python test_llm_api.py --stream
  python test_llm_api.py --prompt "한 줄로 자기소개"

필수 .env:
  OPENAI_API_KEY=...

게이트웨이(LiteLLM/a15t 등) 사용 시 추가:
  OPENAI_API_BASE=https://your-gateway/v1
  OPENAI_CHAT_MODEL=azure/openai/gpt-4.1-mini-2025-04-14-gs

모델명 fallback:
  OPENAI_CHAT_MODEL → OPENAI_MODEL_PRIMARY → gpt-4o-mini
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

from ipn_agent.core.llm_api_test import (
    LlmTestResult,
    run_llm_api_tests,
    snapshot_llm_config,
    test_llm_invoke,
)
from ipn_agent.paths import ensure_vault_path_env


def _format_result(result: LlmTestResult) -> str:
    if result.ok:
        return (
            f"  [OK] {result.mode}: 성공 "
            f"({result.latency_ms}ms) - {result.response_preview}"
        )
    lines = [
        f"  [FAIL] {result.mode}: 실패 ({result.error_type})",
        f"     {result.error_message}",
    ]
    if result.latency_ms is not None:
        lines[0] = f"  [FAIL] {result.mode}: 실패 ({result.error_type}, {result.latency_ms}ms)"
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="LLM API 키·게이트웨이 연결 테스트")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="비스트리밍 성공 후 스트리밍 호출도 추가 검증",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly: OK",
        help="테스트용 사용자 프롬프트",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="결과를 JSON으로 출력",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="LLM 호출 타임아웃(초)",
    )
    args = parser.parse_args()

    load_dotenv()
    ensure_vault_path_env(quiet=True)

    if args.prompt != "Reply with exactly: OK":
        config = snapshot_llm_config()
        invoke = test_llm_invoke(
            streaming=False,
            prompt=args.prompt,
            timeout=args.timeout,
        )
        stream = (
            test_llm_invoke(streaming=True, prompt=args.prompt, timeout=args.timeout)
            if args.stream
            else None
        )
        payload = {
            "ok": invoke.ok and (stream.ok if stream else True),
            "config": config.as_display_dict(),
            "invoke": invoke,
            "stream": stream,
        }
    else:
        payload = run_llm_api_tests(include_stream=args.stream)
        if args.timeout != 60.0:
            payload["invoke"] = test_llm_invoke(timeout=args.timeout)
            if args.stream:
                payload["stream"] = test_llm_invoke(streaming=True, timeout=args.timeout)
            payload["ok"] = payload["invoke"].ok and (
                payload["stream"].ok if payload.get("stream") else True
            )

    if args.json:
        def _serialize(obj):
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return obj

        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_serialize))
        return 0 if payload["ok"] else 1

    print("=== LLM 연결 테스트 ===")
    print("설정:")
    for key, value in payload["config"].items():
        print(f"  {key}: {value}")

    print("\n결과:")
    print(_format_result(payload["invoke"]))
    if payload.get("stream"):
        print(_format_result(payload["stream"]))

    if payload["ok"]:
        print("\n[OK] LLM API 연결 정상")
        return 0

    print("\n[FAIL] LLM API 연결 실패 - OPENAI_API_KEY / OPENAI_API_BASE / 모델명을 확인하세요.")
    invoke = payload["invoke"]
    if invoke.details.get("traceback"):
        print("\n--- 상세 traceback ---")
        print(invoke.details["traceback"].rstrip())
    return 1


if __name__ == "__main__":
    sys.exit(main())
