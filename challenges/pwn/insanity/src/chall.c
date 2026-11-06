#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>


int main (int argc, char* argv[]) {
	setbuf(stdin, 0);
	setbuf(stdout, 0);
	setbuf(stderr, 0);
	puts("This is THE insanity check :)");
	

	char input[32];
	char guess[32];

	int fd = open("/dev/urandom", 0);
	if (fd == -1) {
		fputs("nah", stderr);
		exit(1);
	}
	read(fd, guess, sizeof(guess));
	printf("your guess: ");
	gets(input);

	if (memcmp(input, guess, 32) == 0) {
		puts("nice");
		system("cat flag.txt");
	} else {
		puts(":(");
	}
	return 0;
}
