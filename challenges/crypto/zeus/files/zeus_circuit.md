# Zeus circuit

Zeus is a 1-round, 2-element hash, structurally identical to Poseidon's round
function:

1. **AddRoundConstant**: add a fixed constant to each state element.
2. **S-box**: square each state element.
3. **Reduce**: reduce modulo `A` using a quotient/remainder pair `(Q, C)`.
4. **Mix**: combine the reduced elements through a fixed matrix.

The circuit's native field is `P`; Zeus's reduction modulus is the separate
small integer `A`.

## Public parameters

```
P   = 21888242871839275222246405745257275088548364400416034343698204186575808495617
A   = 5003
rc0 = 5
rc1 = 9
MDS = [[2, 1],
       [1, 3]]
```

## Runtime circuit

The server chooses `s0` and `s1`, then checks the following rows for the
submitted witness:

```
(s0 + rc0) * (s0 + rc0) = D0
D0 * 1 = A*Q0 + C0

(s1 + rc1) * (s1 + rc1) = D1
D1 * 1 = A*Q1 + C1

(2*C0 + C1) * 1 = out0
(C0 + 3*C1) * 1 = out1
```

The quotients must be positive and all submitted values must be non-zero
elements of the native field. The reduction rows do not constrain the
remainders to be smaller than `A`, which means a non-canonical quotient and
remainder pair can produce a different digest while satisfying every row.
