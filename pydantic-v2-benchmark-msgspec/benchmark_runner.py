import argparse
import gc
import json
import os
import sys
import time
from datetime import datetime
from uuid import UUID

# Import the models from main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import threading

from main import MsgspecAddress, MsgspecUser, PydanticAddress, PydanticUser


class ResourceMonitor:
    def __init__(self, interval=0.05):
        self.interval = interval
        self.samples = []
        self.running = False
        self._thread = None
        self.ticks_per_sec = os.sysconf("SC_CLK_TCK")

    def start(self):
        self.running = True
        self.samples = []
        self.start_time = time.perf_counter()
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()
        return self.samples

    def _get_cpu_ticks(self):
        try:
            with open("/proc/self/stat", "r") as f:
                parts = f.read().split()
            # 13 is utime, 14 is stime
            return float(parts[13]) + float(parts[14])
        except Exception:
            return 0.0

    def _get_mem_rss(self):
        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return float(line.split()[1]) / 1024.0  # Convert KB to MB
        except Exception:
            return 0.0
        return 0.0

    def _monitor(self):
        prev_ticks = self._get_cpu_ticks()
        prev_time = time.perf_counter()

        while self.running:
            time.sleep(self.interval)
            now = time.perf_counter()
            current_ticks = self._get_cpu_ticks()
            current_rss = self._get_mem_rss()

            dt = now - prev_time
            dticks = current_ticks - prev_ticks

            if dt > 0:
                cpu_util = (dticks / self.ticks_per_sec) / dt * 100
            else:
                cpu_util = 0.0

            self.samples.append(
                {"time": now - self.start_time, "cpu": cpu_util, "mem": current_rss}
            )

            prev_ticks = current_ticks
            prev_time = now


def generate_raw_user_dicts(n: int):
    """Yield raw user dicts one at a time.

    Implemented as a generator so the caller never holds all `n` dicts in
    memory alongside the materialized model instances — this is critical at
    high limits (e.g. 5M) where holding both would trigger the OOM killer.
    """
    for i in range(n):
        yield {
            "id": f"de305d54-75b4-431b-adb2-eb6b9e5460{i % 100:02d}",
            "name": f"User {i}",
            "email": f"user_{i}@example.com",
            "age": 20 + (i % 60),
            "is_active": i % 2 == 0,
            "created_at": "2026-06-25T19:51:20Z",
            "address": {
                "street": f"{i} Main St",
                "city": "San Francisco",
                "country": "United States",
                "postal_code": f"9410{i % 10}",
            },
            "tags": ["tag1", "tag2", f"tag{i % 5}"],
        }


def run_pydantic_benchmark(limit: int, sample_interval: float):
    from pydantic import TypeAdapter

    monitor = ResourceMonitor(interval=sample_interval)
    results = {}

    # 1. Object instantiation (Validation)
    #    Dicts are produced lazily by the generator so we never hold the
    #    full list of raw dicts alongside the materialized model instances.
    monitor.start()
    t_start = time.perf_counter()
    users = [PydanticUser(**d) for d in generate_raw_user_dicts(limit)]
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["generation"] = {"time_s": t_end - t_start, "samples": samples}
    gc.collect()

    # 2. Serialization
    adapter = TypeAdapter(list[PydanticUser])
    monitor.start()
    t_start = time.perf_counter()
    json_bytes = adapter.dump_json(users)
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["serialization"] = {"time_s": t_end - t_start, "samples": samples}

    # Free the source objects as soon as the JSON bytes exist.
    users = None
    gc.collect()

    # 3. Deserialization
    monitor.start()
    t_start = time.perf_counter()
    users = adapter.validate_json(json_bytes)
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["deserialization"] = {"time_s": t_end - t_start, "samples": samples}

    # Free the JSON bytes before the round-trip allocates its own copy.
    json_bytes = None
    gc.collect()

    # 4. Round-trip: serialize, free the source objects, then deserialize.
    monitor.start()
    t_start = time.perf_counter()
    serialized = adapter.dump_json(users)
    users = None
    deserialized = adapter.validate_json(serialized)
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["round_trip"] = {"time_s": t_end - t_start, "samples": samples}

    return results


def run_msgspec_benchmark(limit: int, sample_interval: float):
    import msgspec

    monitor = ResourceMonitor(interval=sample_interval)
    results = {}

    # 1. Object instantiation (Validation/Coercion)
    #    Dicts are produced lazily by the generator so we never hold the
    #    full list of raw dicts alongside the materialized model instances.
    monitor.start()
    t_start = time.perf_counter()
    users = [msgspec.convert(d, MsgspecUser) for d in generate_raw_user_dicts(limit)]
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["generation"] = {"time_s": t_end - t_start, "samples": samples}
    gc.collect()

    # 2. Serialization
    monitor.start()
    t_start = time.perf_counter()
    json_bytes = msgspec.json.encode(users)
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["serialization"] = {"time_s": t_end - t_start, "samples": samples}

    # Free the source objects as soon as the JSON bytes exist.
    users = None
    gc.collect()

    # 3. Deserialization
    monitor.start()
    t_start = time.perf_counter()
    users = msgspec.json.decode(json_bytes, type=list[MsgspecUser])
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["deserialization"] = {"time_s": t_end - t_start, "samples": samples}

    # Free the JSON bytes before the round-trip allocates its own copy.
    json_bytes = None
    gc.collect()

    # 4. Round-trip: serialize, free the source objects, then deserialize.
    monitor.start()
    t_start = time.perf_counter()
    serialized = msgspec.json.encode(users)
    users = None
    deserialized = msgspec.json.decode(serialized, type=list[MsgspecUser])
    t_end = time.perf_counter()
    samples = monitor.stop()

    results["round_trip"] = {"time_s": t_end - t_start, "samples": samples}

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework", choices=["pydantic", "msgspec"], required=True)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--sample-interval", type=float, default=0.05)
    args = parser.parse_args()

    gc.enable()

    if args.framework == "pydantic":
        res = run_pydantic_benchmark(args.limit, args.sample_interval)
    else:
        res = run_msgspec_benchmark(args.limit, args.sample_interval)

    print(json.dumps(res))
