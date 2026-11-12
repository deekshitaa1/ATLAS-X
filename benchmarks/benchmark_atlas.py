from __future__ import annotations

import statistics
import tempfile
import time
from pathlib import Path

from atlas.persistent_mvcc import PersistentMVCCStore


def percentile(values: list[float], percent: int) -> float:
    ordered = sorted(values)
    index = round((percent / 100) * (len(ordered) - 1))
    return ordered[index]


def benchmark(label: str, operation, count: int) -> None:
    latencies = []
    start = time.perf_counter()

    for number in range(count):
        operation(number)
        latencies.append((time.perf_counter() - start) * 1000)
        start = time.perf_counter()

    total_seconds = sum(latencies) / 1000
    throughput = count / total_seconds if total_seconds else 0

    print(f"\n{label}")
    print(f"Operations: {count}")
    print(f"Throughput: {throughput:.2f} ops/sec")
    print(f"P50: {percentile(latencies, 50):.4f} ms")
    print(f"P95: {percentile(latencies, 95):.4f} ms")
    print(f"P99: {percentile(latencies, 99):.4f} ms")
    print(f"Mean: {statistics.mean(latencies):.4f} ms")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="atlas_benchmark_") as folder:
        store = PersistentMVCCStore(Path(folder), sync=True)
        count = 250

        benchmark(
            "WRITE BENCHMARK (WAL sync enabled)",
            lambda number: store.put(f"key:{number}", {"value": number}),
            count,
        )

        benchmark(
            "READ BENCHMARK",
            lambda number: store.get(f"key:{number % count}"),
            1000,
        )

        start = time.perf_counter()
        result = store.scan()
        scan_seconds = time.perf_counter() - start

        print("\nSCAN BENCHMARK")
        print(f"Records scanned: {len(result)}")
        print(f"Scan time: {scan_seconds * 1000:.4f} ms")

        store.close()


if __name__ == "__main__":
    main()
