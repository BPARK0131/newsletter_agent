---
title: What the World Cup Looks Like in Internet Traffic
source_id: kentik_blog
source_name: kentik_blog
source_url: https://www.kentik.com/blog/what-the-world-cup-looks-like-in-internet-traffic/
source_type: tavily
origin: open_web_search
domain: kentik.com
trust_level: low
category: IP Security
status: review
bias_risk: medium
bias_note: Kentik 제품(OTT Service Tracking, True Origin)과 자사 솔루션의 능력을 중심으로 사례와 결과를
  제시하는 홍보성 서술이 포함되어 있음
published_at: '2026-07-01'
collected_at: '2026-07-03'
reviewed_at: '2026-07-03'
importance_score: 4
review_score: 0.8
hitl_route: approval_pending
topic_tags:
- netflow
- dns
- bgp
- snmp
- ott_service_tracking
- true_origin
- isp
- fox_sports
recollect_required: false
review_required: true
is_published: false
---

# 요약

Kentik은 ISP가 이미 수집하는 흐름 데이터(NetFlow)에 DNS, BGP, SNMP를 결합해 True Origin 엔진으로 OTT 트래픽을 실시간 분류·측정했다. 이를 통해 Fox Sports의 트래픽이 미국 경기 시 급증하고 경기 내에서는 후반에 트래픽이 더 높게 나타나는 경향을 확인했다. 브라질은 Globo 중계 시 국내 트래픽 급증과 국제 트래픽 감소가 관찰되었고, 이란도 유사한 패턴을 보였다. 토너먼트가 진행될수록 경기 단위 집중도가 높아져 단일 경기 피크가 더욱 커질 것으로 예상된다.

# 핵심 포인트

- Kentik은 NetFlow를 DNS, BGP, SNMP와 연계해 True Origin으로 OTT 서비스(예: Fox Sports, Globo)를 실시간 라벨링·측정함
- Fox Sports 트래픽은 미국 경기에서 피크를 기록하고 경기 내에서는 후반(Second half) 트래픽이 더 높게 나타남
- 국가 단위 트래픽 변화 관찰: 브라질은 Globo 중계 시 국내 트래픽 급증과 국제향 트래픽 감소를 기록, 이란도 유사한 동향을 보임
- 토너먼트의 토너먼트(녹아웃) 단계와 결승으로 갈수록 시청집중도가 높아져 개별 경기 트래픽 피크가 커짐
- 용량은 SNMP 폴링으로, 볼륨·비트레이트는 분류된 플로우 데이터로 산출됨

# 뉴스레터 헤드라인

월드컵 네트워크 트래픽 분석: OTT·NetFlow·DNS

# 원문 링크

https://www.kentik.com/blog/what-the-world-cup-looks-like-in-internet-traffic/