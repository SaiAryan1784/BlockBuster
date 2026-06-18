"""
Small shared helpers. sanitize_floats() exists because Starlette's default
JSONResponse uses json.dumps(allow_nan=False) (strict JSON), but our
simulation can legitimately produce inf for a fully-blocked corridor's
V/C ratio (capacity -> 0 -> demand/0 = inf). That's correct simulation
behavior, not a bug -- we just need to make it JSON-safe before it leaves
the API. inf/nan become null on the wire; the frontend should treat a
null vc_ratio as "fully blocked / undefined".
"""
import math


def sanitize_floats(obj):
    if isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_floats(v) for v in obj]
    if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
        return None
    return obj