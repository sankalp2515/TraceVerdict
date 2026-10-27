"""JSON bridge only; the implementation under test is the product's Python engine."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "packages/core"), str(ROOT / "services/gateway")]
from intentseal_gateway.cases.world_model import WorldModel, decide, entity_id_from_name, normalize_name  # noqa: E402

request = json.load(sys.stdin)
world = WorldModel(request["namespace"], request.get("state"), request.get("clock"))
operation, args = request["operation"], request["args"]
try:
    if operation == "normalize":
        result = normalize_name(args)
    elif operation == "identity":
        result = entity_id_from_name(*args)
    elif operation == "decide":
        result = decide(args)
    elif operation == "ingest":
        result = world.ingest(args)
    elif operation == "upsert":
        result = world.upsert_entity(args)
    elif operation == "relate":
        result = world.relate(args)
    elif operation == "shape":
        result = world.state_shape_canonical()
    elif operation == "audit":
        result = world.audit()
    elif operation == "neighbors":
        result = world.neighbors(args[0], **args[1])
    else:
        raise ValueError("unsupported bridge operation")
    print(json.dumps({"result": result, "state": world.data}))
except Exception as exc:
    print(json.dumps({"error": type(exc).__name__}))
