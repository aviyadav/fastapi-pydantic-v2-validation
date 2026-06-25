# FastAPI + Pydantic v2 Validation Demo

A minimal FastAPI project that demonstrates **request validation with Pydantic v2**, including:

- strict typed payload validation
- field-level constraints (lengths, regex, numeric bounds)
- forbidden extra fields
- simple domain/business rule validation (checkout total consistency)

## Tech Stack

- Python `>=3.13`
- FastAPI
- Uvicorn
- Pydantic v2 (via FastAPI)

## Project Structure

- `app.py` – API app, Pydantic models, endpoint, and validation error handling
- `pyproject.toml` – project metadata and dependencies

## API Overview

### `POST /checkout`

Accepts a checkout payload with:

- `items`: non-empty list of strict items (`sku`, `qty`, `price_cents`)
- `address`: shipping address with US-specific validation rules
- `payment_token`: minimum length 10
- `total_cents`: must match computed sum of items (`qty * price_cents`)

Returns:

- `200 OK` with `{ "ok": true }` when valid
- `422 Unprocessable Entity` when validation fails

## Validation Rules Implemented

### Address

- `line1`: min length 3
- `city`: min length 2
- `state`: exactly two uppercase letters (e.g. `CA`)
- `zip`: `12345` or `12345-6789`
- `country`: must be `US`
- extra fields are rejected
- whitespace is stripped from string fields

### Item (strict)

- strict typing enabled (`strict=True`)
- `sku`: string
- `qty`: integer
- `price_cents`: integer
- extra fields are rejected

### Checkout Domain Rule

The API verifies that:

`sum(item.qty * item.price_cents) == total_cents`

If mismatched, the endpoint returns `422` with a clear error message.

## Installation

Using `uv`:

```bash
uv sync
```

Or add dependencies manually:

```bash
uv add fastapi uvicorn
```

## Run

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8090 --reload
```

Then open:

- API root: `http://localhost:8090`
- Swagger UI: `http://localhost:8090/docs`
- ReDoc: `http://localhost:8090/redoc`

## Example Request

```bash
curl -X POST "http://localhost:8090/checkout" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"sku": "ABC-123", "qty": 2, "price_cents": 1500},
      {"sku": "XYZ-999", "qty": 1, "price_cents": 500}
    ],
    "address": {
      "line1": "123 Market St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94105",
      "country": "US"
    },
    "payment_token": "tok_test_12345",
    "total_cents": 3500
  }'
```

## Example Validation Error

If `total_cents` does not match item totals, response is:

```json
{
  "detail": "Total cents do not match sum of item totals."
}
```
