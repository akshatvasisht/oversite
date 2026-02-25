## Objective
Your team's e-commerce checkout is generating **incorrect totals** when customers use a discount coupon on a large order. QA has confirmed the bug only appears when *both* a coupon code and a quantity-based discount are active at the same time.

## The Bug
The `DiscountEngine.apply()` method in `discount.py` applies discounts in the wrong order, causing customers to be **undercharged**.

## Example
**# 5 shirts @ $25 + coupon SAVE20**
- subtotal = $125.00
- **Wrong** → $125 × 0.80 = $100 − $7.50 = **$92.50**
- **Correct** → $125 − $7.50 = $117.50 × 0.80 = **$94.00**

## Your Task
1.  **Trace the logic**: Examine `cart.py`, `product.py`, and `discount.py` to understand how the total is calculated.
2.  **Fix the bug**: Correct the order of operations in `discount.py` to ensure fixed discounts are applied before percentage coupons.
3.  **Verify**: Run the provided test suite to ensure all cases pass.
