"""Stand-in for a slow CLI job; streamed line by line by the Long Task page."""
import sys
import time

steps = int(sys.argv[1]) if len(sys.argv) > 1 else 10
for i in range(1, steps + 1):
    time.sleep(1)
    print(f"[long_task] step {i}/{steps}", flush=True)
print("[long_task] done", flush=True)
