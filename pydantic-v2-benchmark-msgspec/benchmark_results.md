# Benchmark Results: Pydantic v2 vs msgspec

This report compares the performance of **Pydantic V2** and **msgspec** for **5,000,000** nested `User` objects.
Each framework was run in an isolated subprocess. High-frequency telemetry (50ms interval) monitored CPU spikes and RSS memory usage.

## Overview Table

| Metric | Pydantic V2 | msgspec | Ratio (Pydantic / msgspec) | Winner |
| :--- | :---: | :---: | :---: | :---: |
| **Object Generation Time** | 19.212 s | 8.442 s | 2.28x | **msgspec** |
| **Serialization (to JSON) Time** | 5.004 s | 1.569 s | 3.19x | **msgspec** |
| **Deserialization (from JSON) Time** | 14.726 s | 2.924 s | 5.04x | **msgspec** |
| **Round-trip (JSON <-> Obj) Time** | 20.105 s | 5.105 s | 3.94x | **msgspec** |

## Memory Usage Comparison

| Metric | Pydantic V2 | msgspec | Savings (msgspec vs Pydantic) |
| :--- | :---: | :---: | :---: |
| **Object Generation Peak RAM** | 10727.0 MB | 3499.7 MB | 67.4% |
| **Object Generation RAM Growth** | 10653.0 MB | 3435.2 MB | 7217.8 MB |
| **Serialization (to JSON) Peak RAM** | 12181.0 MB | 4953.4 MB | 59.3% |
| **Serialization (to JSON) RAM Growth** | 0.0 MB | 0.0 MB | 0.0 MB |
| **Deserialization (from JSON) Peak RAM** | 18130.8 MB | 6025.9 MB | 66.8% |
| **Deserialization (from JSON) RAM Growth** | 0.0 MB | 0.0 MB | 0.0 MB |
| **Round-trip (JSON <-> Obj) Peak RAM** | 18130.8 MB | 6025.9 MB | 66.8% |
| **Round-trip (JSON <-> Obj) RAM Growth** | 1453.6 MB | 0.0 MB | 1453.6 MB |

## CPU spikes and utilization

| Phase | Pydantic Avg CPU | Pydantic Peak CPU | msgspec Avg CPU | msgspec Peak CPU |
| :--- | :---: | :---: | :---: | :---: |
| **Object Generation** | 100.9% | 359.4% | 100.4% | 228.0% |
| **Serialization (to JSON)** | 100.3% | 100.3% | 50.3% | 100.7% |
| **Deserialization (from JSON)** | 100.1% | 100.1% | 100.0% | 100.0% |
| **Round-trip (JSON <-> Obj)** | 100.4% | 100.6% | 367.4% | 367.4% |

## Strict Overall Peaks (all captured samples)

| Metric | Pydantic V2 | msgspec |
| :--- | :---: | :---: |
| Peak RSS across all phases | 18130.8 MB | 6025.9 MB |
| Peak CPU across all phases | 359.4% | 367.4% |
| Captured telemetry samples | 232 | 106 |

## Key Observations & Insights

1. **Parsing Speed**: `msgspec` leverages a highly optimized native C/Rust-like decoder designed specifically for speed. It routinely outperforms Pydantic V2 by several factors.
2. **Memory Footprint**: `msgspec` Structs are much closer to Python's slots/C-structs in memory, bypassing the heavy overhead of Pydantic's rich validation models.
3. **Serialization/Deserialization**: Pydantic v2 has a Rust-backed serialization engine (pydantic-core), which is extremely fast, but `msgspec` still outperforms it due to avoiding python-object creation overhead during deserialization.
