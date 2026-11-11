# Cutout — 6 processes, 2 liars, 1 key (Series: Rumor)

`Cutout` is a hard Linux challenge about reading what the kernel permits you
to read, at the precise moment the kernel permits you to read it.

## Story
Six processes carry pieces. Two are decoys. One hides the key. The rest hold
the truth — encrypted. You are boul3h14 on the entry host; you will need
hours of patient forensic thinking rather than one big exploit.

## Why you'll like it
- `/proc` fd-holder semantics with a root-side fchmod race window.
- XOR by cyclic repetition across blob offsets, with a two-part /opt key.
- Nothing printed; nothing said. Verify before you trust.

## Attack surface (non-spoiler)
- The 'vendor-tool' in /opt is a decoy. The key is NOT in it.
- A ledger at /var/lib/vendor-tool lists offsets and purposes (world-readable).
- Daemon_fds aren't readable cross-uid… yet they're all you'll care about.

## Instancing
Uses the standard platform instancer with a 512 MB / 0.5 CPU / no-privileged
per-player container. Run via `Press Start` in the challenge page.

Flag format: `ingehack{...}`
