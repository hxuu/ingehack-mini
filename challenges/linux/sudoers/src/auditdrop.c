#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <dlfcn.h>
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
    char audit[1024];

    printf("=== AuditDrop v1.0 ===\n");
    printf("Now with privilege dropping! 100%% secure\n\n");

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <plugin>\n", argv[0]);
        return 1;
    }

    snprintf(path, sizeof(path), "%s%s", NOTES_DIR, argv[1]);

    if (strncmp(path, NOTES_DIR, strlen(NOTES_DIR)) != 0) {
        fprintf(stderr, "Error: plugin must live inside %s\n", NOTES_DIR);
        return 1;
    }

    /* Drop root before touching anything the user controls. */
    if (seteuid(getuid()) != 0) {
        perror("seteuid");
        return 1;
    }

    printf("[*] Loading plugin: %s\n\n", path);

    /*
     * Note renderers are shared objects in the user's notes directory.
     * Loading one runs its code inside this process, after the drop above.
     */
    void *plugin = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!plugin) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        snprintf(audit, sizeof(audit), "user=%s plugin=%s status=load-error",
                 getenv("USER") ? getenv("USER") : "unknown", path);
        write_audit(audit);
        return 1;
    }

    int (*audit_note)(const char *) =
        (int (*)(const char *))dlsym(plugin, "audit_note");
    if (!audit_note) {
        fprintf(stderr, "dlsym: %s\n", dlerror());
        dlclose(plugin);
        return 1;
    }

    audit_note(path);

    dlclose(plugin);

    snprintf(audit, sizeof(audit), "user=%s plugin=%s status=ok",
             getenv("USER") ? getenv("USER") : "unknown", path);
    write_audit(audit);

    return 0;
}
