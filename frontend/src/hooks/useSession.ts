import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import api from '../api';

export interface SessionFile {
    fileId: string;
    filename: string;
    language: string;
    content: string;
    persisted: boolean;
}

interface UseSessionParams {
    routeSessionId: string;
    username: string;
    setSessionIdInContext: (id: string | null) => void;
}

interface UseSessionResult {
    loading: boolean;
    error: string | null;
    sessionId: string | null;
    files: SessionFile[];
    activeFileId: string | null;
    activeFile: SessionFile | null;
    activeContent: string;
    selectFile: (fileId: string) => Promise<void>;
    createFile: (filename: string) => Promise<void>;
    updateActiveContent: (content: string) => void;
    saveEditorEvent: (
        fileId: string,
        content: string,
        trigger: 'debounce' | 'file_switch',
    ) => Promise<void>;
}

// ── Problem Q1: Shopping Cart Debugger ────────────────────────────────────
// Starter files pre-loaded for the candidate. discount.py contains the bug.

const Q1_FILES: { filename: string; content: string }[] = [
  {
    filename: 'product.py',
    content: `from dataclasses import dataclass


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
`,
  },
  {
    filename: 'cart.py',
    content: `from __future__ import annotations

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

    def add_item(self, product: Product, quantity: int = 1) -> None:
        """Add \`quantity\` units of \`product\`. Merges if the SKU already exists."""
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

    def get_items(self) -> list[CartItem]:
        return list(self._items)

    def subtotal(self) -> float:
        """Sum of (price × quantity) for all items — no discounts applied."""
        return sum(item.subtotal for item in self._items)

    def total(self) -> float:
        """Final price after DiscountEngine applies all applicable discounts."""
        return self._engine.apply(self._items, self._coupon)

    def __len__(self) -> int:
        return sum(item.quantity for item in self._items)
`,
  },
  {
    filename: 'discount.py',
    content: `from __future__ import annotations

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
`,
  },
  {
    filename: 'tests/test_cart.py',
    content: `"""
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
`,
  },
];

const fallbackSessionId = (): string => `local-${Date.now().toString(36)}`;

const inferLanguage = (filename: string): string => {
    if (filename.endsWith('.py')) return 'python';
    if (filename.endsWith('.ts') || filename.endsWith('.tsx')) return 'typescript';
    if (filename.endsWith('.js') || filename.endsWith('.jsx')) return 'javascript';
    if (filename.endsWith('.json')) return 'json';
    return 'plaintext';
};

const createLocalFile = (filename: string, content: string): SessionFile => ({
    fileId: `local-${filename.toLowerCase().replace(/[^a-z0-9._-]/g, '-')}-${Date.now().toString(36)}`,
    filename,
    language: inferLanguage(filename),
    content,
    persisted: false,
});

export const useSession = ({
    routeSessionId,
    username,
    setSessionIdInContext,
}: UseSessionParams): UseSessionResult => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [files, setFiles] = useState<SessionFile[]>([]);
    const [activeFileId, setActiveFileId] = useState<string | null>(null);
    const filesRef = useRef<SessionFile[]>([]);
    const lastSavedContentRef = useRef<Record<string, string>>({});

    useEffect(() => {
        filesRef.current = files;
    }, [files]);

    useEffect(() => {
        let isCancelled = false;

        const startSession = async (): Promise<void> => {
            setLoading(true);
            setError(null);

            let resolvedSessionId: string;
            try {
                const response = await api.post('/session/start', {
                    username,
                    project_name: routeSessionId,
                });
                resolvedSessionId = response.data?.session_id ?? fallbackSessionId();
            } catch {
                resolvedSessionId = fallbackSessionId();
                if (!isCancelled) {
                    setError('Using local fallback until /session/start is available.');
                }
            }

            if (isCancelled) return;

            const starterFiles = Q1_FILES.map((f) => createLocalFile(f.filename, f.content));
            setSessionId(resolvedSessionId);
            setSessionIdInContext(resolvedSessionId);
            setFiles(starterFiles);
            setActiveFileId(starterFiles[2].fileId); // open discount.py by default
            setLoading(false);
        };

        void startSession();

        return () => {
            isCancelled = true;
        };
    }, [routeSessionId, setSessionIdInContext, username]);

    const activeFile = useMemo(
        () => files.find((file) => file.fileId === activeFileId) ?? null,
        [files, activeFileId],
    );

    const activeContent = activeFile?.content ?? '';

    const persistFileIfNeeded = useCallback(async (targetFileId: string): Promise<string> => {
        const file = filesRef.current.find((entry) => entry.fileId === targetFileId);
        if (!file || file.persisted) return targetFileId;

        try {
            const response = await api.post('/files', {
                filename: file.filename,
                initial_content: file.content,
            });
            const persistedId = response.data?.file_id as string | undefined;
            if (!persistedId) return targetFileId;

            setFiles((current) =>
                current.map((entry) => (
                    entry.fileId === targetFileId
                        ? { ...entry, fileId: persistedId, persisted: true }
                        : entry
                )),
            );
            setActiveFileId((current) => (current === targetFileId ? persistedId : current));
            return persistedId;
        } catch {
            // Work in local mode while endpoint is unavailable.
            return targetFileId;
        }
    }, []);

    const saveEditorEvent = useCallback(async (
        fileId: string,
        content: string,
        trigger: 'debounce' | 'file_switch',
    ): Promise<void> => {
        if (!sessionId) return;

        const lastSaved = lastSavedContentRef.current[fileId];
        if (lastSaved === content) {
            return;
        }

        const resolvedFileId = await persistFileIfNeeded(fileId);
        if (lastSavedContentRef.current[resolvedFileId] === content) {
            return;
        }

        try {
            await api.post('/events/editor', {
                file_id: resolvedFileId,
                content,
                trigger,
                suggestion_id: null,
                cursor_line: 1,
                cursor_col: 1,
            });
            lastSavedContentRef.current = {
                ...lastSavedContentRef.current,
                [fileId]: content,
                [resolvedFileId]: content,
            };
        } catch {
            // Keep local editing available while backend endpoint is unavailable.
        }
    }, [persistFileIfNeeded, sessionId]);

    const selectFile = useCallback(async (fileId: string): Promise<void> => {
        const previousFileId = activeFileId;
        if (previousFileId && previousFileId !== fileId) {
            const previousFile = filesRef.current.find((file) => file.fileId === previousFileId);
            if (previousFile) {
                await saveEditorEvent(previousFile.fileId, previousFile.content, 'file_switch');
            }
        }

        const resolvedFileId = await persistFileIfNeeded(fileId);
        setActiveFileId(resolvedFileId);
    }, [activeFileId, persistFileIfNeeded, saveEditorEvent]);

    const createFile = useCallback(async (filename: string): Promise<void> => {
        if (files.some((file) => file.filename === filename)) {
            return;
        }
        const file = createLocalFile(filename, '');
        setFiles((current) => [...current, file]);
        setActiveFileId(file.fileId);
        const resolvedFileId = await persistFileIfNeeded(file.fileId);
        setActiveFileId(resolvedFileId);
    }, [files, persistFileIfNeeded]);

    const updateActiveContent = useCallback((content: string): void => {
        setFiles((current) =>
            current.map((file) => (file.fileId === activeFileId ? { ...file, content } : file)),
        );
    }, [activeFileId]);

    return {
        loading,
        error,
        sessionId,
        files,
        activeFileId,
        activeFile,
        activeContent,
        selectFile,
        createFile,
        updateActiveContent,
        saveEditorEvent,
    };
};
