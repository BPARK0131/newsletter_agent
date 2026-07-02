---
title: Path Segment Identifier in MPLS-Based Segment Routing Networks
url: https://datatracker.ietf.org/doc/rfc9545/
source_id: ietf_datatracker
source_name: ietf_datatracker
source_type: standard_reference
published: '2026-05-20T15:44:52Z'
is_vendor: false
bias_risk: low
direct_citation: true
collect_method: ietf_datatracker_api
review_mode: standards_signal
output_section: standardization_radar
doc_name: rfc9545
wg: SPRING
document_type: rfc
maturity: published-rfc
---

# Path Segment Identifier in MPLS-Based Segment Routing Networks

- Document: `rfc9545`
- Working Group: SPRING
- Updated: 2026-05-20T15:44:52Z
- Pages: 11

## Abstract

A Segment Routing (SR) path is identified by an SR segment list. A subset of segments from the segment list cannot be leveraged to distinguish one SR path from another as they may be partially congruent. SR path identification is a prerequisite for various use cases such as performance measurement and end-to-end 1+1 path protection.

 In an SR over MPLS (SR-MPLS) data plane, an egress node cannot determine on which SR path a packet traversed the network from the label stack because the segment identifiers are removed from the label stack as the packet transits the network.

 This document defines a Path Segment Identifier (PSID) to identify an SR path on the egress node of the path.

Full document: https://datatracker.ietf.org/doc/rfc9545/