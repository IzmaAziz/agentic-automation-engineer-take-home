from evaluation.base import BaseCheck, Severity


class OutputIsDictCheck(BaseCheck):
    """Checks that the agent output is a dictionary."""

    name = "output_is_dict"

    def run(self, order, output):
        order_id = order.get("order_id", "")

        if not isinstance(output, dict):
            return self.fail("Output is not a dictionary.", order_id)

        return self.ok(order_id)


class RequiredFieldsCheck(BaseCheck):
    """Checks that required top-level output fields are present."""

    name = "required_fields"

    def run(self, order, output):
        order_id = order.get("order_id", "")

        required = {
            "order_id",
            "format",
            "summary",
            "pricing",
            "shipping",
            "risk_assessment",
            "processing_time_ms",
        }

        missing = sorted(required - output.keys())
        if missing:
            return self.fail(f"Missing fields: {missing}", order_id)

        return self.ok(order_id)


class OrderIdCheck(BaseCheck):
    """Checks that the output order_id matches the input order_id."""

    name = "order_id"

    def run(self, order, output):
        expected = order.get("order_id")
        actual = output.get("order_id")

        if expected != actual:
            return self.fail(f"Expected {expected}, got {actual}.", expected or "")

        return self.ok(expected or "")


class FormatCheck(BaseCheck):
    """Checks that the response format is one of the supported values."""

    name = "format"
    severity = Severity.ADVISORY

    def run(self, order, output):
        order_id = order.get("order_id", "")
        valid_formats = {"narrative", "compact", "structured"}

        if output.get("format") not in valid_formats:
            return self.fail(f"Invalid format: {output.get('format')}", order_id)

        return self.ok(order_id)


class PricingCheck(BaseCheck):
    """Validates pricing structure, quantity, and total calculation."""

    name = "pricing"

    def run(self, order, output):
        order_id = order.get("order_id", "")
        pricing = output.get("pricing")

        if not isinstance(pricing, dict):
            return self.fail("pricing is missing or invalid.", order_id)

        if pricing.get("error"):
            return self.ok(order_id)

        unit_price = pricing.get("unit_price")
        quantity = pricing.get("quantity")
        total = pricing.get("total")

        if not all(isinstance(v, (int, float)) for v in [unit_price, quantity, total]):
            return self.fail("unit_price, quantity, and total must be numeric.", order_id)

        expected_total = round(unit_price * quantity, 2)
        actual_total = round(total, 2)

        if abs(expected_total - actual_total) > 0.01:
            return self.fail(
                f"Expected total {expected_total}, got {actual_total}.",
                order_id,
            )

        expected_quantity = order.get("quantity", 1)
        if quantity != expected_quantity:
            return self.fail(
                f"Expected quantity {expected_quantity}, got {quantity}.",
                order_id,
            )

        return self.ok(order_id)


class ShippingCheck(BaseCheck):
    """Validates normalized shipping output and address validity."""

    name = "shipping"

    def run(self, order, output):
        order_id = order.get("order_id", "")
        shipping = output.get("shipping")

        if not isinstance(shipping, dict):
            return self.fail("shipping is missing or invalid.", order_id)

        required = {"street", "city", "state", "country", "zip", "valid", "confidence"}
        missing = sorted(required - shipping.keys())

        if missing:
            return self.fail(f"Missing shipping fields: {missing}", order_id)

        if not isinstance(shipping.get("valid"), bool):
            return self.fail("shipping.valid must be boolean.", order_id)

        confidence = shipping.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            return self.fail("shipping.confidence is invalid.", order_id)

        address = order.get("shipping_address", {})
        missing_required = not address.get("street") or not address.get("city")

        if missing_required and shipping.get("valid") is not False:
            return self.fail("Invalid address was not marked invalid.", order_id)

        return self.ok(order_id)


