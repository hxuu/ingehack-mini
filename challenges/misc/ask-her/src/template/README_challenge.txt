Ask Her — The Corrupted Backup
==============================

Our monitoring agent grabbed a nightly backup session before the machine was
wiped. What survived:

  - backup_corrupted.zip   the backup archive (partially recoverable)
  - memory.raw             a raw 16 MiB memory image taken minutes later
  - traffic.pcap           the upload of the backup session (TLS)

The backup tool that produced all of this is inside the archive. The keys it
handled that night were never written to disk in plaintext — but nothing on
this box can keep a secret if you look at the right layer.

Goal
----
Recover the master secret of the upload session, decrypt the TLS stream,
and read the flag.

Flag format: ingehack{...}
