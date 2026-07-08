"""Tests for the DI container."""

import pytest

from lke.cli.container import Container


class DummyInterface:
    pass


class DummyImpl(DummyInterface):
    pass


def test_container_register_and_resolve() -> None:
    """Test registering and resolving dependencies."""
    container = Container()
    impl = DummyImpl()

    container.register(DummyInterface, impl)

    resolved = container.resolve(DummyInterface)
    assert resolved is impl


def test_container_resolve_missing() -> None:
    """Test resolving a missing dependency raises an error."""
    container = Container()

    with pytest.raises(KeyError, match="No implementation registered for DummyInterface"):
        container.resolve(DummyInterface)
