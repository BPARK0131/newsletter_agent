---
title: Strengthening APNIC’s security foundations
url: https://blog.apnic.net/2026/06/30/strengthening-apnics-security-foundations/
source_name: apnic_blog
source_type: operator_blog
published: Mon, 29 Jun 2026 22:39:43 +0000
is_vendor: false
bias_risk: low
direct_citation: true
collect_method: rss+bs4_article
body_extract_method: bs4_article
---

APNIC continues to take practical steps to strengthen the security and resilience of the systems that Members and the wider Internet community rely on. As a Regional Internet Registry, APNIC operates services that support critical Internet infrastructure across the region. Keeping those services secure is not a single project or something that can be ‘finished’. It is ongoing work: Replacing ageing technology, testing applications, managing vulnerabilities, improving data handling, and checking that security controls continue to work as intended. These activities span infrastructure, applications, and operational processes.
This work forms part of APNIC’s core platforms and operational foundations, focusing on strengthening the systems that underpin APNIC services. By improving how these systems are secured, maintained, and operated, it supports more secure and resilient services for Members and the wider community.
APNIC’s Information Security Management System, certified to
ISO/IEC 27001
, provides the structure for this work. It helps APNIC identify security risks, decide how to treat or mitigate them and review whether controls remain effective over time.
Reducing legacy risk and improving resilience
Recent activity has focused on several practical areas, including infrastructure modernization. In Q2 of this year, we completed a multi-year program to update core infrastructure and reduce legacy technology risk, moving from end-of-life CentOS Linux hosts to containerized platforms or Red Hat Enterprise Linux 9 (RHEL9). This work is not always visible from the outside, but it matters. Modern, maintainable systems are easier to secure, monitor, and patch when new vulnerabilities are discovered.
We have also prioritised application security. Over the past year, we have rolled out Dynamic Application Security Testing (DAST) across our critical application portfolio. Automated DAST scans of running web applications and APIs now complement our existing Static Application Security Testing (SAST) and external vulnerability discovery, which we manage through our HackerOne Bug Bounty and Vulnerability reporting programs. The aim is simple: Find issues earlier, address them consistently, and reduce the chance that security problems reach production systems.
Data retention is another area where security depends on disciplined housekeeping. Information that no longer meets retention requirements can still create risk if it is kept indefinitely. We have provisioned Microsoft Purview as our data governance platform and are using it to apply sensitivity classifications and define retention schedules. The goal is to improve the way we manage sensitive historical information so that it can be efficiently removed when it is no longer required.
We are also strengthening controls that help prevent sensitive information from being disclosed inappropriately. Building on Microsoft Purview, we are rolling out enhanced data classification and Data Loss Prevention (DLP) controls across endpoints and cloud services, with a Q3 2026 target for the initial uplift. The goal is to protect information while still allowing people to work effectively.
Prevention is only one part of security. We also need to detect and respond to suspicious activity. To support this, we are running a controlled adversary emulation program to inform improvements to our production detection tooling. By simulating attacks, we aim to verify that monitoring and response capabilities operate as expected and to identify areas for improvement.
External security research, including responsible disclosure and bug bounty reporting, continues to play an important role. APNIC manages reports received through these channels, allowing issues to be assessed and resolved through established processes.
The wider vulnerability landscape is changing quickly. The growing use of AI by both security researchers and threat actors is accelerating the rate at which software vulnerabilities are discovered and disclosed, particularly in the open-source components and foundational infrastructure that we rely on. This compresses the window between disclosure and exploit availability and increases the need for faster response. During 2026, we are upgrading our test environments for greater consistency with production, which will let us test and deploy critical patches more quickly and reliably.
How these efforts work together
None of this work stands alone. Infrastructure modernization, application testing, data governance, monitoring, vulnerability management, and patching reinforce each other. Together, they represent a steady investment in the resilience of our services and in the trust Members place in APNIC as a Regional Internet Registry.
While much of this work happens behind the scenes, it plays a central role in keeping our services dependable, secure, and ready to support the region’s Internet community. This ongoing investment in core platforms and operational foundations ensures these systems remain robust, maintainable, and able to adapt as security risks and operational demands evolve.
The views expressed by the authors of this blog are their own
    and do not necessarily reflect the views of APNIC. Please note a
Code of Conduct
applies to this blog.