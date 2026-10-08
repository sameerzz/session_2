"""Simple tools bound to one user's token; no shared login variable."""
from typing import Optional
from uuid import uuid4
from urllib.parse import quote

import httpx
from langchain_core.tools import tool

API_URL = "https://hopscotch-shop.vercel.app"


def sign_in(email):
    response = httpx.post(f"{API_URL}/auth/login", json={"email": email}, timeout=30)
    response.raise_for_status()
    return response.json()


def make_tools(token):
    # This header belongs only to these tools, not every Streamlit user.
    # The token is not a tool argument, so the model cannot change the user.
    headers = {"Authorization": f"Bearer {token}"}

    @tool
    def get_cart() -> dict:
        """Inspect the signed-in customer's current cart.

        Use for questions about cart contents, quantities, and totals.
        Takes no arguments. Returns the current cart items and totals.
        Money values are integer paise: 100 paise equals INR 1.
        This tool only reads the cart; it cannot edit it or place an order.
        """
        response = httpx.get(f"{API_URL}/cart", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    @tool
    def get_orders(order_id: Optional[str] = None) -> dict:
        """List the signed-in customer's orders or inspect a specific order.

        Use for order questions and before cancelling an order item.
        Omit order_id to list orders; provide a real order_id to inspect one.
        Results contain order IDs, item IDs, original quantities, cancelled
        quantities, active quantities, statuses, and totals.
        Use these results to identify the real order_id and item_id and check
        the active quantity before requesting cancellation. Never guess IDs.
        Money values are integer paise: 100 paise equals INR 1.
        This tool only reads orders; it does not change them.

        Args:
            order_id: Optional real order identifier returned by this tool.
        """
        path = "/orders" if order_id is None else f"/orders/{quote(order_id, safe='')}"
        response = httpx.get(f"{API_URL}{path}", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    @tool
    def cancel_item(order_id: str, item_id: str, quantity: int) -> dict:
        """Cancel a selected whole-number quantity of an existing order item.

        Use only when the user explicitly requests cancellation and clearly
        identifies the order, item, and quantity.
        First call get_orders and read its tool result to discover the real
        order_id, item_id, and current active quantity. Do that prerequisite
        read before requesting this tool; never guess identifiers.
        Quantity must be an integer from 1 to 99 and must not exceed the item's
        active quantity. If the order, item, or quantity is ambiguous, explain
        what information is missing and do not cancel.
        Returns the updated order and operation details. Claim success only
        after receiving a successful API result. Money is in integer paise:
        100 paise equals INR 1.
        Each invocation creates a new cancellation request. Do not repeat it
        blindly after an error; inspect the order before taking further action.
        This tool cannot cancel an entire order, place orders, edit carts,
        process refunds, or search the web.

        Args:
            order_id: Real order identifier obtained from get_orders.
            item_id: Real item identifier within that order from get_orders.
            quantity: Number of active units the user explicitly wants cancelled.
        """
        response = httpx.post(
            f"{API_URL}/orders/{quote(order_id, safe='')}/items/{quote(item_id, safe='')}/cancel",
            headers=headers,
            json={"quantity": quantity, "operation_id": str(uuid4())},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    return [get_cart, get_orders, cancel_item]
