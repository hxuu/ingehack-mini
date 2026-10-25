#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>

#define NOTES_DIR "/home/ctf/notes/"
#define AUDIT_LOG "/var/log/auditdrop.log"
#define MAX_PATH 512

void write_audit(const char *msg) {
    seteuid(0);
    int fd = open(AUDIT_LOG, O_WRONLY | O_APPEND | O_CREAT, 0644);
    if (fd >= 0) {
        write(fd, msg, strlen(msg));
        write(fd, "\n", 1);
        close(fd);
    }
    seteuid(getuid());
}

int main(int argc, char **argv) {
    char path[MAX_PATH];
    char cmd[MAX_PATH * 2];
    char audit[1024];

    printf("=== AuditDrop v1.0 ===\n");
    printf("Now with privilege dropping! 100%% secure\n\n");

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <filename>\n", argv[0]);
        return 1;
    }

    snprintf(path, sizeof(path), "%s%s", NOTES_DIR, argv[1]);

    if (strncmp(path, NOTES_DIR, strlen(NOTES_DIR)) != 0) {
        fprintf(stderr, "Error: path must be inside %s\n", NOTES_DIR);
        return 1;
    }

    if (seteuid(getuid()) != 0) {
        perror("seteuid");
        return 1;
    }

    printf("[*] Reading: %s\n\n", path);

    snprintf(cmd, sizeof(cmd), "cat %s", path);
    system(cmd);

    snprintf(audit, sizeof(audit), "user=%s file=%s",
             getenv("USER") ? getenv("USER") : "unknown", path);
    write_audit(audit);

    return 0;
}
