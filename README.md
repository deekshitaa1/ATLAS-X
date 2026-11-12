# ATLAS-X
### A Python-Based Storage Engine and Distributed Database Research Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-205%20Passed-success)]()
[![Lint](https://img.shields.io/badge/Ruff-Passing-success)]()
[![Status](https://img.shields.io/badge/Status-Portfolio%20Project-orange)]()

**ATLAS-X** is a Python-based database and distributed storage research
project. It explores how database storage engines manage persistent data,
recover from crashes, organize indexes, handle transactions, replicate
records, and respond to node failures.

The project was built as a hands-on software engineering portfolio project
to explore storage systems, database internals, distributed systems,
reliability, and performance measurement.

GitHub: https://github.com/deekshitaa1/ATLAS-X

---

## 1. Why I Built ATLAS-X

Modern applications depend on databases and distributed storage systems
to store and retrieve information reliably.

I wanted to understand what happens behind a simple database operation:

- How does a database persist a write?
- What happens if a process crashes during a write?
- How are records indexed for faster lookup?
- How do databases manage concurrent transactions?
- How can multiple nodes store replicas of the same data?
- What happens when a distributed node becomes unavailable?
- How can replicas detect and repair inconsistent data?
- How do we measure read and write performance?

Instead of treating a database as a black box, I built ATLAS-X to explore
these internal mechanisms through Python implementations and automated tests.

## 2. What Is ATLAS-X?

ATLAS-X is an educational storage engine and distributed database
research platform.

It contains two related areas:

1. A persistent storage and transaction layer.
2. Distributed storage concepts implemented through an in-memory
   distributed store and supporting components.

The project is designed to demonstrate database and distributed-system
engineering concepts. It is not intended to replace production databases.

## 3. Architecture Overview

```text
                    Applications
                         |
                         v
                  FastAPI REST API
                         |
                         v
                Persistent MVCC Store
                         |
                         v
                   Write-Ahead Log
                         |
                         v
               Persistent Data Recovery


             Distributed Storage Layer
                         |
                         v
                Consistent Hash Ring
                         |
                         v
                 Replica Placement
                         |
                         v
                  Distributed Store
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
           Node A      Node B      Node C
             |           |           |
             +-----------+-----------+
                         |
                         v
             Failure Detection / Recovery
                         |
                         v
             Consistency and Quorum Logic
```

The diagram represents the major project components. The persistent
MVCC API store and the distributed in-memory store are separate
implementations; they are not one fully integrated distributed database.

## 4. Core Features

### 4.1 Write-Ahead Logging (WAL)

The WAL records storage operations before applying them to the in-memory
state.

Implemented concepts:

- Append-only log records.
- Record framing.
- CRC32 checksums.
- Record magic and payload length validation.
- Incomplete trailing record recovery.
- Optional synchronization to disk.
- WAL corruption detection.

**Why it matters:** WAL helps a storage engine recover committed
operations after a process restart.

**Where it is used:** Database recovery systems and storage engines.

### 4.2 Persistent Key-Value Storage

The storage engine supports:

- PUT
- GET
- DELETE
- SCAN
- COUNT
- WAL-based recovery

Operations are recorded in the WAL and replayed during initialization.

### 4.3 Indexing

The project explores multiple indexing structures.

**Hash Index**
- Dictionary-based key lookup.
- Average-case constant-time lookup.

**B+ Tree**
- Sorted key storage.
- Leaf-node linking.
- Node splitting.
- Range scans.
- Search and deletion.

**Where used:** Database indexes, ordered storage, range queries,
and filesystem structures.

Note: The current B+ Tree is an educational in-memory implementation.
Full production-grade deletion rebalancing is not implemented.

### 4.4 Bloom Filter

The Bloom Filter provides probabilistic membership checks.

Features:

- Configurable capacity.
- Configurable false-positive probability.
- Bit-array implementation.
- Double hashing.
- Estimated false-positive rate.

**Why it matters:** It can avoid unnecessary disk or table lookups when
a key is definitely absent.

**Where used:** LSM-based storage systems, caching layers, and
large-scale data retrieval systems.

### 4.5 Log-Structured Merge Tree (LSM)

The LSM implementation explores:

- WAL-backed writes.
- Sorted String Tables (SSTables).
- Bloom filters.
- Flush operations.
- Compaction.
- Tombstones.
- Checkpoint and recovery operations.
- Batch operations.

**Why it matters:** LSM designs optimize write-heavy workloads by
buffering writes and organizing data into sorted tables.

**Where used:** Write-heavy databases and key-value storage engines.

The current LSM implementation is educational and has crash-consistency
limitations around some flush and compaction failure windows. It should
not be treated as production-grade durable storage.

### 4.6 Transactions

ATLAS-X includes staged transaction operations:

- PUT
- DELETE
- GET
- COMMIT
- ROLLBACK
- Batch WAL records

The LSM transaction interface uses a batch record to group operations.

The transaction implementation does not provide full ACID isolation
or snapshot isolation.

### 4.7 Multi-Version Concurrency Control (MVCC)

MVCC stores multiple versions of a key.

Implemented concepts:

- Versioned records.
- Sequence numbers.
- Snapshot reads.
- Read-your-own-writes.
- Write-write conflict detection.
- Transaction commit and rollback.
- Persistent MVCC using WAL.
- Recovery after restart.

**Why it matters:** MVCC allows readers to work with consistent
versions while newer writes are committed.

**Where used:** Relational databases and transactional storage engines.

The current conflict detection is not a complete serializable
isolation implementation.

### 4.8 REST API

The FastAPI layer exposes persistent key-value operations.

Endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Health check |
| PUT | /kv/{key} | Store a value |
| GET | /kv/{key} | Retrieve a value |
| DELETE | /kv/{key} | Delete a value |
| GET | /scan?prefix= | Scan records |

Request example:

```json
{
  "value": "ATLAS-X"
}
```

The API includes input validation for non-finite floating-point values
and returns HTTP 422 for invalid input.

### 4.9 Distributed Storage

The distributed modules explore:

- Consistent hashing.
- Virtual nodes.
- Replica placement.
- In-memory replication.
- Node registry.
- Node failure handling.
- Replica recovery.
- Heartbeat monitoring.
- Failure detection.
- Replica consistency checking.
- Anti-entropy repair.
- Quorum reads and writes.
- Version clocks and versioned values.
- Failure simulation.
- Concurrent store operations.

**Why it matters:** Distributed storage systems must manage node
availability, replica placement, data consistency, and recovery.

**Where used:** Distributed databases, replicated key-value stores,
caching systems, and distributed infrastructure.

Important: The distributed store is an in-memory research implementation.
It does not provide a fully durable, networked, production-grade
distributed database. Quorum operations are not durable atomic
transactions across independent machines.

## 5. Technology Stack

| Technology | Usage |
|---|---|
| Python 3.12 | Main implementation language |
| FastAPI | REST API |
| Pydantic | Request validation |
| Uvicorn | API server |
| pytest | Automated testing |
| Ruff | Linting and code quality |
| Git | Version control |
| GitHub | Source code hosting |

The storage and distributed-system implementations are written in Python.

## 6. Project Structure

```text
ATLAS-X/
|
|-- src/
|   |-- atlas/
|       |-- api.py
|       |-- engine.py
|       |-- wal.py
|       |-- index.py
|       |-- bptree.py
|       |-- bloom.py
|       |-- lsm.py
|       |-- transaction.py
|       |-- mvcc.py
|       |-- persistent_mvcc.py
|       |
|       |-- distributed/
|           |-- hash_ring.py
|           |-- replication.py
|           |-- store.py
|           |-- node_registry.py
|           |-- heartbeat.py
|           |-- failure_detector.py
|           |-- consistency.py
|           |-- quorum.py
|           |-- versioning.py
|
|-- tests/
|   |-- test_wal.py
|   |-- test_engine.py
|   |-- test_index.py
|   |-- test_bptree.py
|   |-- test_bloom.py
|   |-- test_lsm.py
|   |-- test_transactions.py
|   |-- test_mvcc.py
|   |-- test_persistent_mvcc.py
|   |-- test_api.py
|   |-- test_api_edge_cases.py
|   |
|   |-- distributed/
|
|-- benchmarks/
|   |-- benchmark_atlas.py
|   |-- compare_wal_sync.py
|   |-- BENCHMARK_REPORT.md
|
|-- data/
|-- pyproject.toml
|-- README.md
```

## 7. How to Install and Run

### Requirements

- Python 3.12
- Git
- Windows, Linux, or macOS with a compatible Python environment

### Clone the repository

```bash
git clone https://github.com/deekshitaa1/ATLAS-X.git
cd ATLAS-X
```

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install the project

```bash
python -m pip install -e ".[dev]"
```

### Run automated tests

```bash
python -m pytest -q
```

### Run Ruff

```bash
python -m ruff check src tests
```

### Run benchmarks

```bash
python benchmarks/benchmark_atlas.py
python benchmarks/compare_wal_sync.py
```

### Start the REST API

```bash
python -c "import uvicorn; from atlas.api import create_app; uvicorn.run(create_app(), host='127.0.0.1', port=8000)"
```

Open:

```text
http://127.0.0.1:8000/docs
```

The default persistent API data directory is `data/api_store`.

## 8. How to Use the REST API

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### Store a value

```bash
curl -X PUT http://127.0.0.1:8000/kv/user1 \
  -H "Content-Type: application/json" \
  -d "{\"value\":\"ATLAS-X\"}"
```

### Retrieve a value

```bash
curl http://127.0.0.1:8000/kv/user1
```

### Scan records

```bash
curl "http://127.0.0.1:8000/scan?prefix=user"
```

### Delete a value

```bash
curl -X DELETE http://127.0.0.1:8000/kv/user1
```

## 9. Performance Benchmarks

The benchmark script measures write throughput, read throughput,
latency percentiles, and scan time.

Latest recorded local benchmark:

| Metric | Result |
|---|---:|
| Durable write throughput | 1,397.69 ops/sec |
| Write P50 | 0.5990 ms |
| Write P95 | 1.1416 ms |
| Write P99 | 1.7931 ms |
| Read throughput | 468,318.18 ops/sec |
| Read P50 | 0.0021 ms |
| Read P95 | 0.0022 ms |
| Read P99 | 0.0028 ms |
| Scan 250 records | 0.2015 ms |

Environment: Python 3.12.7 on a Windows development machine.

These are single-run measurements for the benchmark workload, not
production performance guarantees. Results depend on hardware,
operating system, data size, and workload.

The separate WAL synchronization comparison uses three runs per
configuration. See `benchmarks/BENCHMARK_REPORT.md` for its methodology
and limitations.

## 10. Testing and Reliability

The project has **205 automated tests passing** in the recorded
verification run.

Test coverage includes:

- WAL framing and corruption handling.
- Storage engine operations.
- Index and B+ Tree behavior.
- Bloom Filter behavior.
- LSM operations and recovery.
- Transaction behavior.
- MVCC and persistent MVCC.
- REST API behavior and edge cases.
- Consistent hashing and replica placement.
- Node failure and recovery.
- Heartbeats and failure detection.
- Consistency checks and anti-entropy repair.
- Quorum safety.
- Version recovery.
- Failure simulation.
- Concurrent store operations.

Run the complete suite with:

```bash
python -m pytest -q
```

## 11. How I Built and How I Plan to Learn ATLAS-X

I developed ATLAS-X incrementally, adding components and validating
them with automated tests.

The engineering workflow includes:

1. Implement a storage component.
2. Write tests for normal behavior.
3. Test edge cases and failure scenarios.
4. Run Ruff to identify code-quality issues.
5. Run the complete test suite.
6. Measure performance using benchmark scripts.
7. Track changes using Git commits.
8. Publish the project on GitHub.

The implementation and test suite are complete for this portfolio
milestone. Understanding every internal concept is a separate learning
goal; this README does not claim that every topic has already been
mastered.

### Learning roadmap

| Stage | Topics to understand |
|---|---|
| 1 | Python, classes, objects, exceptions |
| 2 | Dictionaries, hashing, trees, complexity |
| 3 | Files, binary records, checksums, WAL |
| 4 | Hash indexes, B+ Trees, Bloom Filters |
| 5 | LSM Trees, SSTables, compaction |
| 6 | Transactions, MVCC, concurrency |
| 7 | Consistent hashing and replication |
| 8 | Heartbeats, failure detection, recovery |
| 9 | Quorum, consistency, versioning |
| 10 | Testing, benchmarking, debugging |
| 11 | System design and SDE-I interview explanations |

The goal is to understand each module well enough to explain:

- Why it exists.
- How it works internally.
- Which data structures it uses.
- Its time and space complexity.
- What can fail.
- How the tests verify its behavior.
- What limitations remain.

## 12. Real-World Applications of These Concepts

ATLAS-X is a learning and research implementation. Its concepts are
relevant to:

- Key-value storage systems.
- Database indexing.
- Write-heavy data storage.
- Transaction processing.
- Crash recovery.
- Distributed replication.
- Fault detection and recovery.
- Data consistency verification.
- Performance engineering.

These are examples of where the underlying concepts are used;
ATLAS-X itself is not a drop-in replacement for those systems.

## 13. Current Limitations

ATLAS-X is a portfolio and educational research project.

Known limitations include:

- The distributed store is in-memory and not networked across
  independent machines.
- Distributed quorum writes are not durable atomic transactions.
- The LSM flush and compaction implementation needs stronger
  crash-safe manifest and metadata handling.
- The B+ Tree does not implement full deletion rebalancing.
- Transaction isolation is not fully serializable.
- MVCC history garbage collection is not implemented.
- Persistent storage does not implement multi-process file locking.
- The failure detector requires explicit calls; it has no background
  scheduler.
- Production deployment, security hardening, and large-scale
  performance testing are outside the current scope.

These limitations are documented to distinguish an educational
implementation from a production database.

## 14. Future Improvements

Possible future engineering work:

- Crash-safe LSM manifests and compaction recovery.
- MVCC version garbage collection.
- Stronger transaction isolation.
- Durable distributed replication.
- Network communication between independent nodes.
- Background failure detection.
- More extensive concurrency testing.
- Repeated benchmarks across larger datasets.
- Continuous integration.
- Docker-based development and test environments.

## 15. What This Project Demonstrates

ATLAS-X demonstrates hands-on exploration of:

- Python software engineering.
- Data structures and algorithms.
- File-based persistence.
- Database internals.
- Transaction processing.
- Concurrency concepts.
- Distributed storage algorithms.
- Fault handling and recovery.
- Automated testing.
- Performance measurement.
- Git-based development workflow.

It is intended as a technical portfolio project and a foundation
for deeper study of database internals and distributed systems.

---

## Author

**Deeksha**

GitHub: https://github.com/deekshitaa1

Project: https://github.com/deekshitaa1/ATLAS-X

---

*Built with Python. Tested with pytest. Published on GitHub.*