class RiskCheck(BaseCheck):
    """Validates the risk assessment structure and allowed values."""

    name = "risk"

    def run(self, order, output):
        order_id = order.get("order_id", "")
        risk = output.get("risk_assessment")

        if not isinstance(risk, dict):
            return self.fail("risk_assessment is missing.", order_id)

        required = {"risk_score", "risk_level", "recommendation", "factors"}
        missing = sorted(required - risk.keys())

        if missing:
            return self.fail(f"Missing risk fields: {missing}", order_id)

        if risk.get("risk_level") not in {"low", "medium", "high", "unknown"}:
            return self.fail("Invalid risk_level.", order_id)

        if risk.get("recommendation") not in {"approve", "review", "manual_review"}:
            return self.fail("Invalid recommendation.", order_id)

        score = risk.get("risk_score")

        if score is not None and not isinstance(score, (int, float)):
            return self.fail("risk_score must be numeric or null.", order_id)

        if isinstance(score, (int, float)) and not 0 <= score <= 1:
            return self.fail("risk_score must be between 0 and 1.", order_id)

        if not isinstance(risk.get("factors"), list):
            return self.fail("risk factors must be a list.", order_id)

        return self.ok(order_id)


class RiskFallbackCheck(BaseCheck):
    """Detects fallback risk responses caused by missing risk scoring."""

    name = "risk_fallback"
    severity = Severity.ADVISORY

    def run(self, order, output):
        order_id = order.get("order_id", "")
        risk = output.get("risk_assessment")

        if not isinstance(risk, dict):
            return self.ok(order_id)

        is_fallback = (
            risk.get("risk_score") is None
            and risk.get("risk_level") == "unknown"
            and risk.get("recommendation") == "manual_review"
        )

        if is_fallback:
            return self.fail("Risk fell back to unknown/manual_review.", order_id)

        return self.ok(order_id)


class CountryMismatchCheck(BaseCheck):
    """Checks that country mismatch is reflected in risk factors."""

    name = "country_mismatch"
    severity = Severity.ADVISORY

    def run(self, order, output):
        order_id = order.get("order_id", "")
        risk = output.get("risk_assessment")

        if not isinstance(risk, dict) or risk.get("risk_score") is None:
            return self.ok(order_id)

        shipping_country = order.get("shipping_address", {}).get("country", "US")
        billing_country = order.get("billing_country", "US")

        if shipping_country != billing_country:
            if "country_mismatch" not in risk.get("factors", []):
                return self.fail("country_mismatch factor is missing.", order_id)

        return self.ok(order_id)


class SummaryLengthCheck(BaseCheck):
    """Checks that the summary is not excessively long."""

    name = "summary_length"
    severity = Severity.ADVISORY

    def run(self, order, output):
        order_id = order.get("order_id", "")
        summary = output.get("summary")

        if not isinstance(summary, str) or not summary.strip():
            return self.fail("summary is missing or invalid.", order_id)

        if len(summary) > 350:
            return self.fail(f"Summary too long: {len(summary)} chars.", order_id)

        return self.ok(order_id)


class SummaryBoilerplateCheck(BaseCheck):
    """Checks that the summary does not contain boilerplate language."""

    name = "summary_boilerplate"
    severity = Severity.ADVISORY

    def run(self, order, output):
        order_id = order.get("order_id", "")
        summary = output.get("summary", "")

        if not isinstance(summary, str):
            return self.ok(order_id)

        bad_phrases = [
            "rapidly evolving landscape",
            "operational excellence",
            "valued stakeholders",
            "state-of-the-art",
            "best-in-class",
            "industry-leading",
        ]

        hits = [phrase for phrase in bad_phrases if phrase in summary.lower()]

        if hits:
            return self.fail(f"Boilerplate detected: {hits}", order_id)

        return self.ok(order_id)


class ProcessingTimeCheck(BaseCheck):
    """Checks that processing time is present and reasonable."""

    name = "processing_time"
    severity = Severity.ADVISORY

    def run(self, order, output):
        order_id = order.get("order_id", "")
        value = output.get("processing_time_ms")

        if not isinstance(value, (int, float)):
            return self.fail("processing_time_ms is invalid.", order_id)

        if value < 0 or value > 1000:
            return self.fail(f"Unexpected processing time: {value}ms.", order_id)

        return self.ok(order_id)


DEFAULT_CHECKS = [
    OutputIsDictCheck(),
    RequiredFieldsCheck(),
    OrderIdCheck(),
    FormatCheck(),
    PricingCheck(),
    ShippingCheck(),
    RiskCheck(),
    RiskFallbackCheck(),
    CountryMismatchCheck(),
    SummaryLengthCheck(),
    SummaryBoilerplateCheck(),
    ProcessingTimeCheck(),
]