# Pydantic v2 Benchmark

A performance and resource benchmark comparing **Pydantic v2** and **msgspec** for object
generation, JSON serialization, deserialization, and round-trip processing of nested
`User` objects. Each framework is run in an isolated subprocess while a background
thread samples CPU utilization and RSS memory at a 50ms interval.

## Project Structure

| File                  | Purpose                                                                                  |
| :-------------------- | :--------------------------------------------------------------------------------------- |
| `main.py`             | Defines the equivalent `User`/`Address` models for both Pydantic v2 and msgspec.        |
| `benchmark_runner.py` | Runs a single framework benchmark (one of `pydantic` / `msgspec`) and emits JSON results. |
| `run_benchmarks.py`   | Orchestrator: runs both frameworks in subprocesses and generates a Markdown report.       |

## Benchmarked Phases

For each framework, the following phases are timed and monitored:

1. **Object Generation** — instantiating `User` objects from raw dictionaries
   (Pydantic `BaseModel(**d)` vs `msgspec.convert(d, User)`).
2. **Serialization** — converting objects to JSON bytes
   (Pydantic `TypeAdapter.dump_json` vs `msgspec.json.encode`).
3. **Deserialization** — converting JSON bytes back to objects
   (Pydantic `TypeAdapter.validate_json` vs `msgspec.json.decode`).
4. **Round-trip** — serialize then immediately deserialize.

## Resource Monitoring

`ResourceMonitor` in `benchmark_runner.py` runs a daemon thread that samples:

- **CPU utilization** — derived from `/proc/self/stat` (`utime` + `stime` ticks,
  normalized by `SC_CLK_TCK` and elapsed wall time).
- **RSS memory** — read from `/proc/self/status` (`VmRSS`, in MB).

> Note: The monitor reads from `/proc`, so it only works on Linux.

## Memory Management

At high limits (e.g. 5M objects), peak memory — not steady-state — is the
crash risk. The Linux OOM killer is triggered when multiple full-size data
structures (raw dicts, model instances, JSON bytes) coexist in RAM.

`benchmark_runner.py` is designed to minimize peak memory by ensuring only one
large structure of each kind is alive at a time:

- **Lazy dict generation** — `generate_raw_user_dicts` is a generator (`yield`),
  so raw input dicts are produced one at a time during object instantiation.
  The full list of 5M dicts is never materialized alongside the model instances.
- **Early release of source objects** — `users` is freed immediately after
  serialization produces `json_bytes`, rather than being held through
  deserialization. The JSON bytes are self-sufficient.
- **Early release of JSON bytes** — `json_bytes` is freed after deserialization,
  before the round-trip allocates its own serialized copy.
- **Mid-round-trip release** — during the round-trip phase, `users` is freed
  after `serialized` is produced but before deserialization runs, so the source
  objects and the deserialized result never coexist.

### Peak memory per phase

| Phase            | Held in memory at once        |
| :--------------- | :---------------------------- |
| Generation       | `users` only                  |
| Serialization    | `users` + `json_bytes`        |
| Deserialization  | `json_bytes` + `users`        |
| Round-trip       | `serialized` + `deserialized` |

> Note: If peak memory still exceeds physical RAM at very high limits, the
> next lever would be chunking generation/serialization into batches instead of
> holding all objects in a single list.

## Requirements

- Python >= 3.14
- Dependencies (managed via `uv`):
  - `msgspec>=0.21.1`
  - `pydantic>=2.13.4`

## FastAPI (Best of Both Worlds)

This project can also use a hybrid API approach:

- **Pydantic** for request/input models and validation.
- **msgspec** for response encoding to JSON for faster output processing.

Typical route pattern:

```python
class UserCreate(BaseModel):
    name: str
    email: str
    age: int

class UserResponse(msgspec.Struct):
    id: str
    name: str
    email: str
    age: int

@app.post("/users", response_model=None)
async def create_user(data: UserCreate):
    user = UserResponse(id="123", name=data.name, email=data.email, age=data.age)
    return Response(content=msgspec.json.encode(user), media_type="application/json")
```

Run FastAPI with `uv` + `uvicorn`:

```sh
uv run uvicorn app:app --reload
```

## Benchmark Usage

Run the full benchmark (both frameworks) and generate a Markdown report:

```sh
uv run run_benchmarks.py --limit 10000 --sample-interval 0.05 --output-report benchmark_results.md
```

Options:

| Flag                | Default                 | Description                                                   |
| :------------------ | :---------------------- | :------------------------------------------------------------ |
| `--limit`           | `10000`                 | Number of `User` objects to generate.                        |
| `--sample-interval` | `0.05`                  | CPU/RSS sampling interval in seconds (e.g. `0.01` = 10ms).   |
| `--output-report`   | `benchmark_results.md` | Path to the generated Markdown report.                        |

Run a single framework benchmark directly (prints JSON to stdout):

```sh
uv run benchmark_runner.py --framework pydantic --limit 10000
uv run benchmark_runner.py --framework msgspec --limit 10000
```

## Output

The orchestrator writes a Markdown report (default `benchmark_results.md`)
containing:

- An overview table of phase timings with the Pydantic/msgspec ratio and winner.
- A memory usage comparison (peak RAM and RAM growth per phase).
- A CPU utilization table (average and peak per phase).
- A strict overall peak summary (max CPU and max RSS across all captured
  telemetry samples, across all phases).
- Key observations about the relative performance characteristics of the two
  frameworks.
