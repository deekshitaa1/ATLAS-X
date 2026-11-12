# ATLAS-X Performance Benchmark Report

Date: 2026-11-12

## Environment
- Language: Python 3.12.7
- Storage: PersistentMVCCStore
- WAL: Enabled
- Runs per configuration: 3
- Operations per run: 500
- Measurement: Median of 3 runs

## Results

| Metric | WAL sync=True | WAL sync=False |
|---|---:|---:|
| Throughput (ops/sec) | 814.55 | 16,894.40 |
| P95 latency (ms) | 1.8075 | 0.1140 |

## Analysis

- sync=False measured approximately 20.7x higher throughput.
- P95 latency was approximately 93.7% lower.
- sync=True provides stronger durability through WAL synchronization.
- sync=False may lose recent writes after an OS crash or power failure.
- sync=True remains the default durability configuration.

## Limitations

- Results are from one Windows development machine.
- Only 500 writes per run were measured.
- Results are preliminary, not production performance guarantees.
- More workloads, machines, repetitions, and concurrent benchmarks are needed.

## Reproduction

Run:

    python benchmarks/compare_wal_sync.py

    python benchmarks/benchmark_atlas.py
