import statistics
import tempfile
import time
from pathlib import Path

from atlas.persistent_mvcc import PersistentMVCCStore


def run_benchmark(sync: bool, count: int = 500) -> tuple[float, float]:
    latencies = []

    with tempfile.TemporaryDirectory() as folder:
        store = PersistentMVCCStore(Path(folder), sync=sync)
        total_start = time.perf_counter()

        for number in range(count):
            start = time.perf_counter()
            store.put(f"key:{number}", number)
            latencies.append((time.perf_counter() - start) * 1000)

        total_seconds = time.perf_counter() - total_start
        store.close()

    throughput = count / total_seconds
    p95 = sorted(latencies)[round(0.95 * (count - 1))]
    return throughput, p95


for sync in (True, False):
    results = [run_benchmark(sync) for _ in range(3)]
    throughputs = [result[0] for result in results]
    p95_values = [result[1] for result in results]

    print(f"\nWAL sync={sync}")
    print(f"Median throughput: {statistics.median(throughputs):.2f} ops/sec")
    print(f"Median P95 latency: {statistics.median(p95_values):.4f} ms")
