---
title: 'When Local Blocks Go Global: The India-Telegram BGP Incident'
source_id: kentik_blog
source_name: kentik_blog
source_url: https://www.kentik.com/blog/when-local-blocks-go-global-the-india-telegram-bgp-incident/
source_type: tavily
origin: open_web_search
domain: kentik.com
trust_level: low
category: Routing/Internet Operations
status: review
bias_risk: low
bias_note: 기술적 사실 위주로 사건 경과와 라우팅 필터링 영향에 대해 설명함
published_at: '2026-06-17'
collected_at: '2026-07-03'
reviewed_at: '2026-07-03'
importance_score: 4
review_score: 0.8
hitl_route: approval_pending
topic_tags:
- bgp
- route_leak
- prefix_hijack
- rpki_rov
- netdevops
recollect_required: false
review_required: false
is_published: false
---

# 요약

2026년 6월 16일 인도 통신사업자 Rcom(AS18101)이 Telegram의 IP 블록을 BGP로 originate하여 트래픽을 블랙홀 처리하려다 해당 경로가 국제적으로 유출되어 일부 사용자에게 Telegram 접속 장애를 일으켰다.
해당 조치는 인도 정부의 Telegram 차단 명령 이행을 위한 것으로 보이며, 더_specific(더세부) 프리픽스를 originate한 점에서 의도성이 드러난다.
대다수 국제 사업자들이 RPKI ROV 등으로 RPKI-invalid 경로를 거부해 피해 확산은 제한되었으나, 인도 사용자들은 VPN 등 우회 수단에 의존해야 했다.

# 핵심 포인트

- Rcom(AS18101)이 Telegram의 IP 프리픽스를 originate해 국내 차단을 시도했으나 그 경로가 유출되어 여러 국가에서 서비스 장애 발생
- 의도적 블랙홀(프리픽스 하이재킹) 시도가 내부에 머물기보다 '라우트 유출'로 확산된 전형적 사례
- RPKI ROV 기반의 라우트 필터링이 다수 국제 사업자에서 적용되어 피해 규모가 크게 축소됨
- AS15412(전달 사업자) 및 일부 인도 네트워크(AS9498, AS4755)가 RPKI-invalid 경로를 차단했다면 영향은 국내에 국한되었을 가능성
- 과거 파키스탄(2008)·이라크(2023) 사례와 유사하게, 국가적 검열 조치가 인터넷 라우팅 전역에 영향을 줄 수 있음

# 뉴스레터 헤드라인

인도 BGP 하이재킹 사례와 RPKI ROV 영향분석

# 원문 링크

https://www.kentik.com/blog/when-local-blocks-go-global-the-india-telegram-bgp-incident/