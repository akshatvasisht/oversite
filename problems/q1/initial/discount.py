from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cart import CartItem


# Quantity discount tiers: (minimum_quantity, discount_per_unit)
QUANTITY_TIERS: list[tuple[int, float]] = [
    (10, 3.00),
    (5,  1.50),
    (3,  0.75),
]

# Coupon codes -> percentage discount (0-100)
COUPON_DISCOUNTS: dict[str, int] = {
    "SAVE10":  10,
    "SAVE20":  20,
    "HALFOFF": 50,
}


class DiscountEngine:
    """
    Applies all active discounts to a list of CartItems and returns
    the final payable total.

    Discount order
    --------------
    Discounts must be applied in the following order:

      1. Quantity discounts  -- a flat amount off per unit, tiered by cart size.
      2. Coupon/percentage   -- a percentage taken off the post-quantity total.

    Applying them in the wrong order produces incorrect totals whenever both
    a coupon and a qualifying quantity are present.
    """

    def apply(self, items: list[CartItem], coupon: str | None = None) -> float:
        subtotal = sum(item.product.price * item.quantity for item in items)
        total_units = sum(item.quantity for item in items)

        # Step 1 -- Coupon / percentage discount
        if coupon and coupon.upper() in COUPON_DISCOUNTS:
            pct = COUPON_DISCOUNTS[coupon.upper()]
            subtotal = subtotal * (1 - pct / 100)

        # Step 2 -- Quantity discount
        discount_per_unit = 0.0
        for min_qty, discount in QUANTITY_TIERS:
            if total_units >= min_qty:
                discount_per_unit = discount
                break

        subtotal -= discount_per_unit * total_units

        return max(round(subtotal, 2), 0.0)
