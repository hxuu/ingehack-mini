#include <stddef.h>
#include <stdint.h>

#define EXPORT __attribute__((visibility("default")))
#define RECORD __attribute__((used, section(".rodata.records")))
#define PACKED __attribute__((packed))

#include "constants.h"

extern const unsigned char __ehdr_start[];

static uint32_t load32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void store32(uint8_t *p, uint32_t x) {
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(x >> (8 * i));
}

static int equal(const uint8_t *a, const uint8_t *b, size_t n) {
    unsigned diff = 0;
    for (size_t i = 0; i < n; ++i) diff |= a[i] ^ b[i];
    return diff == 0;
}

static uint32_t fnv32(const uint8_t *p, size_t n) {
    uint32_t h = UINT32_C(2166136261);
    for (size_t i = 0; i < n; ++i) h = (h ^ p[i]) * UINT32_C(16777619);
    return h;
}

static uint64_t fnv64(const uint8_t *p, size_t n) {
    uint64_t h = UINT64_C(14695981039346656037);
    for (size_t i = 0; i < n; ++i) h = (h ^ p[i]) * UINT64_C(1099511628211);
    return h;
}

static uint32_t crc32(const uint8_t *p, size_t n) {
    uint32_t c = UINT32_MAX;
    for (size_t i = 0; i < n; ++i) {
        c ^= p[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            c = (c >> 1) ^ (UINT32_C(0xedb88320) & (0u - (c & 1)));
    }
    return ~c;
}

static uint32_t power(uint32_t base, uint32_t exponent, uint32_t modulus) {
    uint64_t result = 1;
    while (exponent) {
        if (exponent & 1) result = result * base % modulus;
        base = (uint32_t)((uint64_t)base * base % modulus);
        exponent >>= 1;
    }
    return (uint32_t)result;
}

static uint8_t rol8(uint8_t x, unsigned n) {
    n &= 7;
    return (uint8_t)((uint32_t)x << n | (uint32_t)x >> ((8 - n) & 7));
}

static void xxtea(uint32_t v[3], const uint32_t key[4]) {
    uint32_t z = v[2], y, sum = 0;
    for (unsigned round = 0; round < 23; ++round) {
        sum += UINT32_C(0x9e3779b9);
        unsigned e = (sum >> 2) & 3;
        for (unsigned p = 0; p < 3; ++p) {
            y = v[(p + 1) % 3];
            uint32_t mx = ((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)) ^
                          ((sum ^ y) + (key[(p & 3) ^ e] ^ z));
            z = v[p] += mx;
        }
    }
}

static void xtea(uint32_t v[2], const uint32_t key[4]) {
    uint32_t sum = 0;
    for (unsigned round = 0; round < 32; ++round) {
        v[0] += (((v[1] << 4 ^ v[1] >> 5) + v[1]) ^ (sum + key[sum & 3]));
        sum += UINT32_C(0x9e3779b9);
        v[1] += (((v[0] << 4 ^ v[0] >> 5) + v[0]) ^ (sum + key[(sum >> 11) & 3]));
    }
}

EXPORT int check1(const uint8_t *s, size_t n) {
    if (!s || n != 9) return 0;
    uint8_t padded[12] = {0}, encoded[12];
    uint32_t v[3], key[4];
    for (unsigned i = 0; i < 9; ++i) padded[i] = s[i];
    for (unsigned i = 0; i < 3; ++i) v[i] = load32(padded + 4 * i);
    for (unsigned i = 0; i < 4; ++i) key[i] = load32(stage1.key + 4 * i);
    xxtea(v, key);
    for (unsigned i = 0; i < 3; ++i) store32(encoded + 4 * i, v[i]);
    return equal(encoded, stage1.cipher, 12);
}

EXPORT int check2(const uint8_t *s, size_t n) {
    if (!s || n != 9) return 0;
    unsigned diff = 0;
    for (unsigned row = 0; row < 9; ++row) {
        uint32_t sum = 0;
        for (unsigned col = 0; col < 9; ++col)
            sum += stage2.matrix[row * 9 + col] * (uint32_t)s[col];
        diff |= (sum % 257) ^ stage2.target[row];
    }
    return diff == 0;
}

EXPORT int check3(const uint8_t *s, size_t n) {
    if (!s || n != 5) return 0;
    uint8_t state[256], encoded[5];
    unsigned j = 0;
    for (unsigned i = 0; i < 256; ++i) state[i] = (uint8_t)i;
    for (unsigned i = 0; i < 256; ++i) {
        j = (j + state[i] + stage3.key[i % 8]) & 255;
        uint8_t t = state[i]; state[i] = state[j]; state[j] = t;
    }
    unsigned i = 0; j = 0;
    for (unsigned p = 0; p < 5; ++p) {
        i = (i + 1) & 255; j = (j + state[i]) & 255;
        uint8_t t = state[i]; state[i] = state[j]; state[j] = t;
        encoded[p] = s[p] ^ state[(state[i] + state[j]) & 255];
    }
    return equal(encoded, stage3.cipher, 5);
}

static int hex_digit(uint8_t c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

EXPORT int check4(const uint8_t *s, size_t n) {
    if (!s || n != 16) return 0;
    uint64_t fingerprint = fnv64(__ehdr_start, 64) ^ stage4.salt;
    unsigned diff = 0;
    for (unsigned i = 0; i < 8; ++i) {
        int hi = hex_digit(s[2 * i]), lo = hex_digit(s[2 * i + 1]);
        if (hi < 0 || lo < 0) return 0;
        diff |= (unsigned)((hi << 4) | lo) ^ (uint8_t)(fingerprint >> (8 * i));
    }
    return diff == 0;
}

EXPORT int check5(const uint8_t *s, size_t n) {
    if (!s || n != 6) return 0;
    uint8_t accumulator = 0;
    unsigned pc = 0, seen = 0;
    while (pc < sizeof(stage5.code)) {
        uint8_t opcode = stage5.code[pc++];
        if (opcode == 0xff) return pc == sizeof(stage5.code) && seen == 63;
        if (pc >= sizeof(stage5.code)) return 0;
        uint8_t operand = stage5.code[pc++];
        switch (opcode) {
            case 0x11:
                if (operand >= n) return 0;
                accumulator = s[operand]; seen |= 1u << operand; break;
            case 0x22: accumulator ^= operand; break;
            case 0x33: accumulator = rol8(accumulator, operand); break;
            case 0x55: accumulator = (uint8_t)(accumulator + operand); break;
            case 0x44: if (accumulator != operand) return 0; break;
            default: return 0;
        }
    }
    return 0;
}

EXPORT int check6(const uint8_t *s, size_t n) {
    if (!s || n != 12) return 0;
    uint32_t a = 1 + fnv32(s, n) % (stage6.p - 2);
    if (power(stage6.g, a, stage6.p) != stage6.client) return 0;
    uint32_t shared = power(stage6.server, a, stage6.p);
    uint32_t key[4] = {shared, shared ^ UINT32_C(0xa5c31f73),
                      (uint32_t)stage6.nonce, (uint32_t)(stage6.nonce >> 32)};
    uint8_t plaintext[16];
    for (unsigned block = 0; block < 2; ++block) {
        uint64_t counter = stage6.nonce + block;
        uint32_t v[2] = {(uint32_t)counter, (uint32_t)(counter >> 32)};
        uint8_t stream[8];
        xtea(v, key);
        store32(stream, v[0]); store32(stream + 4, v[1]);
        for (unsigned j = 0; j < 8; ++j)
            plaintext[8 * block + j] = stage6.cipher[8 * block + j] ^ stream[j];
    }
    return crc32(plaintext, 12) == load32(plaintext + 12) && equal(s, plaintext, 12);
}
