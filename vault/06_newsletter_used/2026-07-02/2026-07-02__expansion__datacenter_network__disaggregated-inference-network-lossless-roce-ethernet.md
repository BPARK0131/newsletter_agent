---
title: Disaggregated Inference Network | Lossless RoCE Ethernet
source_id: expansion/datacenter_network
source_name: expansion/datacenter_network
source_url: https://hedgehog.cloud/disaggregated-inference
source_type: tavily
origin: open_web_search
domain: hedgehog.cloud
trust_level: medium
category: DataCenter Network
status: used
bias_risk: medium
bias_note: Hedgehog Fabric Controller와 Spectrum-X를 언급하며 선언형 제어, lossless, 무제한 확장성
  등을 강조하는 홍보성 표현이 포함되어 있음.
published_at: 2026-07-02 11:20
collected_at: 2026-07-02 10:56
reviewed_at: '2026-07-02'
importance_score: 4
review_score: 0.8
hitl_route: approval_pending
topic_tags:
- rocev2
- kubernetes
- qos
- bgp
- ecmp
- evpn
- vrf
- pfc
- ecn
- dcqcn
- prometheus
- grafana
recollect_required: false
review_required: true
is_published: false
discovery_score: 4
discovery_reasons:
- recent_7d(+2)
- title_keywords(+2):ethernet,roce
- body_keywords(+2):5
- long_body(+1)
- normalized(7→4/5)
pipeline_status: approved
approved_at: '2026-07-02'
used_in_issue: '2026-07-02'
---

# 요약

이 글은 Kubernetes Custom Resource Definitions로 VPC, 피어링, QoS를 선언하고, 컨트롤러가 스위치별 RoCEv2, QoS, L3 구성을 자동으로 반영하는 패브릭 구조를 설명한다.
각 스위치의 에이전트가 실제 네트워크 상태를 지속적으로 재조정하며, Grafana와 Prometheus로 큐 깊이와 마이크로버스트를 관측할 수 있다고 소개한다.
또한 PFC, ECN, DCQCN을 이용한 혼잡 제어와 BGP, ECMP 기반의 라우트 Clos, EVPN Type-5와 VRF를 통한 멀티테넌시를 강조한다.
RoCEv2가 UDP/IP 기반이라 L3 패브릭에서 라우팅 가능하며, 표준 호환 NIC이면 다양한 가속기와 연결할 수 있다고 주장한다.

# 핵심 포인트

- Kubernetes Custom Resource Definitions로 VPC, 피어링, QoS를 선언형으로 관리
- 컨트롤러와 스위치 에이전트가 RoCEv2, QoS, L3 설정을 지속적으로 일치시킴
- PFC, ECN, DCQCN을 이용한 RoCEv2 혼잡 제어와 마이크로버스트 관측을 강조
- BGP와 ECMP 기반의 라우트 Clos 및 EVPN Type-5, VRF로 멀티테넌시 구현
- RoCEv2가 UDP/IP라 L3 패브릭에서 라우팅 가능하다는 점을 부각

# 뉴스레터 헤드라인

RoCEv2와 EVPN Type-5 기반 L3 패브릭

# 원문 링크

https://hedgehog.cloud/disaggregated-inference