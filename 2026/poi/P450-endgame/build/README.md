# P450 build

`build_p450.py` builds the endgame dossier: an audit log of exports signed with a device key, an evidence cache with that key and the HMAC method, the badge database, and the plan encrypted with a key derived from P100 and the exhibit. It reuses the P100 and P250 outputs, so build those first. The shipped download is in this challenge's `files/`.
