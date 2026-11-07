"""Review routing without network calls; --live explicitly probes one provider.

Usage: uv run python -m app.llm.smoke
       uv run python -m app.llm.smoke --live --provider vertex --tier free --task items
"""

import argparse
import asyncio
import json
import os

from pydantic import BaseModel, Field

from app.llm.gateway import Gateway, GatewayError, Message, Routing, load_routing
from app.llm.providers import default_gateway


class SmokeAnswer(BaseModel):
    text_vi: str = Field(min_length=1)


def configuration(routing: Routing) -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = []
    for tier, tasks in routing.tiers.items():
        for task, routes in tasks.items():
            for route in routes:
                model = os.path.expandvars(route.model)
                rows.append(
                    {
                        "tier": tier,
                        "task": task,
                        "provider": route.provider,
                        "family": route.family,
                        "model_configured": "$" not in model
                        and route.family in model.casefold()
                        and not model.endswith(":free"),
                    }
                )
    return rows


async def probe(gateway: Gateway, provider: str, tier: str, task: str) -> dict[str, str | int]:
    if task == "verify":
        raise ValueError("Probe a generation task; verification requires actual generator metadata")
    routes = [
        route
        for route in gateway.routing.tiers.get(tier, {}).get(task, [])
        if route.provider == provider
    ]
    isolated = Gateway(
        Routing(tiers={tier: {task: routes}}),
        gateway.adapters,
        attempts_per_model=1,
        total_timeout=40,
    )
    result = await isolated.complete_with_metadata(
        task,
        tier,
        "Đây là kiểm tra kết nối. Trả về JSON ngắn bằng tiếng Việt.",
        [Message(role="user", content='Trả về {"text_vi":"Kết nối thành công."}')],
        SmokeAnswer,
    )
    return {
        "provider": result.route.provider,
        "family": result.route.family,
        "status": "ok",
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P3 routing check; no network unless --live is set."
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--provider",
        choices=["vertex", "bedrock", "openrouter", "deepseek", "gemini"],
        default="deepseek",
    )
    parser.add_argument("--tier", choices=["free", "pro"], default="free")
    parser.add_argument("--task", default="items")
    args = parser.parse_args()
    from app.config import get_settings

    get_settings().export_worker_environment()
    if not args.live:
        print(json.dumps({"live": False, "routes": configuration(load_routing())}, indent=2))
        return
    try:
        print(
            json.dumps(asyncio.run(probe(default_gateway(), args.provider, args.tier, args.task)))
        )
    except (GatewayError, ValueError):
        print(
            json.dumps(
                {
                    "provider": args.provider,
                    "status": "failed",
                    "reason": "Check model IDs, credentials, region and account access.",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
