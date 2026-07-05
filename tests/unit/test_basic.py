"""Basic unit test to verify testing setup."""

from lke import __version__


def test_version() -> None:
    """Verify the package version is a string."""
    assert isinstance(__version__, str)
