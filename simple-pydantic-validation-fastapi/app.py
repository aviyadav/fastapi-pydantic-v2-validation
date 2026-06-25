from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel, Field, ConfigDict, ValidationError


app = FastAPI(title="Checkout API")

class Address(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    line1: str = Field(min_length=3)
    line2: str | None = None
    city: str = Field(min_length=2)
    state: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    zip: str = Field(pattern=r"^\d{5}(-\d{4})?$")
    country: str = Field(pattern=r"^US$")

class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku: str = Field(min_length=1)
    qty: int = Field(ge=1, le=50)
    price_cents: int = Field(ge=0) 

class StrictItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    sku: str
    qty: int
    price_cents: int
    

class Checkout(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # items: list[Item] = Field(min_length=1)
    items: list[StrictItem] = Field(min_length=1)
    address: Address
    payment_token: str = Field(min_length=10)
    total_cents: int = Field(ge=0)

    # Domain invariant: computed totals must match declared totals
    def validate_totals(self) -> None:
        computed = sum(i.qty * i.price_cents for i in self.items)
        if computed != self.total_cents:
            raise ValueError("Total cents do not match sum of item totals.")
        
@app.post("/checkout")
def checkout(payload: Checkout):
    try:
        payload.validate_totals()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    # Process the checkout (e.g., charge payment, create order, etc.)
    return {"ok": True}

@app.exception_handler(ValidationError)
async def pydantic_error_handler(_: Request, exec: ValidationError):
    # Flatten to a stable envelope (no stack traces in prod)
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR",
                 "errors": exec.errors()},
    )


# @app.post("/bulk/items")
# async def bulk_items(request: Request):
#     async for chunk in request.stream():
#         # stream-chunk → decode → pydantic-validate per-record
#         # keep buffers small; avoid materializing entire body
#         ...
#     return {"ok": True}