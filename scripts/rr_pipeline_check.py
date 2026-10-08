"""Smoke-test bid_factory.pipe on the RocketRide development connection.

Run from the workspace root:  python scripts/rr_pipeline_check.py [document]
Reads ROCKETRIDE_URI / ROCKETRIDE_APIKEY from .env. Never prints secrets.
"""
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rocketride import RocketRideClient

ROOT = Path(__file__).resolve().parents[1]


async def main(doc: Path) -> int:
    load_dotenv(ROOT / ".env")
    client = RocketRideClient()
    await client.connect()
    token = None
    try:
        started = await client.use(filepath=str(ROOT / "bid_factory.pipe"), pipelineTraceLevel="summary")
        token = started["token"]
        print("task started")
        mimetype = "application/pdf" if doc.suffix.lower() == ".pdf" else None
        try:
            result = await asyncio.wait_for(
                client.send(token, doc.read_bytes(), objinfo={"name": doc.name}, mimetype=mimetype), timeout=180
            )
        except Exception as exc:  # report and fall through to status
            print(f"send failed: {type(exc).__name__}: {exc}")
            result = None
        status = await client.get_task_status(token)
        print("status:", json.dumps({k: status.get(k) for k in ("state", "error", "errors", "exitCode", "exitMessage") if k in status}, default=str))
        if result is not None:
            print("result keys:", sorted(result.keys()))
            for key in ("requirements", "answers", "text", "table"):
                if key in result:
                    print(f"--- {key} (truncated) ---")
                    print(json.dumps(result[key], default=str)[:1500])
            if "_trace" in result:
                print("--- _trace (truncated) ---")
                print(json.dumps(result["_trace"], default=str)[:3000])
        return 0 if result and (result.get("requirements") or result.get("answers")) else 1
    finally:
        if token:
            try:
                await client.terminate(token)
            except Exception:
                pass
        await client.disconnect()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "real_rfp.pdf"
    sys.exit(asyncio.run(main(target)))
