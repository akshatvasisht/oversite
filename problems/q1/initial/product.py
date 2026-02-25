from dataclasses import dataclass


@dataclass
class Product:
    """Represents a single purchasable item in the store."""

    sku: str
    name: str
    price: float
    category: str = "general"

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValueError(f"Price cannot be negative: {self.price}")

    def __repr__(self) -> str:
        return f"Product(sku={self.sku!r}, name={self.name!r}, price={self.price:.2f})"
