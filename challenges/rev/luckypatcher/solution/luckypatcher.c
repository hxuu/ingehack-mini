/*
 * luckypatcher -- Ingehack Mini rev challenge.
 *
 * Author-side source. The shipped artifact is files/luckypatcher: a
 * statically linked, non-stripped x86-64 ELF. Alice's ten gates compare a
 * volatile value against 1..10; the value is always 0, so every gate takes
 * its dead-end branch. The player flips the ten conditional jumps so the
 * good branch runs, which folds a key into `progress`. print_flag only
 * decodes the flag for the final progress value, so skipping gates (or
 * patching only some of them) is not enough.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "flag_data.h"

static volatile int alice_step = 0;
static uint32_t progress = 0;

static unsigned char next_key(uint32_t *state) {
    *state = *state * 1664525u + 1013904223u;
    return (unsigned char)((*state >> 24) & 0xffu);
}

void print_flag(uint32_t seed) {
    uint32_t state = seed;
    unsigned char k = next_key(&state);

    if ((unsigned char)(FLAG_ENC[0] ^ k) != (unsigned char)'i') {
        puts("The forest is still dark. Alice is not home yet.");
        return;
    }

    puts("The porch light is warm. Alice is home.");
    putchar((int)(FLAG_ENC[0] ^ k));
    for (int i = 1; i < FLAG_LEN; i++) {
        k = next_key(&state);
        putchar((int)(FLAG_ENC[i] ^ k));
    }
    putchar('\n');
}

#define GATE(num, good, bad)                                                   \
    void gate_##num(void) {                                                    \
        if (alice_step == (num)) {                                             \
            puts(good);                                                        \
            progress = progress * 1664525u + 1013904223u + GATE_KEYS[(num) - 1]; \
            return;                                                            \
        }                                                                      \
        puts(bad);                                                             \
        exit((num));                                                           \
    }

GATE(1,
     "Alice ignores the crow and takes the mossy trail. The trees thin out.",
     "Alice follows the crow. The trail ends at a cliff. Dead end.")
GATE(2,
     "She crosses the rope bridge one careful step at a time.",
     "The ropes snap. The river below is loud. Dead end.")
GATE(3,
     "The lantern is real. She follows it into a quiet clearing.",
     "The lantern was a swamp fire. The ground gives way. Dead end.")
GATE(4,
     "She crawls through the hollow oak and finds a path on the far side.",
     "Something growls inside the oak. She backs into thorns. Dead end.")
GATE(5,
     "She follows the river downstream until she hears a bell.",
     "The current drags her into the rapids. Dead end.")
GATE(6,
     "She reads the runes: the stones point north.",
     "The runes are a warning. The stones close in. Dead end.")
GATE(7,
     "She takes the narrow passage. Fresh air waits at the end.",
     "The tunnel collapses behind her. Dead end.")
GATE(8,
     "She climbs the crumbling staircase toward the dawn.",
     "The steps crumble under her feet. Dead end.")
GATE(9,
     "The iron gate opens at her touch.",
     "The gate is locked. The key is lost. Dead end.")
GATE(10,
     "The porch light is on. She crosses the yard.",
     "The house is empty. The light was a memory. Dead end.")

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);

    puts("Alice wakes in the Whispering Woods with no memory of the way home.");
    puts("Ten crossroads stand between her and the porch light.");
    puts("The forest makes every choice for her -- and every choice is wrong.");
    puts("Patch its decisions and lead her back.");
    putchar('\n');

    gate_1();
    gate_2();
    gate_3();
    gate_4();
    gate_5();
    gate_6();
    gate_7();
    gate_8();
    gate_9();
    gate_10();

    print_flag(progress);
    return 0;
}
