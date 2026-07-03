---
title: Notes from NANOG 97
source_id: apnic_blog
source_name: apnic_blog
source_url: https://blog.apnic.net/2026/06/29/notes-from-nanog-97/
source_type: rss
origin: curated_source
domain: blog.apnic.net
trust_level: high
category: AI Network/Autonomous Network
status: review
bias_risk: medium
bias_note: 기사에는 거대한 투자액과 버블 가능성에 대한 저자의 경고적·감정적 표현이 포함되어 있어 과장이나 주관적 해석이 섞여 있음.
published_at: Mon, 29 Ju
collected_at: '2026-07-03'
reviewed_at: '2026-07-03'
importance_score: 4
review_score: 0.8
hitl_route: approval_pending
topic_tags:
- ai_fabric
- llms
- gpu
- data_center
- tls13
- https
- ssh
- netdevops
- edge_proxy
- nanog
recollect_required: false
review_required: true
is_published: false
---

# 요약

NANOG 97에서는 대규모 LLM 구축을 위한 GPU 중심 데이터센터와 AI 도구의 네트워크 운영 적용이 주요 의제로 다뤄졌다. AI 학습·추론 워크로드가 데이터센터 네트워크에 새로운 지연·대역폭 부담을 주며, 이에 따른 인프라 설계 변화가 필요하다고 지적되었다. 대규모 장치 자동화 환경에서는 TLS 1.3을 활용한 HTTPS-대-SSH 엣지 프록시가 연결 수립 지연을 줄이는 방안으로 제시되었다.

# 핵심 포인트

- 대규모 LLM·GPU 배치는 데이터센터 네트워크에 높은 대역폭·지연 민감성을 유발하여 설계 변경을 요구함
- 저자는 2026년 미연방 수준의 대규모 투자(기사 내 수치 제시)를 언급하며 투자 붐과 잠재적 버블을 경고함
- TLS 1.3은 연결 수립을 3 RTT로 단축시키며, 이를 이용한 HTTPS와 SSH 간 엣지 프록시가 대규모 장치 자동화에서 유용할 수 있음
- SSH 기반 장치 관리에서는 수천~수만 대 규모에서 RTT 오버헤드가 문제되며, HTTPS→SSH 프록시가 지연 개선 수단으로 고려됨

# 뉴스레터 헤드라인

AI LLM·GPU 데이터센터와 TLS 1.3 HTTPS→SSH 프록시

# 원문 링크

https://blog.apnic.net/2026/06/29/notes-from-nanog-97/