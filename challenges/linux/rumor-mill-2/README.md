# Rumor Mill #2 — The Encoded Rumor

A Linux privilege-escalation CTF challenge where players must chain base64
decoding, password rotation hints, multi-part password assembly, and OpenSSL
decryption to capture the real flag.

## Quick Start

### Prerequisites
- Docker (20.10+)
- bash

### Build
```bash
docker build -t rumor-mill-2:v2.0.0 .
```

### Run
```bash
# Copy .env.example to .env and adjust if needed
cp .env.example .env
source .env

docker run -d --name rumor-mill-2 \
  -p "${SSH_PORT:-2222}:${SSH_PORT:-2222}" \
  -e SSH_PORT="${SSH_PORT:-2222}" \
  --hostname challenge-rumor-mill-2 \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  rumor-mill-2:v2.0.0
```

### Connect (Player)
```bash
ssh y4ss1n3@localhost -p 2222
# Password: Welcome123
```

### Verify
```bash
# Run verification suite inside the container
docker exec rumor-mill-2 /bin/bash -c 'bash /verify.sh'

# Run automated solver
docker exec rumor-mill-2 /bin/bash /solutions/verify_solution.sh
```

### Stop & Remove
```bash
docker stop rumor-mill-2
docker rm rumor-mill-2
```

### Rollback
```bash
# Remove the container and image
docker stop rumor-mill-2 2>/dev/null; docker rm rumor-mill-2 2>/dev/null
docker rmi rumor-mill-2:v2.0.0

# Rebuild from a specific tag
git checkout v2.0.0
docker build -t rumor-mill-2:v2.0.0 .
```

## Challenge Details
- **Series:** Rumor (2 of 2)
- **Category:** Linux
- **Difficulty:** Hard (400 pts)
- **Flag format:** `ingehack{...}`
- **Connection:** SSH on port 2222

## File Structure
```
.
├── Dockerfile              # Ubuntu 22.04 base image
├── entrypoint.sh           # Container start: users, files, hardening, sshd
├── verify.sh               # Comprehensive verification suite
├── solutions/
│   ├── solve.md            # Step-by-step solution walkthrough
│   └── verify_solution.sh  # Automated solver script
├── challenge.yml           # CTF metadata
├── .env.example            # Environment variable template
├── README.md               # This file
└── LICENSE                 # MIT License
```

## Security Notes
- No secrets are baked into the Docker image
- gh3nj4's password is randomly generated at container start
- All passwords are set via `chpasswd` (hashed by yescrypt in `/etc/shadow`)
- The real flag is AES-256-CBC encrypted at rest
- Comprehensive hardening (H1–H25) is applied at container start
