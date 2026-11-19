from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from pydantic import BaseModel, Field

from packages.schema import MaterialLine

Cents = Annotated[int, Field(ge=0, le=100_000_000_000)]
Hours = Annotated[Decimal, Field(ge=0, le=100_000, max_digits=8, decimal_places=2)]


class QuoteMaterial(BaseModel):
    description: str
    unit: str
    etim_code: str | None = None
    quantity: int = Field(ge=0)
    unit_price: Cents | None = None

    @property
    def key(self) -> tuple[str, str, str | None]:
        return self.description, self.unit, self.etim_code


class QuoteInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    customer: str = Field(max_length=255)
    materials: list[QuoteMaterial]
    labour_hours: Hours = Decimal(0)
    hourly_rate: Cents = 0
    fixed_fee: Cents = 0


class Quote(QuoteInput):
    id: str
    project_id: str
    project_name: str
    created_at: datetime


class QuoteLine(BaseModel):
    description: str
    unit: str
    quantity: Decimal
    price: int
    amount: int


class QuoteChange(BaseModel):
    description: str
    unit: str
    before_quantity: Decimal
    after_quantity: Decimal
    before_price: int
    after_price: int
    delta: int


def rounded_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def quote_materials(items: list[MaterialLine]) -> list[QuoteMaterial]:
    grouped: dict[tuple[str, str, str | None], QuoteMaterial] = {}
    for item in items:
        price = item.unit_price
        material = QuoteMaterial(
            description=item.description, unit=item.unit, etim_code=item.etim_code,
            quantity=item.quantity,
            unit_price=None if price is None else rounded_cents(Decimal(str(price)) * 100),
        )
        previous = grouped.get(material.key)
        if previous is None:
            grouped[material.key] = material
        else:
            previous.quantity += material.quantity
            if previous.unit_price != material.unit_price:
                previous.unit_price = None
    return list(grouped.values())


def quote_lines(quote: QuoteInput) -> dict[tuple, QuoteLine]:
    lines = {}
    for item in quote.materials:
        price = item.unit_price or 0
        lines[("material", *item.key)] = QuoteLine(
            description=item.description, unit=item.unit, quantity=Decimal(item.quantity),
            price=price, amount=price * item.quantity,
        )
    if quote.labour_hours:
        lines[("labour",)] = QuoteLine(
            description="Arbeid", unit="uur", quantity=quote.labour_hours,
            price=quote.hourly_rate, amount=rounded_cents(quote.labour_hours * quote.hourly_rate),
        )
    if quote.fixed_fee:
        lines[("fee",)] = QuoteLine(
            description="Vaste kosten", unit="st", quantity=Decimal(1),
            price=quote.fixed_fee, amount=quote.fixed_fee,
        )
    return lines


def compare_quotes(before: QuoteInput, after: QuoteInput) -> list[QuoteChange]:
    old = quote_lines(before)
    new = quote_lines(after)
    changes = []
    for key in dict.fromkeys([*old, *new]):
        left, right = old.get(key), new.get(key)
        if left == right:
            continue
        line = right or left
        changes.append(QuoteChange(
            description=line.description, unit=line.unit,
            before_quantity=left.quantity if left else Decimal(0),
            after_quantity=right.quantity if right else Decimal(0),
            before_price=left.price if left else 0, after_price=right.price if right else 0,
            delta=(right.amount if right else 0) - (left.amount if left else 0),
        ))
    return changes
