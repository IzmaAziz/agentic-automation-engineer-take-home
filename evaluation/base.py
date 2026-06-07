from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """Severity level used to decide whether a failure blocks shipping."""

    CRITICAL = "critical"
    ADVISORY = "advisory"


@dataclass(frozen=True)
class CheckResult:
    """Result produced by a single evaluation check."""

    check: str
    passed: bool
    severity: Severity
    message: str = ""
    order_id: str = ""
    run_id: str = ""

    @property
    def failed(self) -> bool:
        return not self.passed


class BaseCheck:
    """Base class for reusable evaluation checks."""

    name = ""
    severity = Severity.CRITICAL

    def run(self, order: dict, output: dict) -> CheckResult:
        raise NotImplementedError

    def ok(self, order_id: str = "") -> CheckResult:
        return CheckResult(self.name, True, self.severity, order_id=order_id)

    def fail(self, message: str, order_id: str = "") -> CheckResult:
        return CheckResult(self.name, False, self.severity, message, order_id)