---
title: Disaggregated Inference Network | Lossless RoCE Ethernet
url: https://hedgehog.cloud/disaggregated-inference
source_name: expansion/datacenter_network
source_type: tavily
origin: open_web_search
discovery_score: 4
discovery_reasons:
- recent_7d(+2)
- title_keywords(+2):ethernet,roce
- body_keywords(+2):5
- long_body(+1)
- normalized(7→4/5)
search_query: AI fabric ethernet datacenter networking congestion telemetry RoCE
category: datacenter_network
topic: general
time_range: month
published: '2026-07-02'
published_at: '2026-07-02'
discovered_date: '2026-07-02'
date_reason: published_0d_ago
max_article_age_days: 60
collected_at: 2026-07-02 10:56
is_vendor: false
bias_risk: low
collect_method: tavily_expansion_discovery
_min_discovery_score: 3
domain: hedgehog.cloud
trust_level: medium
newsletter_used_in: '2026-07-02'
status: newsletter_used
---

## Declare intent. The fabric does the rest.

Operators declare what they need — VPCs, peerings, QoS — as Kubernetes Custom Resource Definitions. The Hedgehog Fabric Controller translates that into exact per-switch RoCEv2, QoS, and L3 configuration, and a lightweight agent on each switch continuously reconciles the live network against your declared state.   
  
Deep, real-time telemetry streams natively into Grafana and Prometheus, exposing queue depths and microbursts so you can prove the fabric is lossless — not hope it is.

Group (1).svg) [...] RoCEv2, automated. Validated configurations pushed to every switch, declaratively, from one API.
 Congestion control built in. PFC plus ECN/DCQCN tuned for AI traffic, with load balancing intelligent enough not to collapse multi-gigabyte elephant flows onto a single hashed path.
 L3 to the host. A routed Clos with BGP and ECMP everywhere — no broadcast storms, no spanning tree, no flat-MAC scaling ceiling. It's the same design hyperscalers and NVIDIA Spectrum-X have run for years; Hedgehog just makes it easy.
 Multitenancy without compromise. Per-tenant isolation via L3 EVPN Type-5 routes and VRFs — summarizable, scalable, and enforced in the data plane. Not stretched L2.

roi-design-math@2x

## Because it's routable Ethernet, anything standards-compliant plugs in [...] RoCEv2 packets are UDP/IP — routable across a Layer 3 fabric. That single fact is the open AI ecosystem's biggest lever: any accelerator with a standards-compliant RoCEv2 NIC plugs into the same fabric a GPU plugs into. Keep prefill on NVIDIA GPUs where they dominate, and stay free to choose the most cost- and power-efficient option on decode — Cerebras, SambaNova, or whatever wins the next round.

No proprietary interconnect gets to dictate your accelerator roadmap. And because the fabric is routed multipath, it's ready for the next round of optimization — like Multipath Reliable Connection (MRC), released through OCP in 2026 — that pushes elephant-flow performance well past hash-based ECMP.

illustration-open-source-software

## Declare intent. The fabric does the rest.