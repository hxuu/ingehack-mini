#!/usr/bin/env python3
"""
Patient Zero — ESI-SBA DFIR / Threat Intel Challenge Server
TCP Socket sequential question server.
One wrong answer = connection terminates.
"""

import socket
import threading
import signal
import sys
import os

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 1337))
TIMEOUT = 300  # 5 minutes per question
FLAG = 'ingehack{p4t13nt_z3r0_3s1_sb4_G0t_PWN3d_!}'

BANNER = r"""
  ______  _____ _____     _____ ____          
 |  ____|/ ____|_   _|   / ____|  _ \   /\    
 | |__  | (___   | |____| (___ | |_) | /  \   
 |  __|  \___ \  | |______\___ \|  _ < / /\ \  
 | |____ ____) |_| |_     ____) | |_) / ____ \ 
 |______|_____/|_____|   |_____/|____/_/    \_\
               INCIDENT RESPONSE UNIT          
"""

INTRO = """============================================================
       INCIDENT BRIEFING — OPERATION PATIENT ZERO
============================================================
Target Organization: ESI-SBA (École Supérieure en Informatique)
Affected Asset      : Student & Faculty Services Portal
Impacted User       : [CONFIDENTIAL — Identify via PCAP Telemetry]

The ESI-SBA SOC detected an unauthorized external intrusion
into the primary faculty portal, resulting in administrative
tampering, unprivileged code execution, and domain reconnaissance.

You are provided with the perimeter network packet capture:
  [ esi_sba_breach.pcapng ]

Analyze the evidence and answer the 12 triage questions in sequence.
A single incorrect answer will terminate the session.
============================================================
"""

QUESTIONS = [
    {
        'id': 1,
        'title': 'The Victim Machine',
        'text': 'What is the internal IP address of the compromised ESI-SBA server?',
        'format': 'IPv4 address (e.g. 192.168.1.1)',
        'answers': ['10.10.40.15'],
    },
    {
        'id': 2,
        'title': 'The Adversary',
        'text': 'What is the external IP address of the attacker who initiated the suspicious traffic?',
        'format': 'IPv4 address (e.g. 192.168.1.1)',
        'answers': ['185.220.101.44'],
    },
    {
        'id': 3,
        'title': 'The Target Gateway',
        'text': 'What destination TCP port was the targeted web service listening on?',
        'format': 'Port number (e.g. 80)',
        'answers': ['8040'],
    },
    {
        'id': 4,
        'title': 'The Hostname',
        'text': 'What is the NetBIOS/hostname of the compromised server as identified in HTTP response headers?',
        'format': 'HOSTNAME',
        'answers': ['PORTAL-SBA-01', 'portal-sba-01'],
    },
    {
        'id': 5,
        'title': 'The Rogue Endpoint',
        'text': 'What exact URI request path did the attacker submit to bypass the initial access controls?',
        'format': '/path/to/endpoint',
        'answers': ['/SetupWizard.aspx/SetupWizard.aspx', '/SetupWizard.aspx/'],
    },
    {
        'id': 6,
        'title': 'The Backdoor Account',
        'text': 'What username did the attacker register through the rogue setup wizard to establish administrative persistence?',
        'format': 'username',
        'answers': ['adm_esisba_support'],
    },
    {
        'id': 7,
        'title': 'Staged Payload Filename',
        'text': 'Following the authentication bypass, the attacker executed commands to download a staging script from their infrastructure. What is the filename of this stager?',
        'format': 'filename.ext',
        'answers': ['agent_stager.ps1'],
    },
    {
        'id': 8,
        'title': 'Payload Integrity (Hash)',
        'text': 'What is the SHA-256 hash of the carved agent_stager.ps1 payload?',
        'format': '64-character lowercase hex string',
        'answers': ['40c4c9bb11bb069e9cf6404fcbf52f4f67a9c2e052c51b31e585478e609ac593'],
    },
    {
        'id': 9,
        'title': 'Compromised User Context',
        'text': 'Under what active Windows user account did the stager\'s reconnaissance commands execute?',
        'format': 'DOMAIN\\username or username',
        'answers': [
            'ESISBA\\a.amrane',
            'esisba\\a.amrane',
            'a.amrane',
            'A.AMRANE',
            'ESISBA/a.amrane',
        ],
    },
    {
        'id': 10,
        'title': 'Domain Discovery',
        'text': 'The attacker performed internal Active Directory discovery. What is the Fully Qualified Domain Name (FQDN) of the primary Domain Controller discovered?',
        'format': 'hostname.domain.tld',
        'answers': ['DC01.ESI-SBA.DZ', 'dc01.esi-sba.dz'],
    },
    {
        'id': 11,
        'title': 'Root-Cause Attribution (CVE)',
        'text': 'Based on the affected service on port 8040 and the specific /SetupWizard.aspx traversal vector, what is the official CVE identifier for this vulnerability?',
        'format': 'CVE-YYYY-NNNNN',
        'answers': ['CVE-2024-1709', 'cve-2024-1709'],
    },
    {
        'id': 12,
        'title': 'MITRE ATT&CK Classification',
        'text': 'What is the primary MITRE ATT&CK technique ID for the initial access vector used to compromise this perimeter asset?',
        'format': 'TXXXX (e.g. T1190)',
        'answers': ['T1190', 't1190'],
    },
]


