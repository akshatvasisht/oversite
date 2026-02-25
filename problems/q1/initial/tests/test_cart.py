"""
Shopping Cart -- test suite
Run with:  pytest tests/test_cart.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from product import Product
from cart import ShoppingCart


@pytest.fixture
def shirt():
    return Product(sku="SHIRT-001", name="Cotton T-Shirt", price=25.00, category="apparel")

@pytest.fixture
def apple():
    return Product(sku="APPLE-001", name="Organic Apple", price=1.50, category="produce")

@pytest.fixture
def laptop():
    return Product(sku="LAPTOP-001", name="Dev Laptop", price=999.99, category="electronics")


class TestCartOperations:
    def test_empty_cart_has_zero_total(self):
        assert ShoppingCart().total() == 0.0

    def test_add_single_item(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 1)
        assert len(cart) == 1

    def test_adding_same_sku_twice_merges(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.add_item(shirt, 3)
        assert len(cart) == 5
        assert len(cart.get_items()) == 1

    def test_remove_item(self, shirt, apple):
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.add_item(apple, 5)
        cart.remove_item("SHIRT-001")
        skus = [i.product.sku for i in cart.get_items()]
        assert "SHIRT-001" not in skus

    def test_subtotal_no_discounts(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 3)
        assert cart.subtotal() == pytest.approx(75.00)

    def test_zero_quantity_raises(self, shirt):
        with pytest.raises(ValueError):
            ShoppingCart().add_item(shirt, 0)


class TestQuantityDiscounts:
    def test_no_discount_below_threshold(self, shirt):
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        assert cart.total() == pytest.approx(50.00)

    def test_tier_3_discount(self, shirt):
        # 3 x $25 = $75.00 - (3 x $0.75) = $72.75
        cart = ShoppingCart()
        cart.add_item(shirt, 3)
        assert cart.total() == pytest.approx(72.75)

    def test_tier_5_discount(self, shirt):
        # 5 x $25 = $125.00 - (5 x $1.50) = $117.50
        cart = ShoppingCart()
        cart.add_item(shirt, 5)
        assert cart.total() == pytest.approx(117.50)

    def test_tier_10_discount(self, shirt):
        # 10 x $25 = $250.00 - (10 x $3.00) = $220.00
        cart = ShoppingCart()
        cart.add_item(shirt, 10)
        assert cart.total() == pytest.approx(220.00)


class TestCouponDiscounts:
    def test_save20_coupon(self, shirt):
        # 2 x $25 = $50.00, 20% off -> $40.00
        cart = ShoppingCart()
        cart.add_item(shirt, 2)
        cart.apply_coupon("SAVE20")
        assert cart.total() == pytest.approx(40.00)

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


class TestCombinedDiscounts:
    def test_quantity_then_percentage_basic(self, shirt):
        """
        5 shirts x $25 = $125.00
        Coupon SAVE20 (20% off) + tier-5 quantity ($1.50/unit x 5 = $7.50 off)

        CORRECT (quantity first):  $125 - $7.50 = $117.50  ->  x0.80 = $94.00
        WRONG   (percent first):   $125 x 0.80  = $100.00  ->  - $7.50 = $92.50
        """
        cart = ShoppingCart()
        cart.add_item(shirt, 5)
        cart.apply_coupon("SAVE20")
        assert cart.total() == pytest.approx(94.00)

    def test_quantity_then_percentage_tier10(self, shirt):
        """
        10 shirts x $25 = $250.00
        Coupon SAVE10 (10% off) + tier-10 ($3.00/unit x 10 = $30.00 off)

        CORRECT: $250 - $30 = $220  ->  x0.90 = $198.00
        WRONG:   $250 x 0.90 = $225 ->  - $30  = $195.00
        """
        cart = ShoppingCart()
        cart.add_item(shirt, 10)
        cart.apply_coupon("SAVE10")
        assert cart.total() == pytest.approx(198.00)

    def test_mixed_products_with_coupon(self, shirt, apple):
        """
        4 shirts ($100) + 3 apples ($4.50) = $104.50, 7 units -> tier-5
        Coupon SAVE20

        CORRECT: $104.50 - $10.50 = $94.00  ->  x0.80 = $75.20
        WRONG:   $104.50 x 0.80  = $83.60  ->  - $10.50 = $73.10
        """
        cart = ShoppingCart()
        cart.add_item(shirt, 4)
        cart.add_item(apple, 3)
        cart.apply_coupon("SAVE20")
        assert cart.total() == pytest.approx(75.20)
