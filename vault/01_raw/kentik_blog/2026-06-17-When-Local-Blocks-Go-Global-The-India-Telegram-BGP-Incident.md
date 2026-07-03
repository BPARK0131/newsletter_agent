---
title: 'When Local Blocks Go Global: The India-Telegram BGP Incident'
url: https://www.kentik.com/blog/when-local-blocks-go-global-the-india-telegram-bgp-incident/
source_name: kentik_blog
source_type: engineering_blog
published: '2026-06-17'
is_vendor: false
bias_risk: medium
direct_citation: true
collect_method: blog_index+tavily_extract
body_extract_method: bs4_article
recollected_at: '2026-07-03'
recollect_attempts: 1
---

Table of contents
Background
What happened?
Intentional, but also accidental
Conclusion
Subscribe
Summary
Yesterday’s leak of a BGP hijack intended to block Telegram in India is the latest routing mishap best described as
intentional, but also accidental
— a pattern dating back to Pakistan Telecom’s infamous hijack of YouTube in 2008, in which a domestic block escaped containment and disrupted the service worldwide.
Yesterday, India moved to temporarily block the popular messaging app Telegram over concerns about medical exam fraud. To implement this block, Indian carrier Rcom (AS18101) originated Telegram’s IP space in BGP in order to attract and blackhole the traffic.
This is a familiar story: a hijack intended to stay within national borders leaked out, disrupting Telegram service for a portion of users around the world.
In this post, I’ll explore the incident, its predecessors, and examine how route filtering techniques like
RPKI ROV
helped to limit the damage caused by the leak.
Background
On June 16, 2026, India’s government ordered a
nationwide block on Telegram
, set to remain in effect through June 22. The order was issued under Section 69A of India’s IT Act on the recommendation of the National Testing Agency (NTA), which cited the organized use of Telegram by cheating networks targeting candidates sitting for the NEET (UG) 2026 medical school entrance re-examination scheduled later this month.
Fraudulent Telegram channels — operating under names like “PAPER LEAKED NEET” and “Private Mafia” — were demanding payments from students and their families in exchange for purported access to exam materials. The government also ordered Telegram to disable its message-editing feature through June 30, arguing the feature had been exploited to fabricate after-the-fact evidence of paper leaks.
Telegram CEO Pavel Durov
pushed back publicly
, calling the week-long restriction a punishment of more than 150 million Indian users rather than the bad actors responsible — and
separately alleged
that Indian telecom operator Rcom was disrupting access to Telegram for some users outside India through unauthorized internet routing announcements. It is that last claim — routing manipulation by a major Indian carrier — that sets the stage for what we observed in the BGP data.
What happened?
At 07:17 UTC on June 16th, Rcom (AS18101, formerly Reliance Communications
and not Reliance Jio
) began originating several IP blocks used by Telegram, ostensibly to blackhole traffic destined for those address ranges. Those hijacked routes leaked outside of India and impacted users around the world.
In the visualization below, the red sliver along the top of the stack plot represents the propagation of AS18101’s hijack of 91.108.4.0/22, normally only originated by Telegram (AS62041). Only 1.6% of our BGP sources saw the hijacked route, a number likely owing to Telegram’s deployment of ROAs on all of its routes, enabling networks to drop the RPKI-invalid routes.
In response, Telegram began originating more-specific routes of the hijacks to regain control of the IP space, as the smaller routes get priority in the BGP selection algorithm. However, hours after this began,
AS18101 began hijacking those more-specifics at 16:14 UTC.
Here’s what the traffic data showed. From the moment the hijack began until Telegram fought back by announcing more-specifics, a small portion of global Telegram traffic was redirected to AS18101 in India and dropped. That recovery was short-lived: AS18101 hijacked the more-specifics too, redirecting traffic once again until those routes were finally withdrawn.
For a full table of the timings of the various hijacked routes, check out
this write-up by tech policy researcher Pranesh Prakash
.
Intentional, but also accidental
Yesterday’s leak of BGP hijacks targeting Telegram is the latest in a category of BGP incidents which are both
intentional
,
but also accidental
. I cover several of them in my
Brief History of the Internet’s Biggest BGP Incidents
, with the most famous being
Pakistan’s hijack of YouTube
in 2008.
But there have been numerous other incidents over the years as network operators have opted to use BGP to implement a block ordered by the government, only to mistakenly leak the routes into the global routing table.
During the military coup in Myanmar in February 2021, one
ISP began originating Twitter’s routes
in an attempt to comply with a government order to block the social media service. They subsequently leaked the routes at an internet exchange, disrupting the service for users around the region. In response to this incident, Twitter created ROAs for all of its routes, enabling RPKI ROV to reject the circulation of routes with incorrect origins, as is the case in most of these incidents.
Twitter’s adoption of RPKI ROV came just in time, as
an identical event occurred
just a year later during Russia’s crackdown on independent media in the aftermath of their invasion of Ukraine. Twitter’s rollout of ROAs for their routes greatly limited the collateral damage caused by the Russian leak. As Twitter’s CISO
wrote at the time
, “a bunch of the point of having security is to keep your systems from breaking all of the time,” and in this case, it kept a BGP hijack from breaking access to Twitter for users outside of Russia.
Most recently,
Brazil ordered X/Twitter to be blocked
, and again, a provider (AS263276) leaked its BGP hijack outside the country. Never heard of that incident? That’s probably because the leaked hijack routes were almost completely filtered. When RPKI ROV works correctly, disruptions due to routing mishaps can be avoided, becoming a headache that you never knew that you didn’t have.
The case closest to yesterday’s incident was
Iraq’s move to block Telegram
in August of 2023. Again, the hijack was leaked, but the impact was minimal due to route filtering, likely RPKI ROV, although it is impossible to know for sure.
Conclusion
In this particular case, it seems quite clear that this was another “intentional, but also accidental” incident. AS18101 likely didn’t want to leak their hijacked routes outside of India,
but they did
, disrupting Telegram service in numerous countries. The fact that AS18101 hijacked the more-specifics that Telegram announced to combat the original hijacks makes the intentionality pretty clear.
Had AS15412, the sole transit provider for AS18101, along with Indian networks AS9498 and AS4755 blocked RPKI-invalid routes, the incident would have been contained to India. RPKI ROV works pretty well in this scenario, but only if international carriers reject RPKI-invalid routes. Thankfully, most of them did, or Telegram would have been disrupted to a far greater extent.
Of course, this is little solace to the Indian users who had to employ a VPN to circumvent this IP-level blockage. Censoring Telegram is now the latest mechanism employed by a government to combat cheating on student exams.
In contrast, earlier this year,
Syria announced
that it would stop its long-running practice of national shutdowns to prevent cheating by high schoolers. Might India, like Syria, find another way to address this issue without blocking a popular communication tool and source of news and information?