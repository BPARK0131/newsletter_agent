---
title: ASPA Is Live. Can You See It Working?
url: https://labs.ripe.net/author/ritesh-mukherjee/aspa-is-live-can-you-see-it-working/
source_name: ripe_labs
source_type: operator_blog
published: Mon, 29 Jun 2026 06:40:15 +0000
is_vendor: false
bias_risk: low
direct_citation: true
collect_method: rss+bs4_article
body_extract_method: bs4_article
newsletter_used_in: '2026-07-02'
status: newsletter_used
---

ASPA objects can be registered today with ARIN and RIPE NCC. Validators support RTR v2. But if you're an operator, can you actually see what ASPA is doing - or would do - on your network? We built a tool to find out.
What recent incidents tell us
When Pakistan Telecom took YouTube
offline
in 2008 by leaking a more specific prefix globally via PCCW, the post-incident analysis was conducted entirely from external route collector data — manually, after the fact. There was no mechanism for an operator to see from inside their own network that something was wrong until their users were already affected.
Twelve years later, Rostelecom
originated
over 8,800 prefixes belonging to Google, Amazon, Cloudflare, and others. ROV was partially deployed by this point — Telia and NTT automatically dropped the invalid routes; Level 3 and Hurricane Electric did not. Operators who had deployed ROV had an answer. Those who had not were still relying on external collectors and community mailing lists to understand what was happening in their own routing table.
On 16 June 2026, AS18101 — registered to Reliance Communications — announced IP prefixes belonging to Telegram. The announcement was origin-invalid; Telegram's prefixes are RPKI-signed. FLAG Telecom (AS15412) and Tata Communications failed to filter it, resulting in users in the UAE and elsewhere outside India losing access for several hours. The public debate about whether the incident was deliberate or accidental played out over days, drawing on external route-collector data.
Doug Madory
at Kentik and
Anurag Bhatia
independently concluded it was most likely a misconfiguration. But the telling detail is not the conclusion — it is how long it took to reach it, and what data was used. Operators affected by the incident had no straightforward way to see, against their own BMP feed, that the routes arriving from upstream were RPKI-invalid. The visibility came from outside, not from inside.
This is the structural gap. ROV has materially improved the situation for origin hijacks — the AS18101 incident propagated less far than Pakistan Telecom did in 2008, precisely because more of the transit-free tier now validates. But origin hijacks are only half the problem. A route leak — where the origin ASN is legitimate, and the prefix is correctly signed, but the route has travelled through an unauthorised provider relationship — passes ROV entirely. BGP accepts it. Traffic follows it. And an operator watching their routing table has no signal that anything is wrong. This is where ASPA picks up, and where the observability gap becomes acute.
The feedback loop that drove ROV adoption — and what ASPA is missing
ROV adoption did not accelerate because operators read the RFC and were convinced. It accelerated when operators could answer a specific question:
if I deploy a reject-invalid policy today, what breaks?
Tools that could simulate that impact on a live routing table — showing which prefixes would be dropped, which origin ASNs would be affected, and what percentage of traffic would be at risk — made the decision tractable. Operators could see the cost before committing.
ASPA lacks this feedback loop entirely — and this matters right now. The RIPE NCC enabled ASPA object creation in December 2025, ARIN followed in January 2026, and Routinator delivers ASPA Validated Payloads via RTR v2 to any relying party that connects. The infrastructure is ready. But an operator who registers an ASPA object on the the RIPE NCC dashboard and asks, "What did that just do for my network?" has no tool to answer the question. There is nothing that looks at their actual routing table — the routes they are receiving from peers and transits right now — and shows which paths are consistent with their declared ASPA topology and which are not. There is no what-if mode. There is no live signal.
The consequence is predictable. ASPA adoption remains well under 1% of the global ASN space. Operators are not registering objects at scale because they cannot see what those objects would do for them. The infrastructure is ahead of the observability.
What the gap actually looks like
Consider what an operator would need to do today to answer the question: "Is my network currently seeing any ASPA-invalid paths?"
They would need to retrieve their routing table — probably from a route server or a looking glass — which gives them a post-policy, aggregated view rather than the pre-policy Adj-RIB-In that shows everything the router received before filtering. They would need to obtain ASPA records from a validator, manually correlate them with AS_PATHs, and apply the upstream verification procedure from draft-ietf-sidrops-aspa-verification for each path they want to check. They would need to do this offline, against a snapshot, with no live update when RPKI data changes or when new routes arrive.
For a single prefix, this is feasible. For a full routing table across multiple peers, it is not a workflow any operator is going to run in production.
BGP Monitoring Protocol (BMP) exists precisely to solve the visibility half of this problem. Routers configured with BMP stream their Adj-RIB-In in real time to a collector — every route from every peer, pre-policy, as received. The IETF GROW working group has been discussing extensions to BMP, specifically to surface RPKI validation state (
draft-wang-grow-bmp-rpki-mon-reqs
). The gap identified in that draft is exactly the one described above: BMP gives you the routing state, RTR gives you the RPKI state, but nothing correlates them in a way that is useful to an operator in real time.
What we built
RAVEN (Routing Analysis, Validation, and Event Network) is an attempt to close this gap. It is an open-source, single Go binary that accepts BMP sessions from routers, maintains an RTR v2 connection to an RPKI validator, and annotates every received route with its ROV and ASPA validation state in real time.
The combined security posture per route is the core output. It is not enough to know that a route is ROV-valid — that tells you the origin is correctly registered, but says nothing about whether the AS_PATH is consistent with declared provider relationships. RAVEN combines both signals:
Secured
— origin valid, path consistent with ASPA records
Origin-only
— origin valid, path not verifiable (ASPA coverage gap — common today)
Path-suspect
— origin valid, but path violates ASPA — the route leak signal
Origin-invalid
— origin fails ROV regardless of path
The route leak scenario is the one that matters most for the current moment. In our lab environment, using real-world ASPA records from the global RPKI, we replicate a route leak in which a prefix is announced with a legitimate origin ASN but via a provider relationship not declared in the relevant ASPA object. ROV accepts it — the origin is correct. RAVEN flags it as path-suspect, identifies the specific hop where the customer-provider relationship is violated, and surfaces this via CLI, Prometheus metrics, and live streaming.
This is what a route leak looks like from inside your network — the AS_PATH violation is visible in real time before external route collectors notice anything and before the NOC starts getting calls.
The what-if mode is the near-term practical value for most operators. Running
raven what-if --reject-invalid
against a live routing table shows exactly which prefixes would be dropped under the ROV enforcement policy, which origin ASNs would be affected, and the traffic impact. The equivalent for ASPA enforcement —
raven what-if --aspa-enforce
— is the tool that does not currently exist anywhere else.
RAVEN is deployed on a laptop via Containerlab for demo purposes and can connect to production routers via BMP in the same configuration. The repository includes a full lab topology with FRR routers, Routinator, and three demo scenarios: origin hijack, more-specific hijack, and route leak via ASPA violation.
What we found — and what is still missing
Running RAVEN against our lab environment with real-world RPKI data confirms what the adoption numbers suggest: ASPA coverage is sparse. The majority of routes show
Unknown
for ASPA state — not because the paths are suspicious, but because most operators have not yet registered ASPA objects. This is the expected state of the ecosystem in mid-2026, and it will improve as the RIRs continue to onboard operators.
The implication for operators evaluating ASPA is that the near-term value is not enforcement — it is coverage measurement and incident investigation. RAVEN lets you answer: Of the routes I am currently receiving, how many involve AS_PATHs that I could decide on at all? Which of those are path-suspect? Where are my coverage gaps — the hops in my upstream paths where no ASPA record exists and therefore no determination is possible?
These are the questions that will drive ASPA registration, just as ROV what-if analysis drove ROA registration. Operators need to see the gap before they will fill it.
We are also honest about what RAVEN does not yet do. It does not replace a BMP collector for operators who already have OpenBMP or GoBMP pipelines — it is designed to complement them or serve as a lightweight alternative. It does not enforce — it observes and signals. And the ASPA verification algorithm it implements is based on a standards-track draft that has not yet been published as an RFC. We track the draft and will update the implementation as the specification evolves.
Try it
RAVEN is open source under the Apache 2.0 license and hosted at
github.com/nokia/bgp-routing-security-monitor
. Documentation is at
ritmukhe.github.io/raven-docs
.
If you have BMP-capable routers and an RTR-speaking validator, the configuration to connect RAVEN is minimal. If you want a safe environment to explore the scenarios described in this article, the Containerlab lab provides a full-stack setup on a laptop.
We are particularly interested in hearing from operators who run RAVEN against a production or near-production BMP feed — what the ASPA coverage looks like in practice, which path-suspect detections are genuine versus artefacts of incomplete ASPA registration, and what would make the what-if output more useful for deployment decisions. The tooling gap is real, and we have made a start on closing it, but the ecosystem data that operators can generate by running tools like this is what will actually move the needle on ASPA adoption.
ASPA is live. The infrastructure is ready. The question now is whether operators can see it working — and if they cannot, whether that is enough reason to help build the visibility layer that will make the difference.