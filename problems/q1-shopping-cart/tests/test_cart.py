"""
Shopping Cart — test suite
==========================
Run with:  pytest tests/test_cart.py -v

The tests in TestCombinedDiscounts will FAIL until the discount ordering
bug in discount.py is fixed.  All other tests should pass immediately.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from product import Product
from cart import ShoppingCart


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def shirt() -> Product:
    return Product(sku="SHIRT-001", name="Cotton T-Shirt", price=25.00, category="apparel")


@pytest.fixture
def apple() -> Product:
    return Product(sku="APPLE-001", name="Organic Apple", price=1.50, category="produce")


@pytest.fixture
def laptop() -> Product:
    return Product(sku="LAPTOP-001", name="Dev Laptop", price=999.99, category="electronics")


# ---------------------------------------------------------------------------
# Cart operations
# ---------------------------------------------------------------------------

class TestCartOperations:
    def test_empty_cart_has_zero_total(self):
        assert ShoppingCart().total() == 0.0

    def test_add_single_item(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 1)
        assert len(cart) == 1

    def test_add_multiple_quantities(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 4)
        assert len(cart) == 4

    def test_adding_same_sku_twice_merges(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.add_item(shirt, 3)
        assert len(cart) == 5
        assert len(cart.get_items()) == 1  # still one line item

    def test_remove_item(self, shirt, apple):
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.add_item(apple, 5)
        cart.remove_item("SHIRT-001")
        skus = [i.product.sku for i in cart.get_items()]
        assert "SHIRT-001" not in skus
        assert "APPLE-001" in skus

    def test_remove_nonexistent_sku_is_noop(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 1)
        cart.remove_item("DOES-NOT-EXIST")  # should not raise
        assert len(cart) == 1

    def test_subtotal_no_discounts(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 3)
        assert cart.subtotal() == pytest.approx(75.00)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError):
            Product(sku="BAD", name="Bad", price=-1.00)

    def test_zero_quantity_raises(self, shirt):
        cart = ShoppingCart()
        with pytest.raises(ValueError):
            cart.add_item(shirt, 0)


# ---------------------------------------------------------------------------
# Quantity discounts only (no coupon)
# ---------------------------------------------------------------------------

class TestQuantityDiscounts:
    def test_no_discount_below_threshold(self, shirt):
        # 2 items — below the minimum tier of 3
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        assert cart.total() == pytest.approx(50.00)

    def test_tier_3_discount(self, shirt):
        # 3 × $25 = $75.00 − (3 × $0.75) = $72.75
        cart = ShoppingCart()
        cart.add_item(shirt, 3)
        assert cart.total() == pytest.approx(72.75)

    def test_tier_5_discount(self, shirt):
        # 5 × $25 = $125.00 − (5 × $1.50) = $117.50
        cart = ShoppingCart()
        cart.add_item(shirt, 5)
        assert cart.total() == pytest.approx(117.50)

    def test_tier_10_discount(self, shirt):
        # 10 × $25 = $250.00 − (10 × $3.00) = $220.00
        cart = ShoppingCart()
        cart.add_item(shirt, 10)
        assert cart.total() == pytest.approx(220.00)

    def test_quantity_spans_multiple_skus(self, shirt, apple):
        # 4 shirts + 2 apples = 6 units → tier 5 ($1.50/unit)
        # subtotal: 4×$25 + 2×$1.50 = $103.00
        # discount: 6 × $1.50 = $9.00 → total $94.00
        cart = ShoppingCart()
        cart.add_item(shirt, 4)
        cart.add_item(apple, 2)
        assert cart.total() == pytest.approx(94.00)


# ---------------------------------------------------------------------------
# Coupon discounts only (quantity below threshold)
# ---------------------------------------------------------------------------

class TestCouponDiscounts:
    def test_save10_coupon(self, shirt):
        # 2 × $25 = $50.00, 10% off → $45.00
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.apply_coupon("SAVE10")
        assert cart.total() == pytest.approx(45.00)

    def test_save20_coupon(self, shirt):
        # 2 × $25 = $50.00, 20% off → $40.00
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.apply_coupon("SAVE20")
        assert cart.total() == pytest.approx(40.00)

    def test_halfoff_coupon(self, laptop):
        # 1 × $999.99, 50% off → $499.995 → $500.00
        cart = ShoppingCart()
        cart.add_item(laptop, 1)
        cart.apply_coupon("HALFOFF")
        assert cart.total() == pytest.approx(500.00, abs=0.01)

    def test_coupon_is_case_insensitive(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.apply_coupon("save20")
        assert cart.total() == pytest.approx(40.00)

    def test_invalid_coupon_is_ignored(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.apply_coupon("NOTACODE")
        assert cart.total() == pytest.approx(50.00)

    def test_no_coupon_no_quantity_returns_subtotal(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 1)
        assert cart.total() == pytest.approx(25.00)


# ---------------------------------------------------------------------------
# Combined discounts — these tests EXPOSE THE BUG
#
# Correct order: quantity discount first, then percentage off the result.
# The current code does it backwards (percentage first, then quantity),
# producing a lower total than correct.
# ---------------------------------------------------------------------------

class TestCombinedDiscounts:
    def test_quantity_then_percentage_basic(self, shirt):
        """
        5 shirts × $25 = $125.00 subtotal
        Coupon: SAVE20 (20% off)
        Quantity tier 5+: $1.50/unit × 5 = $7.50 off

        CORRECT  (quantity first):  $125.00 − $7.50 = $117.50 → ×0.80 = $94.00
        WRONG    (percent first):   $125.00 × 0.80  = $100.00 → − $7.50 = $92.50
        """
        cart = ShoppingCart()
        cart.add_item(shirt, 5)
        cart.apply_coupon("SAVE20")
        assert cart.total() == pytest.approx(94.00)

    def test_quantity_then_percentage_tier10(self, shirt):
        """
        10 shirts × $25 = $250.00 subtotal
        Coupon: SAVE10 (10% off)
        Quantity tier 10+: $3.00/unit × 10 = $30.00 off

        CORRECT:  $250.00 − $30.00 = $220.00 → ×0.90 = $198.00
        WRONG:    $250.00 × 0.90  = $225.00 → − $30.00 = $195.00
        """
        cart = ShoppingCart()
        cart.add_item(shirt, 10)
        cart.apply_coupon("SAVE10")
        assert cart.total() == pytest.approx(198.00)

    def test_mixed_products_quantity_then_percentage(self, shirt, apple):
        """
        4 shirts ($100) + 3 apples ($4.50) = $104.50 subtotal
        Total units: 7 → tier 5+: $1.50/unit × 7 = $10.50 off
        Coupon: SAVE20 (20% off)

        CORRECT:  $104.50 − $10.50 = $94.00 → ×0.80 = $75.20
        WRONG:    $104.50 × 0.80  = $83.60 → − $10.50 = $73.10
        """
        cart = ShoppingCart()
        cart.add_item(shirt, 4)
        cart.add_item(apple, 3)
        cart.apply_coupon("SAVE20")
        assert cart.total() == pytest.approx(75.20)

    def test_halfoff_with_quantity_tier(self, shirt):
        """
        3 shirts × $25 = $75.00 subtotal
        Quantity tier 3+: $0.75/unit × 3 = $2.25 off
        Coupon: HALFOFF (50% off)

        CORRECT:  $75.00 − $2.25 = $72.75 → ×0.50 = $36.375 → $36.38
        WRONG:    $75.00 × 0.50 = $37.50 → − $2.25 = $35.25
        """
        cart = ShoppingCart()
        cart.add_item(shirt, 3)
        cart.apply_coupon("HALFOFF")
        assert cart.total() == pytest.approx(36.38, abs=0.01)
