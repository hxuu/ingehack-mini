import json
import os
import sys
import secrets

A = 5003
P = 21888242871839275222246405745257275088548364400416034343698204186575808495617
RC0, RC1 = 5, 9
M00, M01, M10, M11 = 2, 1, 1, 3
FLAG = os.environ.get("FLAG", "ingehack{??????????????????????????????????????????????}")


class Challenge:
    def __init__(self):
        self.s0 = secrets.randbelow(A)
        self.s1 = secrets.randbelow(A)

        self.D0 = (self.s0 + RC0) ** 2
        self.D1 = (self.s1 + RC1) ** 2

        trueQ0, trueC0 = divmod(self.D0, A)
        trueQ1, trueC1 = divmod(self.D1, A)
        self.canonical_out0 = M00 * trueC0 + M01 * trueC1
        self.canonical_out1 = M10 * trueC0 + M11 * trueC1

    def verify_circuit(self, Q0, C0, Q1, C1, out0, out1):
        """
        This is Section 3 of zeus_circuit.md, checked directly:

            D0 * 1 = A*Q0 + C0
            D1 * 1 = A*Q1 + C1
            (M00*C0 + M01*C1) * 1 = out0
            (M10*C0 + M11*C1) * 1 = out1

        The quotient positivity and field-membership rows are also enforced.
        """
        row_inputs_in_field = all(0 < v < P for v in (Q0, C0, Q1, C1, out0, out1))

        row_reduce_0 = (A * Q0 + C0) == self.D0
        row_reduce_1 = (A * Q1 + C1) == self.D1
        row_mix_0 = (M00 * C0 + M01 * C1) == out0
        row_mix_1 = (M10 * C0 + M11 * C1) == out1

        row_quotient_positive = (Q0 > 0) and (Q1 > 0)

        produces_different_digest = (out0, out1) != (self.canonical_out0, self.canonical_out1)

        valid_witness = (
            row_inputs_in_field
            and row_reduce_0
            and row_reduce_1
            and row_mix_0
            and row_mix_1
            and row_quotient_positive
        )

        return (valid_witness, produces_different_digest)

    def challenge(self, your_input):
        if "option" not in your_input:
            return {"error": "missing `option`"}

        handlers = {
            "get_id": self._h_get_id,
            "submit": self._h_submit,
        }
        handler = handlers.get(your_input["option"])
        if handler is None:
            return {"error": "invalid option"}
        return handler(your_input)

    def _h_get_id(self, your_input):
        return {
            "s0": self.s0,
            "s1": self.s1,
            "canonical_out0": self.canonical_out0,
            "canonical_out1": self.canonical_out1,
        }

    def _h_submit(self, your_input):
        try:
            Q0 = int(your_input["Q0"])
            C0 = int(your_input["C0"])
            Q1 = int(your_input["Q1"])
            C1 = int(your_input["C1"])
            out0 = int(your_input["out0"])
            out1 = int(your_input["out1"])
        except Exception as e:
            return {"error": str(e)}

        valid_witness, produces_different_digest = self.verify_circuit(
            Q0, C0, Q1, C1, out0, out1
        )

        if not valid_witness:
            return {"msg": "rejected: a row failed"}

        if produces_different_digest:
            return {"msg": FLAG}
        return {"msg": "nuh uh, you specifically got all the free food you needed!!"}


if __name__ == "__main__":
    chal = Challenge()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            res = chal.challenge(json.loads(line))
        except Exception as e:
            res = {"error": str(e)}
        print(json.dumps(res), flush=True)
