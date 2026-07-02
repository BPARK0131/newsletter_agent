# IP Network Newsletter Vault

Obsidian에서 **Open folder as vault**로 이 폴더를 엽니다.

> 상세: [docs/vault-structure.md](../docs/vault-structure.md)

## 폴더 구조

```
vault/
├── 01_raw/                    수집 원문 (fetch + Tavily expansion)
│   ├── {source_id}/           APNIC, IETF, TM Forum 등
│   └── expansion/{category}/  Tavily quality gate 통과분 (별도 discovery 폴더 없음)
│
├── 02_review/                 LLM 리뷰 + HITL 검토 큐
├── 03_approved/               HITL 승인
├── 04_newsletter/
│   ├── draft/
│   ├── published/
│   └── ietf_radar.md          IETF Radar (기사 HITL 아님)
├── 05_newsletter_archive/
├── 06_newsletter_used/
├── registry/published_articles.json
└── 99_rejected/
```

> **Discovery는 vault 밖:** Tavily gate 제외·저점수 로그 → `mini pjt/logs/discovery/`  
> 통과분 raw만 `01_raw/expansion/`에 저장됩니다.

## Collect → Review 흐름

```
fetch (--source)     → 01_raw/{source_id}/
expansion_search     → quality gate → 01_raw/expansion/{category}/
review_script        → 01_raw/** → 02_review/
Streamlit 기사 검토  → 03_approved / 99_rejected
```

## 초기화

```bash
python reset_vault.py --phase 01    # raw만
python reset_vault.py --all         # vault Phase 전체
```

## 관련 문서

- [docs/vault-structure.md](../docs/vault-structure.md)
- [docs/setup-and-operations.md](../docs/setup-and-operations.md)
- [docs/newsletter-pipeline.md](../docs/newsletter-pipeline.md)
