# Sudoers — Solution & Writeup

> **Notice:** Do not publish until the CTF ends.

## Red Herring Name
The challenge is named **sudoers** as a deliberate red herring. The target system does not give the `ctf` user `sudo` access, nor is `/etc/sudoers` misconfigured. The actual vulnerability lies in **setuid / SUID privilege retention**, and the custom binary is named `/usr/local/bin/auditdrop` to avoid clashing with standard system utilities like `sudo`.

## Vulnerability Analysis

### RUID, EUID, and SUID
In Linux process credentials:
- **RUID (Real User ID):** Identifies the user who launched the process (`ctf`, UID 1000).
- **EUID (Effective User ID):** Used by the operating system for access control decisions (`root`, UID 0, when executing a setuid-root binary).
- **SUID (Saved Set-User-ID):** Preserves the privileged EUID across temporary privilege drops so the process can regain privileges later if needed.

### Temporary vs. Permanent Dropping
In `auditdrop.c`, the developer intended to safely execute a user-controlled command by dropping privileges:
```c
if (seteuid(getuid()) != 0) {
    perror("seteuid");
    return 1;
}
...
snprintf(cmd, sizeof(cmd), "cat %s", path);
system(cmd);
```
`seteuid(getuid())` modifies **only the EUID**, changing it from 0 to 1000 (`ctf`). The Saved UID (`SUID`) remains **0 (root)**.

Because SUID is still 0:
- Any later call to `seteuid(0)` succeeds (as demonstrated by the program's own `write_audit()` logging function).
- When `system(cmd)` forks a shell child process, the child process is executed with:
  - RUID = 1000
  - EUID = 1000
  - SUID = 0

### The Exploit
Since the child shell inherits `SUID = 0`, any command injected via `system("cat /home/ctf/notes/<arg>")` also runs in an environment where SUID is 0.

1. Inject a command using a semicolon in the filename argument:
   `"welcome.txt; /tmp/restore"`
2. Inside `/tmp/restore.c`, invoke `seteuid(0)`. Because SUID is 0, the kernel permits the process to restore EUID back to root.
3. Read `/flag` with restored root privileges and output the contents.

### Remediation
To drop privileges permanently and prevent regaining root:
```c
if (setresuid(getuid(), getuid(), getuid()) != 0) {
    perror("setresuid");
    exit(1);
}
```
Setting RUID, EUID, and SUID all to `getuid()` permanently discards root privileges and prevents any child from restoring EUID to 0. Additionally, user input passed to command execution should use parameterized APIs (such as `execve`) rather than shell interpolation via `system()`.

## Flag Storage & Deployment (ADR 0004)
In accordance with **ADR 0004**, real event flags live exclusively on the VMs or in GitHub Actions secrets and are never committed to git.
At deployment time, the static container runtime injects the flag via the `FLAG` environment variable through `/entrypoint.sh`, which writes the value to `/flag` with permissions `0600` (owned by `root:root`). The committed files contain only placeholder flags.
