"""Typed errors raised by domain invariants."""


class DomainError(RuntimeError):
    """Base class for errors that adapters may translate into protocol responses."""


class InvalidTransition(DomainError):
    """The requested command is not valid in the aggregate's current state."""


class NotFound(DomainError):
    """A requested mission, robot, or station does not exist."""


class NoEligibleRobot(DomainError):
    """No robot satisfies dispatch safety and availability constraints."""


class StationBusy(DomainError):
    """A station already has a live lease for another mission."""


class LeaseInvalid(DomainError):
    """A station lease is absent, expired, or does not match the request."""


class DuplicateMissionConflict(DomainError):
    """A mission ID was reused with a different immutable payload."""


class RecoveryLimitExceeded(DomainError):
    """A mission exhausted its bounded autonomous recovery budget."""


class TrafficConflict(DomainError):
    """A traffic zone is reserved by another robot or mission."""
