"""
Supported PII entity types.

Every detector in the pipeline uses these type strings so that the
merger and conflict resolver can compare detections from different
sources without mismatched vocabulary.

Extending
---------
Add a new member to ``EntityType``.  That's it.  The merger,
confidence engine, and summary generator all operate on the string
value and will pick up the new type automatically.

For custom / domain‑specific types, you can use ``EntityType.CUSTOM``
and store the specific label in ``Detection.reason``.
"""

from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    """
    Every PII category that the system can detect.

    Using ``str, Enum`` as the base means each member **is** a string
    (e.g. ``EntityType.EMAIL == "EMAIL"``) so it serialises naturally
    to JSON without a custom encoder.
    """

    # ── Personal identification ──
    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    AGE = "AGE"
    GENDER = "GENDER"

    # ── Organisational ──
    ORGANIZATION = "ORGANIZATION"

    # ── Government / National IDs (India‑focused) ──
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    PASSPORT = "PASSPORT"
    VOTER_ID = "VOTER_ID"
    DRIVING_LICENSE = "DRIVING_LICENSE"

    # ── Financial ──
    BANK_ACCOUNT = "BANK_ACCOUNT"
    CREDIT_CARD = "CREDIT_CARD"
    IFSC = "IFSC"
    UPI_ID = "UPI_ID"
    CIN = "CIN"  # Corporate Identification Number
    GST = "GST"

    # ── Digital / Network ──
    URL = "URL"
    IP_ADDRESS = "IP_ADDRESS"
    MAC_ADDRESS = "MAC_ADDRESS"

    # ── Other ──
    CUSTOM = "CUSTOM"

    # ── Metadata helpers ──

    @classmethod
    def government_ids(cls) -> set[str]:
        """Return all government‑ID type strings."""
        return {
            cls.AADHAAR.value,
            cls.PAN.value,
            cls.PASSPORT.value,
            cls.VOTER_ID.value,
            cls.DRIVING_LICENSE.value,
        }

    @classmethod
    def financial(cls) -> set[str]:
        """Return all financial type strings."""
        return {
            cls.BANK_ACCOUNT.value,
            cls.CREDIT_CARD.value,
            cls.IFSC.value,
            cls.UPI_ID.value,
            cls.CIN.value,
            cls.GST.value,
        }

    @classmethod
    def personal(cls) -> set[str]:
        """Return all personal‑identification type strings."""
        return {
            cls.PERSON.value,
            cls.EMAIL.value,
            cls.PHONE.value,
            cls.ADDRESS.value,
            cls.DATE_OF_BIRTH.value,
            cls.AGE.value,
        }
