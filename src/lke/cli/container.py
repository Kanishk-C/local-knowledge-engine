"""Dependency Injection container."""

from typing import Any, TypeVar
from typing import cast as typing_cast

T = TypeVar("T")


class Container:
    """A lightweight dependency injection container.

    Holds singletons and resolves dependencies for the CLI and Application layers.
    """

    def __init__(self) -> None:
        self._registry: dict[type, Any] = {}

    def register(self, interface: type[T], implementation: T) -> None:
        """Register an implementation for an interface."""
        self._registry[interface] = implementation

    def resolve(self, interface: type[T]) -> T:
        """Resolve an implementation for an interface."""
        if interface not in self._registry:
            raise KeyError(f"No implementation registered for {interface.__name__}")
        return typing_cast(T, self._registry[interface])


# Global container instance
container = Container()
