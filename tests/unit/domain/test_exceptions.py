"""Tests for domain exceptions."""

from lke.domain.exceptions import ConfigurationError, DomainError, InfrastructureError, LKEError


def test_exception_hierarchy() -> None:
    """Test that all exceptions inherit from LKEError."""
    assert issubclass(DomainError, LKEError)
    assert issubclass(InfrastructureError, LKEError)
    assert issubclass(ConfigurationError, LKEError)


def test_exception_instantiation() -> None:
    """Test exception instantiation."""
    err = DomainError("Something went wrong")
    assert str(err) == "Something went wrong"
