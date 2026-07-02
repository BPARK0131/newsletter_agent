"""한국어 네트워크 기술 용어 출력 정규화."""

from __future__ import annotations

import re

# (pattern, replacement) — 순서 중요: 구체적 패턴을 먼저
_NETWORK_TERM_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    # broken hijack transliterations
    (re.compile(r"BGP\s*히\s*[iI]\s*jack(?:ing)?", re.I), "BGP 하이재킹"),
    (re.compile(r"BGP\s*히\s*재킹", re.I), "BGP 하이재킹"),
    (re.compile(r"BGP\s*히jack(?:ing)?", re.I), "BGP 하이재킹"),
    (re.compile(r"BGP\s*hijack(?:ing)?", re.I), "BGP 하이재킹"),
    (re.compile(r"BGP\s*히재킹", re.I), "BGP 하이재킹"),
    (re.compile(r"히\s*[iI]\s*jack(?:ing)?", re.I), "하이재킹"),
    (re.compile(r"히\s*재킹", re.I), "하이재킹"),
    (re.compile(r"히jack(?:ing)?", re.I), "하이재킹"),
    (re.compile(r"히재킹", re.I), "하이재킹"),
    (re.compile(r"\bhijack(?:ing)?\b", re.I), "하이재킹"),
    # route leak
    (re.compile(r"route\s*leak(?:s|age)?", re.I), "라우트 유출"),
    (re.compile(r"라우트\s*리크", re.I), "라우트 유출"),
    # prefix hijack
    (re.compile(r"prefix\s*hijack(?:ing)?", re.I), "프리픽스 하이재킹"),
)

_MIXED_SCRIPT_RE = re.compile(
    r"[\uac00-\ud7a3]+[a-zA-Z]{2,}|[a-zA-Z]{2,}[\uac00-\ud7a3]+"
)


def normalize_network_terms(text: str) -> str:
    """LLM 출력의 네트워크 용어·깨진 한영 혼용을 일관된 한국어로 정규화."""
    if not text:
        return ""
    t = str(text)
    for pattern, repl in _NETWORK_TERM_RULES:
        t = pattern.sub(repl, t)
    t = re.sub(r"(하이재킹\s+){2,}", "하이재킹 ", t)
    t = re.sub(r"(BGP\s+하이재킹\s+){2,}", "BGP 하이재킹 ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def has_mixed_script_artifact(text: str) -> bool:
    """한글+영문이 붙은 조어(예: 히ijack) 잔존 여부."""
    if not text:
        return False
    return bool(_MIXED_SCRIPT_RE.search(text))
