import argparse
import sys

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Run API smoke tests against a deployed service")
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    response = requests.get(f"{base_url}/api/health", timeout=30)
    response.raise_for_status()

    payload = response.json()
    if payload.get("status") != "ok":
        print(f"Unexpected health payload: {payload}", file=sys.stderr)
        sys.exit(1)

    print("Smoke test passed")


if __name__ == "__main__":
    main()
