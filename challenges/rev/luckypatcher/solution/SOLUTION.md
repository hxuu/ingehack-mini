# Solution — luckypatcher

**Flag:** `ingehack{alice_found_the_way_home}`

**Category:** rev (description-only, handout `luckypatcher`)

## Intended path

The handout is an x86-64 Linux ELF, statically linked and **not stripped**:

```console
$ file luckypatcher
luckypatcher: ELF 64-bit LSB executable, x86-64, statically linked, ... not stripped

$ nm -n luckypatcher | grep -E ' (gate_[0-9]+|print_flag|main)$'
00000000004030c0 T print_flag
0000000000403169 T gate_1
...
0000000000403493 T gate_10
00000000004034ed T main
```

Running it normally shows the first dead end:

```console
$ ./luckypatcher
Alice wakes in the Whispering Woods with no memory of the way home.
Ten crossroads stand between her and the porch light.
The forest makes every choice for her -- and every choice is wrong.
Patch its decisions and lead her back.

Alice follows the crow. The trail ends at a cliff. Dead end.
```

Each gate compares the volatile `alice_step` value (always `0`) with its
gate number (`1..10`). Disassembling `gate_1`:

```console
$ objdump -d -M intel --disassemble=gate_1 luckypatcher
0000000000403169 <gate_1>:
  40316d:  mov    eax,DWORD PTR [rip+0xb891d]   # alice_step
  403173:  cmp    eax,0x1
  403176:  jne    4031a7 <gate_1+0x3e>            # dead end
  403178:  ...                                    # good branch: puts + progress update
  4031a7:  ...                                    # puts("... Dead end."); exit(1)
```

Because `alice_step` is `0`, the `jne` is always taken to the dead end. Flip
the opcode at `0x403176` from `75` (`jne`) to `74` (`je`). The `je` is **not**
taken for `0 != 1`, so execution falls through into the good branch, prints
the scene, and folds that gate's key into `progress`.

Repeat for `gate_1` through `gate_10` — ten one-byte patches:

| gate | `jne` address | bytes |
|---|---|---|
| `gate_1` | `0x403176` | `75 2f` → `74 2f` |
| `gate_2` | `0x4031d0` | `75 2f` → `74 2f` |
| `gate_3` | `0x40322a` | `75 2f` → `74 2f` |
| `gate_4` | `0x403284` | `75 2f` → `74 2f` |
| `gate_5` | `0x4032de` | `75 2f` → `74 2f` |
| `gate_6` | `0x403338` | `75 2f` → `74 2f` |
| `gate_7` | `0x403392` | `75 2f` → `74 2f` |
| `gate_8` | `0x4033ec` | `75 2f` → `74 2f` |
| `gate_9` | `0x403446` | `75 2f` → `74 2f` |
| `gate_10` | `0x4034a0` | `75 2f` → `74 2f` |

NOPing the conditional jump (`75 2f` → `90 90`) also works: it falls through
to the good branch.

Patch only some gates and the journey stops at the next dead end. Patching the
`exit` call instead of the jump is not enough: the good branch is what updates
`progress`, and `print_flag` only decodes the flag when `progress` holds the
value produced by all ten good paths. Otherwise it prints
`The forest is still dark. Alice is not home yet.`

## Solver

`solution/solve.py` finds the first conditional jump in every `gate_N`
function and flips `jne` to `je` (short or near form), mapping the virtual
address back to the file offset through `.text`:

```console
$ python3 solution/solve.py files/luckypatcher /tmp/luckypatcher.patched
gate_1: 0x403176  jne -> je  (752f -> 742f)
...
gate_10: 0x4034a0  jne -> je  (752f -> 742f)
patched 10 gates -> /tmp/luckypatcher.patched
```

It does not modify the original handout. Run the patched copy:

```console
$ chmod +x /tmp/luckypatcher.patched
$ /tmp/luckypatcher.patched
...
The porch light is on. She crosses the yard.
The porch light is warm. Alice is home.
ingehack{alice_found_the_way_home}
```

## Rebuild (author side)

```console
$ ./solution/build.sh
```

The flag lives only in `chall.yaml`; `solution/gen_flag.py` encodes it with
the same keystream the binary uses and writes `solution/flag_data.h`.
