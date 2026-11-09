#!/usr/bin/env python3
"""
solve.py - Automated solver for Challenge 1: 'Patient Zero'
Validates all 12 questions against server.py and retrieves the flag.
"""

import socket
import sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1337

ANSWERS = [
    ("10.10.40.15"),                                                      # Q1: Internal Target IP
    ("185.220.101.44"),                                                   # Q2: Attacker IP
    ("8040"),                                                             # Q3: Target Port
    ("PORTAL-SBA-01"),                                                    # Q4: Hostname
    ("/SetupWizard.aspx/SetupWizard.aspx"),                               # Q5: Rogue Endpoint
    ("adm_esisba_support"),                                               # Q6: Rogue Admin Account
    ("agent_stager.ps1"),                                                 # Q7: Staged Payload Filename
    ("40c4c9bb11bb069e9cf6404fcbf52f4f67a9c2e052c51b31e585478e609ac593"), # Q8: Payload SHA256
    ("ESISBA\\a.amrane"),                                                 # Q9: User Context
    ("DC01.ESI-SBA.DZ"),                                                  # Q10: Domain Controller
    ("CVE-2024-1709"),                                                    # Q11: Root-Cause CVE
    ("T1190"),                                                            # Q12: MITRE Technique
]

def main():
    print(f"[*] Connecting to {HOST}:{PORT}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
    except ConnectionRefusedError:
        print(f"[!] Could not connect to {HOST}:{PORT}. Is server.py running?")
        sys.exit(1)

    for i, ans in enumerate(ANSWERS, 1):
        # Read until prompt
        buf = b""
        while b"Your answer: " not in buf:
            chunk = s.recv(1024)
            if not chunk:
                print(f"[!] Connection closed prematurely at Q{i}!")
                print(buf.decode("utf-8", errors="replace"))
                sys.exit(1)
            buf += chunk

        prompt_text = buf.decode("utf-8", errors="replace")
        print(f"\n[+] Answering Question {i}/12 with: {ans}")

        # Send answer
        s.sendall(ans.encode("utf-8") + b"\n")

    # Read final response (flag)
    final_buf = b""
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        final_buf += chunk

    output = final_buf.decode("utf-8", errors="replace")
    print("\n" + output)

    if "ingehack{" in output:
        print("[SUCCESS] Flag successfully retrieved!")
    else:
        print("[FAIL] Flag not found in output.")
        sys.exit(1)

if __name__ == "__main__":
    main()
