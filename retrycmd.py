#!/usr/bin/env python3
"""retrycmd - Retry commands with backoff strategies.

One file. Zero deps. Never fail once.

Usage:
  retrycmd.py -- curl https://flaky-api.com     → retry 3x with exponential backoff
  retrycmd.py -n 5 --delay 2 -- ./deploy.sh     → 5 retries, 2s base delay
  retrycmd.py --strategy linear --delay 5 -- cmd → linear backoff
  retrycmd.py --until-success -- ./check.sh      → retry until exit 0
"""

import argparse
import subprocess
import sys
import time


def backoff(strategy: str, attempt: int, base: float, max_delay: float) -> float:
    if strategy == "constant":
        delay = base
    elif strategy == "linear":
        delay = base * attempt
    elif strategy == "exponential":
        delay = base * (2 ** (attempt - 1))
    else:
        delay = base
    return min(delay, max_delay)


def main():
    p = argparse.ArgumentParser(description="Retry commands with backoff")
    p.add_argument("command", nargs=argparse.REMAINDER)
    p.add_argument("-n", "--retries", type=int, default=3)
    p.add_argument("-d", "--delay", type=float, default=1.0, help="Base delay seconds")
    p.add_argument("--max-delay", type=float, default=60)
    p.add_argument("--strategy", choices=["constant", "linear", "exponential"], default="exponential")
    p.add_argument("--until-success", action="store_true", help="Retry indefinitely until exit 0")
    p.add_argument("-q", "--quiet", action="store_true")
    args = p.parse_args()

    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        p.print_help()
        return 1

    max_attempts = 999999 if args.until_success else args.retries + 1
    for attempt in range(1, max_attempts + 1):
        if not args.quiet:
            label = f"[attempt {attempt}]" if attempt > 1 else ""
            if label:
                print(f"  {label} {' '.join(cmd)}", file=sys.stderr)

        r = subprocess.run(cmd)
        if r.returncode == 0:
            return 0

        if attempt >= max_attempts:
            break

        delay = backoff(args.strategy, attempt, args.delay, args.max_delay)
        if not args.quiet:
            print(f"  ⚠️  Exit {r.returncode}, retrying in {delay:.1f}s...", file=sys.stderr)
        time.sleep(delay)

    if not args.quiet:
        print(f"  ❌ Failed after {attempt} attempts", file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
