---
title: What the World Cup Looks Like in Internet Traffic
url: https://www.kentik.com/blog/what-the-world-cup-looks-like-in-internet-traffic/
source_name: kentik_blog
source_type: engineering_blog
published: '2026-07-01'
is_vendor: false
bias_risk: medium
direct_citation: true
collect_method: blog_index+tavily_extract
body_extract_method: bs4_article
recollected_at: '2026-07-03'
recollect_attempts: 1
---

Table of contents
How Kentik’s OTT Service Tracking works
Traffic surges for Fox Sports during games
Within a match, the second half usually wins
National traffic dips during games
Brazil
Iran
Australia
The biggest surges are still ahead
Subscribe
Summary
The World Cup may be the most-watched event in media history — so what does it look like from inside the network? We dug into ISP traffic data to reveal how Fox Sports peaks during US games, why second halves usually win, and how traffic flows shift for entire nations like Brazil and Iran when their team takes the field.
FIFA is
projecting
that approximately six billion people will engage with the tournament in some form across traditional broadcast, streaming, digital platforms, and out-of-home viewing, a figure that would make it the single most-watched sporting event in the history of global media. That’s roughly 75% of the world’s entire population!
With billions of people expected to engage with the tournament, the effects on global internet traffic are going to be widespread. Although we’re still in the middle of the tournament, we thought we’d share a few of the interesting things our traffic numbers show from the ISP’s perspective.
How Kentik’s OTT Service Tracking works
Kentik’s
OTT Service Tracking
gives broadband operators visibility into the over-the-top services running across their networks without the cost and complexity of deep packet inspection. It is powered by Kentik’s
True Origin
engine, which correlates the telemetry that an operator already collects, primarily flow records such as NetFlow enriched with DNS data, along with BGP and SNMP. (Learn more about
OTT Services (Over-the-Top Services) and OTT service tracking
.)
By matching subscriber DNS lookups to the flows that follow and comparing them against a continuously updated catalog of provider and hostname patterns, True Origin labels each flow in real time with an OTT Service Name (for example, Fox Sports, Globo, or Netflix), an OTT Service Category (video, gaming, social, audio, and so on), and an OTT Provider Name.
Capacity figures come from SNMP polling, while volume and bitrate figures are derived from the classified flow data, so that each service can be measured in bits per second over time and sliced by category, provider, connectivity type, geography, or subscriber segment. Moving beyond simple throughput, our engine can derive deeper telemetry, such as the total count of distinct destination IPs. Furthermore, tracking the peak or 95th percentile bitrate for each unique source or destination address provides a sophisticated proxy for household engagement and the quality of experience delivered to individual subscribers.
From there, we layered in complementary Kentik data, including destination-AS traffic to a country and CDN delivery paths, to show not just how much a given event drove but who carried it and where it entered the network. This is the same pattern Kentik has documented in its own event analyses, such as the
anatomy of an OTT traffic surge for Thursday Night Football on Amazon Prime
, and it is a capability any customer running OTT Service Tracking can apply to their own traffic.
Traffic surges for Fox Sports during games
By aggregating our traffic from an array of US-based ISPs running
OTT Service Tracking
, we can get a peek into the shape of the traffic curves for Fox Sports, the exclusive English-language broadcaster of the World Cup in the US.
Unsurprisingly, World Cup matches are driving the biggest traffic peaks on the service right now. The impact shows up in granular detail, including dips during the
controversial mandatory hydration breaks
, alongside the expected halftime drop.
Traffic for June 19 is pictured below. The US defeated Australia that day in a thrilling follow-up to their opening win over Paraguay. Traffic for subsequent matches was lower, as expected when the host nation was not playing.
June 20 fell on a Saturday, so the first match, the Netherlands trouncing Sweden, kicked off earlier than the day before. The day closed late with Japan dismantling Tunisia in the 1,000th World Cup match ever played. The late hour likely accounts for the lower traffic volumes seen from our customers’ subscribers.
Sunday, June 21, below, offered another slate of games, beginning earlier than the weekday schedule but without a late game like the previous day.
Within a match, the second half usually wins
For daytime and evening matches, the audience builds as the game goes on, so the traffic peak almost always falls in the second half, above the first-half high. Clear examples include England vs. Ghana (second half up 26 percent over the first-half peak), Portugal vs. Uzbekistan (up 11 percent), and USA vs. Paraguay, whose second half produced the single highest traffic volume of any half so far (up to June 25th). The first half also reads artificially low for each day’s opening match, because viewers are still arriving from a near-zero afternoon baseline.
That “second half is bigger” rule reverses for the late, midnight-ET West Coast games, where the second half fades as people head to bed. The second-half peak of Australia vs. Türkiye (12am ET) was 22 percent lower than the first half, while South Korea vs. Czechia (10pm ET) was essentially flat from half to half. In other words, kickoff time is a dominant modifier: Early and primetime games crescendo, while post-midnight games erode.
Score and matchup matter too. Competitiveness shapes the curve: Tight games and draws (England 0-0 Ghana) hold and build their audience into the second half, while blowouts (Germany 7-1, Brazil 3-0) tend to flatten or sag once the result is decided and people stop tuning in.
Team interest is the other big factor. The USMNT and marquee European sides (Argentina, Brazil, England, Netherlands) show steep second-half growth, whereas low-interest matchups stay flat. Mexico is the exception that proves the rule: It looks muted on Fox Sports only because its audience is watching the Spanish-language feed on Peacock (via Telemundo).
When we tally up the peak traffic (bits/sec) of all of the games by time of day, we arrive at this fascinating view of the tournament thus far. These peaks point to an arc of viewership heading into primetime ET. We saw significantly higher traffic for the US games, as might be expected.
National traffic dips during games
Brazil
Globo is the exclusive streaming service for Brazil’s World Cup matches. We see a clear surge in Globo traffic whenever the Seleção Canarinha is on the field, coinciding with dips in international traffic to various Brazilian providers as the country turns its attention to the match.
Iran
Even though
Iran’s internet
is still only
partially restored
, we saw the same dynamic as Iranians watched their team play Belgium on June 21. The national internet exchange
reported a surge in traffic
that coincided with a dip in international traffic to Iran, as internet users focused their attention on domestically hosted services carrying the game, away from external content sources.
Australia
SBS Video is the exclusive streaming service for World Cup soccer in Australia. The match against the US was popular, but it was not enough to move international traffic levels like Brazil’s and Iran’s did. It is worth noting that the game kicked off at 5 am AEST, while the other examples were closer to prime time.
The biggest surges are still ahead
Everything above is just the group stage. As the tournament moves into the knockout rounds, we expect viewership and, therefore, traffic, to climb toward the final. A few reasons stand out.
First, the schedule thins out dramatically. The group stage packed as many as four matches into a single day, scattering attention across the slate, whereas the knockout rounds feature just one or two matches per day. With fewer games competing for viewers, each one becomes a singular focus, reviving something increasingly rare in the on-demand era: appointment television, where large audiences gather around the same match at the same time.
Second, the stakes are far higher. Group-stage games can end in a draw and still leave a team alive, but every knockout match is win-or-go-home. That jump in consequence pulls in casual viewers on top of the die-hards.
Third, the field only gets stronger. The marquee sides that already over-index on our Fox Sports traffic statistics above are the ones most likely to still be playing, and weaker draws are eliminated each round. And then there is the final itself, routinely the most-watched event on the planet.
Expect the national-level effects to sharpen for the teams still alive. The Globo surge in Brazil and the matching dip in international traffic to the country were tied to a single group game, and with Brazil still in the hunt, those swings should grow more pronounced as each match becomes a must-watch, win-or-go-home event for the entire nation. Iran showed the same dynamic during its group game against Belgium before being eliminated.
As long as the USMNT keeps advancing, expect US traffic to set new highs. Even if the hosts bow out, the semifinals and final should still deliver the largest single-match traffic peaks of the entire tournament. We will be watching the curves!