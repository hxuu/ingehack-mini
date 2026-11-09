/* A very important SUID backup helper. It does not do anything, ever. */
#include <stdio.h>
#include <unistd.h>

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    puts("backup: scanning /var/backups ...");
    for (;;) {
        puts("backup: waiting for the restore key ...");
        sleep(3);
    }
}
