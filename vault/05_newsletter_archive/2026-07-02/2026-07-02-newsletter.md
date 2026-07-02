---
issue_date: '2026-07-02'
status: archived
total_articles: 7
used_sources:
- Cisco Networking
- lightreading
- ripe
- 웹검색
fallback_used: false
included_urls:
- https://inflect.com/blog/gpu-cluster-networking-infiniband-vs.-roce-for-large-scale-ai-training
- https://ubuntu.com/blog/what-is-rdma-over-converged-ethernet-roce
- https://labs.ripe.net/author/ritesh-mukherjee/aspa-is-live-can-you-see-it-working/
- https://labs.ripe.net/author/kjerstin-burdiek/ripe-ncc-days-baltics-insights-into-regional-resilience/
- https://blogs.cisco.com/networking/embedded-network-security-the-ultimate-defense-against-ai-driven-threats/
- https://www.lightreading.com/5g/echostar-tagged-as-stalking-horse-for-dish-wireless-assets
- https://hedgehog.cloud/disaggregated-inference
included_approved_files:
- 2026-06-08__expansion__datacenter_network__gpu-cluster-networking-infiniband-vs-roce-for-large-scale-ai.md
- 2026-06-09__expansion__datacenter_network__what-is-rdma-over-converged-ethernet-roce-ubuntu.md
- 2026-06-29__ripe_labs__aspa-is-live-can-you-see-it-working.md
- 2026-06-30__ripe_labs__ripe-ncc-days-baltics-insights-into-regional-resilience.md
- 2026-07-01__cisco_networking_blog__embedded-network-security-the-ultimate-defense-against-ai-dr.md
- 2026-07-01__lightreading__echostar-tagged-as-stalking-horse-amid-possible-auction-of-d.md
- 2026-07-02__expansion__datacenter_network__disaggregated-inference-network-lossless-roce-ethernet.md
published_at: 2026-07-02 11:20
source_draft: 2026-07-02-newsletter.md
archived_at: 2026-07-02 11:20
source_published: 04_newsletter/published/2026-07-02-newsletter.md
---

# IP Network 기술 동향 뉴스레터 — 2026-07-02

총 기사: 7건 | 출처: Cisco Networking, lightreading, ripe, 웹검색

## DataCenter Network

---

#### 1. RoCEv2와 InfiniBand의 GPU 클러스터 네트워킹 비교

**한줄 요약:** 이 글은 GPU 클러스터 학습용 네트워크에서 InfiniBand와 RoCEv2를 비교합니다

**상세 요약**

이 글은 GPU 클러스터 학습용 네트워크에서 InfiniBand와 RoCEv2를 비교합니다. RoCEv2는 PFC, ECN, DCQCN을 통해 Ethernet 위에서 RDMA 성능을 구현하지만, 각 메커니즘의 설정과 튜닝이 매우 중요하다고 설명합니다. 특히 잘못된 PFC나 ECN, DCQCN 설정은 성능 저하와 헤드오브라인 블로킹, 버퍼 오버플로로 이어질 수 있습니다. 반면 InfiniBand는 기본적인 혼잡 제어와 지연 안정성 측면에서 대규모 동기식 학습에 유리하다고 주장합니다. 대규모 환경에서는 비용과 운영 역량까지 포함한 위험 조정 관점에서 선택해야 한다는 점을 강조합니다.

- RoCEv2는 PFC, ECN, DCQCN을 조합해 Ethernet 위에서 RDMA 성능을 구현함
- PFC 설정 오류는 헤드오브라인 블로킹을 유발할 수 있음
- ECN과 DCQCN 튜닝이 부족하면 마이크로버스트와 처리량 저하가 발생할 수 있음
- InfiniBand는 혼잡 관리와 꼬리 지연 안정성 측면에서 대규모 AI 학습에 유리하다고 설명함
- 대규모 GPU 클러스터에서는 성능뿐 아니라 운영 성숙도와 비용도 선택 기준이 됨

**keyword:** ai_fabric, roce, infiniband, rdma, pfc, ecn

