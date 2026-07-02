---
title: What is RDMA over Converged Ethernet (RoCE)? - Ubuntu
url: https://ubuntu.com/blog/what-is-rdma-over-converged-ethernet-roce
source_name: expansion/datacenter_network
source_type: tavily
origin: open_web_search
discovery_score: 4
discovery_reasons:
- recent_30d(+1)
- title_keywords(+2):ethernet,roce
- body_keywords(+2):4
- article_url(+1)
- long_body(+1)
- normalized(7→4/5)
search_query: AI fabric ethernet datacenter networking congestion telemetry RoCE
category: datacenter_network
topic: general
time_range: month
published: '2026-06-09'
published_at: '2026-06-09'
discovered_date: '2026-07-02'
date_reason: published_23d_ago
max_article_age_days: 60
collected_at: 2026-07-02 10:56
is_vendor: false
bias_risk: low
collect_method: tavily_expansion_discovery
_min_discovery_score: 3
domain: ubuntu.com
trust_level: medium
newsletter_used_in: '2026-07-02'
status: newsletter_used
---

Load balancing creates additional pressure. Ethernet fabrics typically rely on equal-cost multipath (ECMP) hashing to spread flows across multiple paths, but synchronized AI and HPC traffic patterns do not distribute evenly. Large flows can land on the same links while other paths remain underutilized, concentrating congestion inside a subset of the fabric.

Mechanisms such as explicit congestion notification (ECN), data center bridging (DCB), and later data center quantized congestion notification (DCQCN) were introduced to make this behavior manageable. ECN marks packets before queues overflow so endpoints can slow down gradually. DCB defines how traffic classes are isolated and prioritized across the fabric. DCQCN builds on those signals to regulate sender rates dynamically. [...] This matters even more as Ethernet fabrics continue to evolve for AI and HPC workloads. Canonical works closely with silicon vendors, switch manufacturers, and ecosystem partners to follow developments around technologies such as Spectrum-X, Ultra Ethernet, Falcon, and next-generation RoCE congestion control. The goal is not simply hardware enablement. It is making sure Ubuntu and the surrounding cloud-native stack can expose those capabilities consistently through upstream kernels, drivers, orchestration tooling, and CNCF integrations as the ecosystem evolves. [...] # Evolving congestion control

While RoCE can deliver excellent performance, large deployments also expose some of the weaker aspects of Ethernet under sustained congestion and synchronized traffic. Congestion spreads more easily, synchronized traffic patterns create hotspots, and mechanisms such as PFC can stabilize the fabric in one situation while amplifying instability in another.