def normalize(s):
    """Strip whitespace, quotes, and normalize dashes."""
    s = s.strip()
    s = s.replace('\u2014', '-').replace('\u2013', '-')
    s = s.replace('\u2018', "'").replace('\u2019', "'")
    s = s.replace('\u201c', '"').replace('\u201d', '"')
    return s


def check_answer(q, answer):
    """Check if the provided answer matches any of the accepted forms."""
    norm_answer = normalize(answer)
    for expected in q['answers']:
        if norm_answer.lower() == normalize(expected).lower():
            return True
    return False


def handle_client(conn, addr):
    """Handle an interactive client socket session."""
    try:
        conn.settimeout(TIMEOUT)
        conn.sendall(BANNER.encode())
        conn.sendall(INTRO.encode())

        for q in QUESTIONS:
            msg = (
                f"\n{'─' * 60}\n"
                f"  [{q['id']:02d}/12] {q['title']}\n"
                f"{'─' * 60}\n"
                f"  {q['text']}\n"
                f"\n  Format: {q['format']}\n"
                f"\n  Your answer: "
            )
            conn.sendall(msg.encode())

            # Read answer line
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    raise ConnectionError("client disconnected")
                data += chunk
                if b'\n' in data:
                    break

            answer = data.decode('utf-8', errors='replace').strip()

            if check_answer(q, answer):
                conn.sendall(b"\n  [+] Correct! Proceeding...\n")
            else:
                conn.sendall(
                    b"\n  [-] Incorrect answer.\n"
                    b"  The investigation has failed. Connection terminated.\n\n"
                )
                return

        # Success - Deliver Flag
        success_msg = (
            f"\n{'=' * 60}\n"
            f"  INCIDENT TRIAGE COMPLETE — ALL 12 QUESTIONS SOLVED\n"
            f"{'=' * 60}\n\n"
            f"  Flag: {FLAG}\n\n"
            f"  You have accurately attributed the breach of Prof. A. AMRANE's\n"
            f"  system. The attacker has successfully pivoted into the\n"
            f"  internal ESI-SBA Linux workstation infrastructure.\n\n"
            f"  Proceed to Challenge 2: 'The Domain Workstation'...\n"
            f"{'=' * 60}\n\n"
        )
        conn.sendall(success_msg.encode())

    except (ConnectionError, BrokenPipeError, OSError):
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(10)

    def shutdown(sig, frame):
        print("\n[!] Server shutting down.")
        server.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"[+] ESI-SBA Patient Zero Server listening on {HOST}:{PORT}")
    print(f"[+] 12 sequential questions loaded. Timeout: {TIMEOUT}s")

    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except OSError:
            break


if __name__ == '__main__':
    main()
