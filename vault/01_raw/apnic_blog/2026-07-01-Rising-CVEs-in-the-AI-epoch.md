---
title: Rising CVEs in the AI epoch
url: https://blog.apnic.net/2026/07/01/rising-cves-in-the-ai-epoch/
source_name: apnic_blog
source_type: operator_blog
published: Wed, 01 Jul 2026 01:40:30 +0000
is_vendor: false
bias_risk: low
direct_citation: true
collect_method: rss+bs4_article
body_extract_method: bs4_article
---

Photo by
Kelly Sikkema
on
Unsplash
.
A recent update on the
FIRST blog
highlights a significant shift in the 2026 vulnerability landscape. In
The 2026 Vulnerability Forecast Update: Navigating the AI Epoch
, the FIRST Forecasting team, Jerry Gamblin and Eireann Leverett, cut through the noise with new mid-year data showing a sharp rise in Common Vulnerabilities and Exposure (CVE) volumes driven by AI-assisted discovery and structural changes in reporting, while reframing what this surge actually means for defenders in an emerging ‘AI epoch’.
At first glance, the headline figure is striking. CVE volume is tracking more than 46% above the original forecast, pointing to roughly 66,000 vulnerabilities for the year. However, the authors caution against treating this as a crisis. Instead, they argue that the surge reflects predictable structural shifts, particularly the rapid scaling of AI‑assisted discovery and expanded vulnerability cataloguing.
Their central point is simple. More vulnerabilities do not necessarily mean more risk.
The report shows how autonomous and semi‑autonomous AI systems are reshaping discovery workflows. Tools such as Anthropic’s experimental ‘Mythos’ agent and OpenAI’s GPT‑5.4‑Cyber accelerate bug identification far beyond human-only capability. Real examples, including Mozilla’s AI‑assisted bug hunting pipeline, show how teams can surface and resolve hundreds of issues in a single release cycle. This is not incremental improvement. It is a steep change.
AI is only part of the story. The authors also highlight structural drivers of volume. These include backlog clearing by CVE Numbering Authorities (CNAs), growth in GitHub Security Advisories, and continued expansion of the global software ecosystem. Many open-source projects are only now receiving sustained scrutiny. In short, we are not just finding more bugs — we are looking in places we largely ignored before.
This context matters. The rise in CVEs does not simply reflect declining software quality. It also reflects improved visibility and broader coverage.
The report’s ‘rain versus flood’ analogy is particularly useful. Total disclosure volume (‘rainfall’) has increased sharply. Yet the subset of vulnerabilities that matter most — those with confirmed exploitation (CISA KEV) or high exploit likelihood (EPSS >10%) — remains largely flat. The message is clear. The signal‑to‑noise ratio is worsening, not the underlying threat.
For defenders, this shifts the challenge. The issue is no longer discovering vulnerabilities, but prioritizing them effectively. Triage, validation, and response are now the bottlenecks. Human capacity remains limited, especially for verification, coordinated disclosure, and detection engineering. Writing reliable exploit signatures and contextualizing risk at scale are emerging pain points.
The report also challenges assumptions about operational impact. Despite the increase in CVEs, software release cadences have remained stable. While more vulnerabilities are identified per release, organizations are not shipping updates more often. As a result, the day‑to‑day patching burden may remain relatively steady in the near term, even as upstream workload grows for developers and the Product Security Incident Response Team (PSIRT).
The authors describe a growing ‘race’ between offensive and defensive AI. The same technologies that accelerate discovery and exploit development also enable automated remediation, faster patching, and improved detection. The key question for late 2026 is not whether AI increases risk, but which side can operationalize it more effectively.
A forward‑looking section explores ‘ephemeral software’. As AI‑generated, on‑demand applications become more common, many ‘micro‑vulnerabilities’ will never appear in formal registries such as CVE. These untracked flaws create distributed and localized risk that traditional vulnerability management cannot address. The proposed response includes AI‑driven asset discovery, dynamic cataloguing, and runtime monitoring. In this model, the SBOM becomes far more fluid.
The report closes on a pragmatic note. Asset owners should scale programs in line with software growth, not CVE counts. Software producers should expect more vulnerabilities per release and invest in automation.
Overall, the message is one of measured adaptation. The volume increase is real, but it does not equal chaos. In the AI epoch, success depends on identifying which vulnerabilities matter — and acting on them quickly.
For security-minded folks, it’s a
very interesting read
worth your time. The full analysis and methodology are also
available on GitHub
.
The views expressed by the authors of this blog are their own
    and do not necessarily reflect the views of APNIC. Please note a
Code of Conduct
applies to this blog.