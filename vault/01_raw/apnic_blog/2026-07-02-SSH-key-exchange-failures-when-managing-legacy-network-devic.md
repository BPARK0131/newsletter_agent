---
title: SSH key exchange failures when managing legacy network devices
url: https://blog.apnic.net/2026/07/03/ssh-key-exchange-failures-when-managing-legacy-network-devices/
source_name: apnic_blog
source_type: operator_blog
published: Thu, 02 Jul 2026 22:37:20 +0000
is_vendor: false
bias_risk: low
direct_citation: true
collect_method: rss+bs4_article
body_extract_method: bs4_article
---

Or,
when your laptop refuses to talk to your own routers…
You Secure Shell (SSH) into a router you have logged into a hundred times, and this time your laptop refuses. No password prompt, no banner, just a flat rejection before the session starts:
Unable to negotiate with 192.0.2.40 port 22: No matching key exchange method found.
Their offer: diffie-hellman-group-exchange-sha1, diffie-hellman-group14-sha1
The device is fine. Your credentials are fine. What changed is your laptop. Modern operating systems have been quietly removing weak cryptographic algorithms from SSH, and a lot of network gear still in production has never learned the newer ones. This post is about that gap, and how to bridge it without quietly undoing years of security work.
What is failing
SSH negotiates its cryptography at the start of every connection. Each side advertises ordered lists of what it supports for several independent parameters, and they agree on the strongest option both have in common. In short, both sides must agree on every category, or the connection fails before authentication.
Three of those parameters are where legacy devices fall over.
Key exchange
(
KexAlgorithms
) is how the two sides derive a shared session key. Old devices often only offer SHA-1-based methods such as
diffie-hellman-group-exchange-sha1
and
diffie-hellman-group14-sha1
. There are two separate issues here: group size and hashing algorithm. The group sizes are not the problem — group 14 is a sound 2048-bit group. What gets both disabled is the SHA-1 hash they rely on. OpenSSH removed the older 1024-bit group1 entirely in version 7.0, and later dropped these SHA-1 variants from its defaults.
Host key algorithm
is how the server proves its identity, and this catches people off guard. A device presents an RSA host key, and you assume RSA is the problem, but the key itself is usually fine. The key type (RSA) is not the issue; the signing method (SHA-1) is. What OpenSSH 8.8 disabled by default in 2021 was the
ssh-rsa
signature scheme, which signs with SHA-1. The RSA key can stay; the SHA-1 signature over it is what your client now refuses.
no matching host key type found. Their offer: ssh-rsa
Cipher
(ciphers) is the symmetric encryption for the session body. Older gear leans on CBC-mode ciphers such as
aes256-cbc
or
3des-cbc
, which modern OpenSSH has pushed out in favour of CTR and GCM modes.
On a mixed-age network, you can hit all three issues on the same device.
Why this happened, and why it is correct
It is tempting to blame the operating system vendors. Resist that. The algorithms above are weak by current standards: SHA-1 has practical collision attacks, the older 1024-bit Diffie-Hellman groups are within reach of well-resourced adversaries, and Cipher Block Chaining (CBC) -mode ciphers in SSH have a history of plaintext-recovery weaknesses. Even where the underlying group is still adequate, as with the 2048-bit group 14, pairing it with SHA-1 is enough to retire it. OpenSSH disabling these by default is the system working as intended.
The friction is real because network equipment lives for 10 or 15 years, with firmware frozen in the cryptographic assumptions of its release date. A switch from 2012 has no idea that
ssh-rsa
would fall out of favour in 2021. You are caught between a client who has moved on and a device that cannot.
The workaround, scoped properly
You can re-enable a specific old algorithm for a specific connection. The critical detail is the ‘
+
’ prefix, which appends the algorithm to your existing secure defaults, rather than replacing the whole list.
Without the
+
, you would force SSH to use only that one weak algorithm for every host — exactly the mistake to avoid.
For a one-off session:
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 \
    -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o Ciphers=+aes256-cbc \
    admin@192.0.2.40
Typing that every time invites error, so put it in
~/.ssh/config
, scoped tightly to your legacy devices:
Host 192.0.2.* legacy-sw-*
    KexAlgorithms +diffie-hellman-group14-sha1
    HostKeyAlgorithms +ssh-rsa
    PubkeyAcceptedAlgorithms +ssh-rsa
    Ciphers +aes256-cbc
The host pattern matching is what keeps you safe. These relaxed settings apply only when you connect to a matching host. Every other SSH session — to servers, Git hosts, and modern gear — still negotiates at full strength. The weakening is surgical, not global. Note also that when a device offers more than one weak method — both
group-exchange-sha1
and
group14-sha1
— you re-enable only the stronger one (the fixed 2048-bit group14) and leave the rest off.
PubkeyAcceptedAlgorithms
matters only if you authenticate with an RSA key, since the client must then be willing to offer an SHA-1 RSA signature for your own key.
Treat the workaround as a countdown, not a destination
The moment you add
diffie-hellman-group14-sha1
back, you have created a connection whose security rests on a deprecated hash. On an isolated out-of-band management network, that is a tolerable, temporary state — not something to leave running indefinitely, and never something to apply globally because it was easier than scoping it.
The honest reading of one of these errors is that a device has aged out of the current security baseline. The flag gets you in today; it fixes nothing. The real remediation is one of:
Upgrade firmware. Many devices that shipped with only
ssh-rsa
gained
rsa-sha2-256
and
rsa-sha2-512
in later releases. Sometimes, the fix is an update you have been putting off
Regenerate host keys after upgrading, as a device may keep offering SHA-1 signatures until forced otherwise
Replace the device if it is genuinely end of life
For anyone running equipment across many procurement cycles, this is not really an SSH problem. It is a lifecycle planning problem wearing an SSH error message. Each host that needs a relaxed config is telling you where it sits on the replacement roadmap. Keep a record of which hosts required which relaxations — that list is your crypto-deprecation migration backlog.
The takeaway
When a modern client refuses an older device, the failure is informative, not arbitrary. Read the offered algorithm in the error, re-enable it narrowly with the ‘+’ syntax and host scoping, and record the device as one that needs attention. Get in, do the work, and treat every such error as a reminder that the equipment has fallen behind the baseline that the rest of your network already meets.
Tuwan Azgar Jaleel is a Senior Network and Systems Engineer at the Lanka Education and Research Network (LEARN), Sri Lanka’s national research and education network, where he manages the campus backbone network and institutional connectivity services. He is also an APNIC Community Trainer and an active member of LKNOG.
The views expressed by the authors of this blog are their own
    and do not necessarily reflect the views of APNIC. Please note a
Code of Conduct
applies to this blog.