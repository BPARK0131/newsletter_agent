---
title: SSH key exchange failures when managing legacy network devices
source_id: apnic_blog
source_name: apnic_blog
source_url: https://blog.apnic.net/2026/07/03/ssh-key-exchange-failures-when-managing-legacy-network-devices/
source_type: rss
origin: curated_source
domain: blog.apnic.net
trust_level: high
category: IP Security
status: approved
bias_risk: low
bias_note: 기술적 설명 위주이며 특정 벤더 홍보나 과장 표현 없음
published_at: Thu, 02 Ju
collected_at: '2026-07-03'
reviewed_at: '2026-07-03'
importance_score: 4
review_score: 0.8
hitl_route: approval_pending
topic_tags:
- ssh
- openssh
- sha1
- ssh-rsa
- kexalgorithms
- netdevops
recollect_required: false
review_required: false
is_published: false
pipeline_status: approved
approved_at: '2026-07-03'
---

# 요약

최신 운영체제와 OpenSSH는 SHA-1 기반 키교환·서명·구식 암호를 기본에서 제거해 레거시 라우터에 대한 SSH 연결이 실패할 수 있다. 오류 메시지는 제안된 알고리즘을 알려주므로 문제 원인을 파악할 수 있다. 단기적으로는 호스트 범위의 '+' 문법으로 특정 알고리즘을 국한해 재활성화하고, 장기적으로는 장비 교체·펌웨어 업그레이드·호스트 키 재생성 등 마이그레이션 계획을 세워야 한다.

# 핵심 포인트

- SSH 협상 단계의 세 가지 항목(키 교환 KexAlgorithms, 호스트 키 서명 방식, 세션 암호 ciphers) 중 어느 하나라도 공통 항목이 없으면 연결이 실패함
- 많이 발생하는 원인: diffie-hellman-group-exchange-sha1·diffie-hellman-group14-sha1 등 SHA-1 기반 KEX, ssh-rsa 서명 방식(sha-1), CBC 모드 암호의 제거
- 임시대응: OpenSSH 클라이언트에서 호스트 범위로 필요한 알고리즘만 '+' 문법으로 제한해 재활성화하고 접속 후 장비를 점검
- 근본대응: 장비 펌웨어/소프트웨어 업그레이드, 호스트 키 재생성(서명 방식 변경), 또는 교체 및 교체 우선순위(마이그레이션 백로그) 수립

# 뉴스레터 헤드라인

OpenSSH 업데이트로 인한 SSH 키교환 실패 대응

# 원문 링크

https://blog.apnic.net/2026/07/03/ssh-key-exchange-failures-when-managing-legacy-network-devices/