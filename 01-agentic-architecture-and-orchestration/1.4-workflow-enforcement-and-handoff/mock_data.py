"""Made-up Nimbus Robotics support backend. Nothing to do here.

These are the raw backend functions. They do NO checks on their own: the
workflow rules (verify first, refund limit) are yours to enforce in starter.py.
"""

CUSTOMERS = {
    "priya.n@example.com": {"customer_id": "C-2201", "name": "Priya Nair", "tier": "standard"},
    "tom.b@example.com": {"customer_id": "C-3307", "name": "Tom Berger", "tier": "plus"},
}

ORDERS = {
    "NR-1042": {"customer_id": "C-2201", "item": "Nimbus Vac S2 robot vacuum", "amount": 349.00,
                "status": "delivered", "delivered": "2026-10-08",
                "note": "Customer reports it arrived with a cracked chassis."},
    "NR-1077": {"customer_id": "C-2201", "item": "Stratus Home robotic arm", "amount": 1299.00,
                "status": "delivered", "delivered": "2026-09-29",
                "charges": [{"date": "2026-09-25", "amount": 1299.00},
                            {"date": "2026-09-25", "amount": 1299.00}],
                "note": "Payment processor shows two identical charges 14 seconds apart."},
    "NR-1090": {"customer_id": "C-2201", "item": "Spare brush kit", "amount": 39.00,
                "status": "shipped", "carrier": "DHL", "tracking": "JD014677812",
                "eta": "2026-10-16"},
    "NR-0999": {"customer_id": "C-3307", "item": "Nimbus Vac S2 robot vacuum", "amount": 349.00,
                "status": "delivered", "delivered": "2026-10-01"},
}

REFUNDS: list[dict] = []        # what process_refund actually did
ESCALATIONS: list[dict] = []    # what escalate_to_human actually received


def reset() -> None:
    REFUNDS.clear()
    ESCALATIONS.clear()


def get_customer(email: str) -> dict:
    c = CUSTOMERS.get(email.strip().lower())
    if not c:
        raise LookupError(f"No customer with email {email!r}")
    return dict(c)


def lookup_order(order_id: str) -> dict:
    o = ORDERS.get(order_id.strip().upper())
    if not o:
        raise LookupError(f"No order {order_id!r}")
    return {"order_id": order_id.upper(), **o}


def process_refund(order_id: str, amount: float, reason: str) -> dict:
    REFUNDS.append({"order_id": order_id.upper(), "amount": amount, "reason": reason})
    return {"refund_id": f"RF-{len(REFUNDS):04d}", "order_id": order_id.upper(),
            "amount": amount, "status": "issued"}


def escalate_to_human(**handoff) -> dict:
    ESCALATIONS.append(handoff)
    return {"ticket_id": f"ESC-{len(ESCALATIONS):04d}", "status": "queued for a human agent"}
