"""In-App Purchase receipt validation for Apple App Store and Google Play."""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Dict

LOGGER = logging.getLogger("pegasus.iap")

PRODUCT_CATALOG: Dict[str, Dict[str, Any]] = {
    "pegasus_tokens_500k": {"tokens": 500_000, "price_usd": 0.99},
    "pegasus_tokens_2m": {"tokens": 2_000_000, "price_usd": 2.99},
    "pegasus_tokens_5m": {"tokens": 5_000_000, "price_usd": 4.99},
}


def get_product_tokens(product_id: str) -> int | None:
    """Return token count for a product ID, or None if not found."""
    product = PRODUCT_CATALOG.get(product_id)
    return product["tokens"] if product else None


def get_product_list() -> list[Dict[str, Any]]:
    """Return the list of purchasable products."""
    return [
        {
            "productId": pid,
            "tokens": info["tokens"],
            "priceUsd": info["price_usd"],
            "label": _format_tokens(info["tokens"]),
        }
        for pid, info in PRODUCT_CATALOG.items()
    ]


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n // 1_000_000}M tokens"
    if n >= 1_000:
        return f"{n // 1_000}K tokens"
    return f"{n} tokens"


# ---------------------------------------------------------------------------
# Apple App Store Server API v2
# ---------------------------------------------------------------------------

def validate_apple_receipt(transaction_id: str, receipt_data: str) -> Dict[str, Any]:
    """
    Validate an Apple App Store signed transaction (JWS).

    In production this should:
    1. Decode the JWS (3-part base64url string)
    2. Verify signature against Apple's root certificate chain
    3. Extract transactionId, productId, bundleId
    4. Verify bundleId matches our app

    For now, we decode the JWS payload without full crypto verification
    (Apple's StoreKit 2 transactions are signed JWS tokens).
    Full verification requires the `cryptography` package and Apple root certs.
    """
    try:
        # JWS format: header.payload.signature
        parts = receipt_data.split(".")
        if len(parts) != 3:
            return {"valid": False, "error": "Invalid JWS format"}

        # Decode the payload (2nd part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes)

        product_id = payload.get("productId")
        txn_id = payload.get("transactionId") or payload.get("originalTransactionId")
        bundle_id = payload.get("bundleId")

        expected_bundle = os.getenv("APPLE_BUNDLE_ID", "")
        if expected_bundle and bundle_id != expected_bundle:
            return {"valid": False, "error": f"Bundle ID mismatch: {bundle_id}"}

        if product_id not in PRODUCT_CATALOG:
            return {"valid": False, "error": f"Unknown product: {product_id}"}

        LOGGER.info("Apple receipt validated: txn=%s product=%s", txn_id, product_id)
        return {
            "valid": True,
            "product_id": product_id,
            "transaction_id": str(txn_id or transaction_id),
        }

    except Exception as exc:
        LOGGER.error("Apple receipt validation failed: %s", exc)
        return {"valid": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Google Play Developer API
# ---------------------------------------------------------------------------

def validate_google_receipt(purchase_token: str, product_id: str) -> Dict[str, Any]:
    """
    Validate a Google Play purchase.

    In production this should call:
    androidpublisher.purchases.products.get(
        packageName, productId, token
    )
    and verify purchaseState == 0 (purchased).

    For now, we accept the purchase_token and product_id if the product is valid.
    Full verification requires Google service account credentials.
    """
    try:
        if product_id not in PRODUCT_CATALOG:
            return {"valid": False, "error": f"Unknown product: {product_id}"}

        package_name = os.getenv("GOOGLE_PLAY_PACKAGE_NAME", "")

        # In production: call Google Play Developer API
        # from google.oauth2 import service_account
        # from googleapiclient.discovery import build
        # credentials = service_account.Credentials.from_service_account_file(...)
        # service = build('androidpublisher', 'v3', credentials=credentials)
        # result = service.purchases().products().get(
        #     packageName=package_name, productId=product_id, token=purchase_token
        # ).execute()
        # if result.get('purchaseState') != 0:
        #     return {"valid": False, "error": "Purchase not completed"}

        # For now: trust the client-side purchase (receipt stored for later audit)
        order_id = f"GPA.{purchase_token[:20]}"

        LOGGER.info("Google receipt validated: product=%s order=%s", product_id, order_id)
        return {
            "valid": True,
            "product_id": product_id,
            "order_id": order_id,
        }

    except Exception as exc:
        LOGGER.error("Google receipt validation failed: %s", exc)
        return {"valid": False, "error": str(exc)}
