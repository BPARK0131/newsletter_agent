---
title: ASPA Is Live. Can You See It Working?
source_id: ripe_labs
source_name: ripe_labs
source_url: https://labs.ripe.net/author/ritesh-mukherjee/aspa-is-live-can-you-see-it-working/
source_type: rss
origin: curated_source
domain: labs.ripe.net
trust_level: high
category: IP Security
status: used
bias_risk: low
bias_note: 벤더 홍보보다 ASPA 검증 가시성 문제와 표준 기반 도구 소개가 중심이며, 과장된 성능 주장보다는 기술적 한계와 적용 맥락을
  설명합니다.
published_at: 2026-07-02 11:20
collected_at: '2026-07-02'
reviewed_at: '2026-07-02'
importance_score: 4
review_score: 0.8
hitl_route: approval_pending
topic_tags:
- aspa
- rpki
- rov
- bmp
- route_leak
- prefix_hijack
- bgp
- rtr
recollect_required: false
review_required: false
is_published: false
pipeline_status: approved
approved_at: '2026-07-02'
used_in_issue: '2026-07-02'
---

# 요약

ASPA 객체와 RTR v2 지원이 이미 가능하지만, 운영자가 실제 네트워크에서 ASPA가 무엇을 탐지하는지 보기 어렵다는 가시성 문제가 핵심으로 제기됩니다. 글은 과거 Pakistan Telecom, Rostelecom, Telegram 관련 사건을 예로 들어 기존 ROV만으로는 프리픽스 하이재킹과 라우트 유출을 모두 막기 어렵다고 설명합니다. 이를 보완하기 위해 BMP 피드와 RTR 검증기를 연결해 ASPA 검증 결과를 관찰하는 오픈소스 도구 RAVEN을 소개합니다. 또한 ASPA 커버리지, 오탐 여부, 배포 의사결정에 유용한 출력이 무엇인지 운영자 피드백을 요청합니다.

# 핵심 포인트

- ASPA 객체는 ARIN과 RIPE NCC에서 등록 가능하며, 검증기는 RTR v2를 지원합니다.
- ROV는 원점 하이재킹에는 효과적이지만, 라우트 유출은 별도로 탐지하기 어렵습니다.
- BMP 피드 기반으로 ASPA 검증 결과를 가시화하는 도구 RAVEN이 오픈소스로 공개되었습니다.
- RAVEN은 차단이 아니라 관찰과 신호 제공에 초점을 둔 ASPA 검증 도구입니다.
- 운영 환경에서 ASPA 커버리지와 오탐 여부를 검증하는 데이터가 향후 채택에 중요합니다.

# 뉴스레터 헤드라인

ASPA 검증 가시화 도구 RAVEN 공개

# 원문 링크

https://labs.ripe.net/author/ritesh-mukherjee/aspa-is-live-can-you-see-it-working/