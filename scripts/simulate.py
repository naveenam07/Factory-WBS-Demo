"""Send a mix of advisor traffic to the portal API, then save the app logs."""

import json
import os
import random
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_URL = os.getenv("WAVEBANK_URL", "http://localhost:30080")
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "trading-app.log"
KUBECTL = ["kubectl", "--context", "kind-wavebank", "-n", "wavebank"]
ADVISORS = ["A-1001", "A-1003", "A-1007", "A-1012", "A-1015"]
UNTYPED_SLOTS = [1, 3, 5, 7, 9]
SYMBOLS = ["AAPL", "MSFT", "NVDA", "JPM", "KO", "SPY"]


def account_id(advisor_id: str, slot: int) -> str:
    return f"ACC-{(int(advisor_id[2:]) - 1001) * 10 + slot + 1:06d}"


def build_requests(rng: random.Random) -> list[tuple[str, str, str, dict | None]]:
    reqs = []
    for i in range(90):
        adv = ADVISORS[i % len(ADVISORS)]
        reqs.append(("accounts", "GET", f"/api/v1/advisors/{adv}/accounts", None))
    for i in range(40):
        adv = ADVISORS[i % len(ADVISORS)]
        acc = account_id(adv, rng.choice([0, 2, 4]))
        reqs.append(("positions", "GET", f"/api/v1/accounts/{acc}/positions", None))
    for i in range(70):
        adv = ADVISORS[i % len(ADVISORS)]
        body = {
            "advisor_id": adv,
            "account_id": account_id(adv, rng.choice([0, 2, 4, 6, 8])),
            "symbol": rng.choice(SYMBOLS),
            "side": rng.choice(["buy", "sell"]),
            "quantity": rng.randint(1, 50),
        }
        reqs.append(("orders", "POST", "/api/v1/orders", body))
    for i in range(25):
        body = {
            "advisor_id": "A-1012",
            "account_id": account_id("A-1012", UNTYPED_SLOTS[i % len(UNTYPED_SLOTS)]),
            "symbol": rng.choice(SYMBOLS),
            "side": "buy",
            "quantity": rng.randint(1, 50),
        }
        reqs.append(("orders-untyped", "POST", "/api/v1/orders", body))
    for version, count in (("v2", 40), ("v1", 35)):
        for i in range(count):
            adv = ADVISORS[i % len(ADVISORS)]
            body = {
                "advisor_id": adv,
                "from_account_id": account_id(adv, 0),
                "to_account_id": account_id(adv, 2),
                "amount": rng.choice([100, 250, 500, 750]),
            }
            reqs.append((f"transfers-{version}", "POST", f"/api/{version}/transfers", body))
    rng.shuffle(reqs)
    return reqs


def send(req: tuple[str, str, str, dict | None]) -> tuple[str, str]:
    name, method, path, body = req
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE_URL + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return name, str(response.status)
    except urllib.error.HTTPError as exc:
        return name, str(exc.code)
    except OSError as exc:
        return name, type(exc).__name__


def save_logs() -> int:
    output = subprocess.run(
        [*KUBECTL, "logs", "-l", "app=trading-app", "--tail=-1", "--prefix",
         "--max-log-requests=4"],
        check=True, capture_output=True, text=True,
    ).stdout
    LOG_FILE.parent.mkdir(exist_ok=True)
    lines = 0
    with LOG_FILE.open("w") as out:
        for raw in output.splitlines():
            prefix, _, payload = raw.partition(" ")
            try:
                entry = json.loads(payload)
            except json.JSONDecodeError:
                continue
            entry["pod"] = prefix.strip("[]").split("/")[1]
            out.write(json.dumps(entry) + "\n")
            lines += 1
    return lines


def main() -> None:
    reqs = build_requests(random.Random())
    print(f"Sending {len(reqs)} requests to {BASE_URL} ...")
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(send, reqs))
    print(f"Done in {time.monotonic() - started:.1f}s")

    print("\nStatus counts:")
    for status, count in sorted(Counter(status for _, status in results).items()):
        print(f"  {status}: {count}")
    print("\nBy request type:")
    for (name, status), count in sorted(Counter(results).items()):
        print(f"  {name:<16} {status}: {count}")

    time.sleep(2)
    lines = save_logs()
    print(f"\nWrote {lines} log lines to {LOG_FILE}")


if __name__ == "__main__":
    main()