**출처:** 웹검색 · [원문 보기](https://inflect.com/blog/gpu-cluster-networking-infiniband-vs.-roce-for-large-scale-ai-training)

---

#### 2. RoCE와 ECN DCB DCQCN 혼잡 제어

**한줄 요약:** RoCE는 Ethernet 위에서 RDMA 성능을 활용하기 위한 기술이며, 대규모 AI/HPC 트래픽에서는 부하 분산과 혼잡 제어가 핵심 과제로 제시됩니다

**상세 요약**

RoCE는 Ethernet 위에서 RDMA 성능을 활용하기 위한 기술이며, 대규모 AI/HPC 트래픽에서는 부하 분산과 혼잡 제어가 핵심 과제로 제시됩니다.
본문은 ECMP 해시가 동기화된 대형 플로우를 고르게 분산하지 못해 일부 링크에 혼잡이 집중될 수 있다고 설명합니다.
이를 완화하기 위해 ECN, DCB, DCQCN 같은 혼잡 제어 메커니즘이 사용되며, 패킷 마킹과 우선순위 제어로 송신 속도를 조절합니다.
또한 PFC는 특정 상황에서는 안정화에 도움이 되지만, 다른 상황에서는 불안정을 키울 수 있다고 언급합니다.

- ECMP 해시는 AI/HPC처럼 동기화된 트래픽에서 부하를 고르게 나누지 못할 수 있음
- ECN은 큐가 가득 차기 전에 패킷을 표시해 수신자·송신자가 점진적으로 대응하게 함
- DCB는 트래픽 클래스를 분리하고 우선순위를 부여하는 메커니즘임
- DCQCN은 혼잡 신호를 이용해 송신 속도를 동적으로 조절함
- PFC는 상황에 따라 안정화와 불안정화 양쪽 영향을 모두 가질 수 있음

**keyword:** rdma, roce, ecmp, ecn, dcb, dcqcn

**출처:** 웹검색 · [원문 보기](https://ubuntu.com/blog/what-is-rdma-over-converged-ethernet-roce)

**편향 검토:** Canonical, Ubuntu, silicon vendors, switch manufacturers, ecosystem partners 등 특정 생태계와 제품군을 긍정적으로 강조하는 표현이 있어 벤더 관점이 일부 섞여 있습니다

---

#### 3. RoCEv2와 EVPN Type-5 기반 L3 패브릭

**한줄 요약:** 이 글은 Kubernetes Custom Resource Definitions로 VPC, 피어링, QoS를 선언하고, 컨트롤러가 스위치별 RoCEv2, QoS, L3 구성을 자동으로 반영하는 패브릭 구조를 설명한다

**상세 요약**

이 글은 Kubernetes Custom Resource Definitions로 VPC, 피어링, QoS를 선언하고, 컨트롤러가 스위치별 RoCEv2, QoS, L3 구성을 자동으로 반영하는 패브릭 구조를 설명한다.
각 스위치의 에이전트가 실제 네트워크 상태를 지속적으로 재조정하며, Grafana와 Prometheus로 큐 깊이와 마이크로버스트를 관측할 수 있다고 소개한다.
또한 PFC, ECN, DCQCN을 이용한 혼잡 제어와 BGP, ECMP 기반의 라우트 Clos, EVPN Type-5와 VRF를 통한 멀티테넌시를 강조한다.
RoCEv2가 UDP/IP 기반이라 L3 패브릭에서 라우팅 가능하며, 표준 호환 NIC이면 다양한 가속기와 연결할 수 있다고 주장한다.

- Kubernetes Custom Resource Definitions로 VPC, 피어링, QoS를 선언형으로 관리
- 컨트롤러와 스위치 에이전트가 RoCEv2, QoS, L3 설정을 지속적으로 일치시킴
- PFC, ECN, DCQCN을 이용한 RoCEv2 혼잡 제어와 마이크로버스트 관측을 강조
- BGP와 ECMP 기반의 라우트 Clos 및 EVPN Type-5, VRF로 멀티테넌시 구현
- RoCEv2가 UDP/IP라 L3 패브릭에서 라우팅 가능하다는 점을 부각

**keyword:** rocev2, kubernetes, qos, bgp, ecmp, evpn

**관련 표준 맥락**

- BESS / EVPN: DC Fabric 및 VPN 서비스 구현 방향과 연결

**출처:** 웹검색 · [원문 보기](https://hedgehog.cloud/disaggregated-inference)

**편향 검토:** Hedgehog Fabric Controller와 Spectrum-X를 언급하며 선언형 제어, lossless, 무제한 확장성 등을 강조하는 홍보성 표현이 포함되어 있음

## IP Security

---

#### 1. ASPA 검증 가시화 도구 RAVEN 공개

**한줄 요약:** ASPA 객체와 RTR v2 지원이 이미 가능하지만, 운영자가 실제 네트워크에서 ASPA가 무엇을 탐지하는지 보기 어렵다는 가시성 문제가 핵심으로 제기됩니다

**상세 요약**

ASPA 객체와 RTR v2 지원이 이미 가능하지만, 운영자가 실제 네트워크에서 ASPA가 무엇을 탐지하는지 보기 어렵다는 가시성 문제가 핵심으로 제기됩니다. 글은 과거 Pakistan Telecom, Rostelecom, Telegram 관련 사건을 예로 들어 기존 ROV만으로는 프리픽스 하이재킹과 라우트 유출을 모두 막기 어렵다고 설명합니다. 이를 보완하기 위해 BMP 피드와 RTR 검증기를 연결해 ASPA 검증 결과를 관찰하는 오픈소스 도구 RAVEN을 소개합니다. 또한 ASPA 커버리지, 오탐 여부, 배포 의사결정에 유용한 출력이 무엇인지 운영자 피드백을 요청합니다.

- ASPA 객체는 ARIN과 RIPE NCC에서 등록 가능하며, 검증기는 RTR v2를 지원합니다.
- ROV는 원점 하이재킹에는 효과적이지만, 라우트 유출은 별도로 탐지하기 어렵습니다.
- BMP 피드 기반으로 ASPA 검증 결과를 가시화하는 도구 RAVEN이 오픈소스로 공개되었습니다.
- RAVEN은 차단이 아니라 관찰과 신호 제공에 초점을 둔 ASPA 검증 도구입니다.
- 운영 환경에서 ASPA 커버리지와 오탐 여부를 검증하는 데이터가 향후 채택에 중요합니다.

**keyword:** aspa, rpki, rov, bmp, route_leak, prefix_hijack

**관련 표준 맥락**

- IDR / BGP: BGP 확장·정책·Route Leak·Routing Security 논의 추적

**출처:** ripe · [원문 보기](https://labs.ripe.net/author/ritesh-mukherjee/aspa-is-live-can-you-see-it-working/)

---

#### 2. AI 기반 SecOps와 embedded network security

**한줄 요약:** AI 확산으로 네트워크 트래픽과 보안 위협이 동시에 증가하면서, 분산 환경에서의 보호와 운영 단순화가 중요해졌다고 설명합니다

**상세 요약**

AI 확산으로 네트워크 트래픽과 보안 위협이 동시에 증가하면서, 분산 환경에서의 보호와 운영 단순화가 중요해졌다고 설명합니다.
기존 오버레이 방식의 보안은 가시성 분산, 정책 불일치, 성능 병목을 만들 수 있어 한계가 있다고 봅니다.
이에 따라 보안을 네트워크에 내장하는 embedded network security와 AI 기반 SecOps를 통해 탐지, 우선순위화, 대응을 더 빠르게 하자는 메시지를 제시합니다.
또한 Cisco Meraki 대시보드와 통합 보안 사례를 통해 운영 복잡도 감소와 대응 시간 단축 효과를 강조합니다.

- AI 및 agentic 워크로드는 대규모 대역폭과 예측하기 어려운 트래픽 패턴을 만든다
- 공격자도 AI를 활용해 피싱, 악성코드, 자동화 스캐닝을 고도화하고 있다
- 오버레이 보안은 가시성 분산과 정책 불일치, 성능 저하를 유발할 수 있다
- 네트워크 장비에 보안을 내장하고 AI 지원 SecOps를 결합하는 접근을 제안한다
- Cisco Meraki 대시보드와 통합 보안 사례로 운영 효율 개선을 강조한다

**keyword:** ai_security, secops, network_security, overlay_security, embedded_security

**출처:** Cisco Networking · [원문 보기](https://blogs.cisco.com/networking/embedded-network-security-the-ultimate-defense-against-ai-driven-threats/)

**편향 검토:** Cisco 제품과 고객 사례를 중심으로 구성된 홍보성 콘텐츠이며, 성능 개선 수치와 ‘ultimate defense’ 같은 과장 표현이 포함되어 있습니다

## Routing/Internet Operations

---

#### 1. RIPE Atlas와 RIPEstat로 본 발트 지역 회복탄력성

**한줄 요약:** RIPE NCC Days Baltics에서는 발트 지역의 인터넷 회복탄력성을 주제로 네트워크 운영 사례와 측정 결과가 논의됐다

**상세 요약**

RIPE NCC Days Baltics에서는 발트 지역의 인터넷 회복탄력성을 주제로 네트워크 운영 사례와 측정 결과가 논의됐다. 해저 케이블 장애와 같은 물리 계층 문제에 대해 RIPE Atlas 측정으로 트래픽이 우회 라우팅됐고, 지연은 일부 경로에서만 소폭 증가했으며 패킷 손실 증가는 관측되지 않았다. 또한 로컬 트래픽 처리, IXPs 강화, 네트워크 모니터링 확대, IPv6 배분과 자원 보유 현황 같은 지역 인터넷 인프라 현황도 공유됐다.

- 해저 케이블 장애 이후에도 트래픽이 대체 경로로 우회해 인터넷이 유지됐음
- RIPE Atlas 측정에서 일부 경로의 지연만 소폭 증가했고 패킷 손실 증가는 없었음
- 발트 지역의 회복탄력성 강화를 위해 IXPs 강화와 네트워크 모니터링 확대가 논의됐음
- RIPE NCC의 RIS, RIPE Atlas, RIPEstat 같은 도구 활용이 회복탄력성 분석 수단으로 언급됐음
- 발트 3국의 AS 번호, IPv6 배분, 자원 보유 현황 등 지역 인터넷 생태계 통계가 소개됐음

**keyword:** routing, ripe_atlas, ris, ripe_stat, ixp, ipv6

**출처:** ripe · [원문 보기](https://labs.ripe.net/author/kjerstin-burdiek/ripe-ncc-days-baltics-insights-into-regional-resilience/)

---

#### 2. EchoStar Dish Wireless 자산 매각과 5G 철수

**한줄 요약:** EchoStar와 Dish Wireless의 자산 매각 및 5G 네트워크 철수 과정이 법적·규제 이슈와 맞물려 진행되고 있습니다

**상세 요약**

EchoStar와 Dish Wireless의 자산 매각 및 5G 네트워크 철수 과정이 법적·규제 이슈와 맞물려 진행되고 있습니다. Dish Wireless는 5G 네트워크를 사실상 종료하고, Boost Mobile은 AT&T망을 이용하는 하이브리드 MVNO 모델로 전환했습니다. FCC는 스펙트럼 보유 및 5G 구축 이행과 관련해 EchoStar에 압박을 가했으며, 일부 스펙트럼 매각으로 이를 해소한 바 있습니다. 현재 Dish Wireless는 타워 업체와 인프라 공급사들로부터 170건이 넘는 소송에 직면해 있습니다.

- EchoStar가 Dish Wireless 자산 매각에서 잠재적 인수 후보로 거론됨
- Dish Wireless는 5G 네트워크를 사실상 철수하고 Boost Mobile을 MVNO 모델로 전환
- FCC는 스펙트럼 보유와 5G 구축 이행 문제로 EchoStar를 압박해 왔음
- 스펙트럼 매각 이후 장비 철거, 회선 종료, 창고 보관·폐기 등 네트워크 정리 작업이 진행 중
- Dish Wireless는 타워 업체 등과의 계약 분쟁으로 170건 이상 소송에 직면

**keyword:** 5g, mvno, spectrum, fcc, wireless

**출처:** lightreading · [원문 보기](https://www.lightreading.com/5g/echostar-tagged-as-stalking-horse-for-dish-wireless-assets)