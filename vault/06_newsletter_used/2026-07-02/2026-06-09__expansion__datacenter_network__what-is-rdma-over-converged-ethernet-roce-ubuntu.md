---
title: What is RDMA over Converged Ethernet (RoCE)? - Ubuntu
source_id: expansion/datacenter_network
source_name: expansion/datacenter_network
source_url: https://ubuntu.com/blog/what-is-rdma-over-converged-ethernet-roce
source_type: tavily
origin: open_web_search
domain: ubuntu.com
trust_level: medium
category: DataCenter Network
status: used
bias_risk: medium
bias_note: Canonical, Ubuntu, silicon vendors, switch manufacturers, ecosystem partners
  등 특정 생태계와 제품군을 긍정적으로 강조하는 표현이 있어 벤더 관점이 일부 섞여 있습니다.
published_at: 2026-07-02 11:20
collected_at: 2026-07-02 10:56
reviewed_at: '2026-07-02'
importance_score: 4
review_score: 0.8
hitl_route: approval_pending
topic_tags:
- rdma
- roce
- ecmp
- ecn
- dcb
- dcqcn
- pfc
- ai_fabric
- hpc
recollect_required: false
review_required: true
is_published: false
discovery_score: 4
discovery_reasons:
- recent_30d(+1)
- title_keywords(+2):ethernet,roce
- body_keywords(+2):4
- article_url(+1)
- long_body(+1)
- normalized(7→4/5)
pipeline_status: approved
approved_at: '2026-07-02'
used_in_issue: '2026-07-02'
---

# 요약

RoCE는 Ethernet 위에서 RDMA 성능을 활용하기 위한 기술이며, 대규모 AI/HPC 트래픽에서는 부하 분산과 혼잡 제어가 핵심 과제로 제시됩니다.
본문은 ECMP 해시가 동기화된 대형 플로우를 고르게 분산하지 못해 일부 링크에 혼잡이 집중될 수 있다고 설명합니다.
이를 완화하기 위해 ECN, DCB, DCQCN 같은 혼잡 제어 메커니즘이 사용되며, 패킷 마킹과 우선순위 제어로 송신 속도를 조절합니다.
또한 PFC는 특정 상황에서는 안정화에 도움이 되지만, 다른 상황에서는 불안정을 키울 수 있다고 언급합니다.

# 핵심 포인트

- ECMP 해시는 AI/HPC처럼 동기화된 트래픽에서 부하를 고르게 나누지 못할 수 있음
- ECN은 큐가 가득 차기 전에 패킷을 표시해 수신자·송신자가 점진적으로 대응하게 함
- DCB는 트래픽 클래스를 분리하고 우선순위를 부여하는 메커니즘임
- DCQCN은 혼잡 신호를 이용해 송신 속도를 동적으로 조절함
- PFC는 상황에 따라 안정화와 불안정화 양쪽 영향을 모두 가질 수 있음

# 뉴스레터 헤드라인

RoCE와 ECN DCB DCQCN 혼잡 제어

# 원문 링크

https://ubuntu.com/blog/what-is-rdma-over-converged-ethernet-roce