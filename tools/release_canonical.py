"""Cross-runtime release digest encoding (versforms.typed-json.v1).

Every value is type tagged. Finite numbers use normalized IEEE-754 binary64
bytes; integers must be exactly representable in JavaScript's safe range.
Object keys follow UTF-16 order. This is an explicit internal encoding, not JCS.
"""
import json
import math
import struct


def canonical(value):
    visiting = set()

    def string(text):
        # Reject lone surrogates instead of letting UTF-8 replacement collide.
        text.encode("utf-8")
        return text

    def node(item):
        if item is None:
            return ["null"]
        if type(item) is bool:
            return ["boolean", item]
        if isinstance(item, str):
            return ["string", string(item)]
        if type(item) in (int, float):
            if not math.isfinite(item) or (float(item).is_integer() and abs(item) > 9007199254740991):
                raise ValueError("Release numbers must be finite and integers must be safe")
            return ["number", struct.pack(">d", 0.0 if item == 0 else item).hex()]
        if type(item) not in (list, dict):
            raise ValueError("Release inputs must be plain JSON")
        identity = id(item)
        if identity in visiting:
            raise ValueError("Cyclic release input")
        visiting.add(identity)
        try:
            if isinstance(item, list):
                return ["array", [node(v) for v in item]]
            if any(not isinstance(k, str) for k in item):
                raise ValueError("Release object keys must be strings")
            keys = sorted(item, key=lambda k: string(k).encode("utf-16-be"))
            return ["object", [[k, node(item[k])] for k in keys]]
        finally:
            visiting.remove(identity)

    return json.dumps(["versforms.typed-json.v1", node(value)], ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)
