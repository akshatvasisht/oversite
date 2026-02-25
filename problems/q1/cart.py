from __future__ import annotations

from product import Product
from discount import DiscountEngine


class CartItem:
    """A product + quantity pair inside a cart."""

    def __init__(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        self.product = product
        self.quantity = quantity

    @property
    def subtotal(self) -> float:
        return self.product.price * self.quantity

    def __repr__(self) -> str:
        return f"CartItem({self.product.sku!r}, qty={self.quantity})"


class ShoppingCart:
    """
    A shopping cart that holds CartItems and delegates final pricing
    to DiscountEngine.

    Public interface
    ----------------
    add_item(product, quantity)  – add or merge an item
    remove_item(sku)             – remove all of a given SKU
    apply_coupon(code)           – attach a coupon code
    subtotal() -> float          – sum of raw item prices (no discounts)
    total()    -> float          – final price after all discounts
    """

    def __init__(self) -> None:
        self._items: list[CartItem] = []
        self._coupon: str | None = None
        self._engine = DiscountEngine()

    # ── Mutations ────────────────────────────────────────────────────────────

    def add_item(self, product: Product, quantity: int = 1) -> None:
        """Add `quantity` units of `product`. Merges if the SKU already exists."""
        for item in self._items:
            if item.product.sku == product.sku:
                item.quantity += quantity
                return
        self._items.append(CartItem(product, quantity))

    def remove_item(self, sku: str) -> None:
        """Remove all units of the item with the given SKU."""
        self._items = [i for i in self._items if i.product.sku != sku]

    def apply_coupon(self, code: str) -> None:
        """Attach a coupon code. Only one coupon is active at a time."""
        self._coupon = code

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_items(self) -> list[CartItem]:
        return list(self._items)

    def subtotal(self) -> float:
        """Sum of (price × quantity) for all items — no discounts applied."""
        return sum(item.subtotal for item in self._items)

    def total(self) -> float:
        """Final price after DiscountEngine applies all applicable discounts."""
        return self._engine.apply(self._items, self._coupon)

    def __len__(self) -> int:
        """Total number of units across all items."""
        return sum(item.quantity for item in self._items)

    def __repr__(self) -> str:
        return f"ShoppingCart(items={len(self._items)}, units={len(self)}, coupon={self._coupon!r})"
