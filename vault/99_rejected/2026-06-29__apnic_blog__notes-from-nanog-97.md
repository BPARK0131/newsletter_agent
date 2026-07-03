---
title: Notes from NANOG 97
source_id: apnic_blog
source_name: apnic_blog
source_url: https://blog.apnic.net/2026/06/29/notes-from-nanog-97/
source_type: rss
origin: curated_source
domain: blog.apnic.net
trust_level: high
category: NetDevOps
status: rejected
bias_risk: low
bias_note: ''
published_at: Mon, 29 Ju
collected_at: '2026-07-02'
reviewed_at: '2026-07-02'
importance_score: 3
review_score: 0.6
hitl_route: needs_human_review
topic_tags:
- ai_fabric
- data_center_network
- netdevops
- ssh
- tls1.3
recollect_required: false
review_required: false
is_published: false
pipeline_status: rejected
rejected_at: '2026-07-03'
---

# 요약

NANOG 97에서는 AI 학습·추론 워크로드가 데이터센터 네트워크 설계에 주는 부담과, 네트워크 운영에 AI 도구를 적용하는 사례가 논의됐다. 특히 GPU 중심의 대규모 데이터센터 투자와 그에 따른 네트워크 아키텍처 변화가 주요 화제로 다뤄졌다. 또한 SSH 기반 장비 관리의 연결 지연을 줄이기 위해 HTTPS over TLS 1.3와 SSH를 잇는 에지 프록시 접근법이 소개됐다. 대규모 장비 자동화 환경에서는 RTT 절감이 운영 효율에 큰 영향을 줄 수 있음을 강조했다.

# 핵심 포인트

- AI 학습·추론·에이전틱 워크로드가 데이터센터 네트워크에 새로운 부하를 유발
- GPU 클러스터를 위한 데이터센터 구축과 투자 규모가 크게 확대되고 있음
- SSH 연결 설정의 RTT 오버헤드를 줄이기 위한 HTTPS-to-SSH 에지 프록시 제안
- TLS 1.3 기반 HTTPS는 연결 성립을 더 적은 RTT로 완료할 수 있음
- 대규모 네트워크 자동화에서는 인증·채널 오픈 지연이 운영 효율의 핵심 변수

# 뉴스레터 헤드라인

AI 학습·추론과 TLS 1.3 SSH 에지 프록시

# 원문 링크

https://blog.apnic.net/2026/06/29/notes-from-nanog-97/