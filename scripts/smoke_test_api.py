import argparse
import sys
import time
from typing import Any

import requests


def check_health(base_url: str, timeout: int) -> tuple[bool, str]:
    url = f"{base_url}/api/health"
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return False, f"request failed: {exc}"

    body = response.text[:500]
    if response.status_code != 200:
        return False, f"HTTP {response.status_code}: {body}"

    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        return False, f"invalid JSON response: {body}"

    if payload.get("status") != "ok":
        return False, f"unexpected payload: {payload}"

    return True, f"healthy payload: {payload}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run API smoke tests against a deployed service")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--delay-seconds", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    last_message = "not checked"

    for attempt in range(1, args.attempts + 1):
        ok, message = check_health(base_url, args.timeout)
        last_message = message
        print(f"Attempt {attempt}/{args.attempts}: {message}")

        if ok:
            print("Smoke test passed")
            return

        if attempt < args.attempts:
            time.sleep(args.delay_seconds)

    print(f"Smoke test failed after {args.attempts} attempts: {last_message}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
