import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ibind import var


@dataclass
class OAuthConfig(ABC):
    """
    Base dataclass encapsulating OAuth configuration parameters.

    This abstract base class defines the common attributes and methods for managing
    OAuth authentication settings. It provides default configuration values for handling
    the initialization, maintenance, and shutdown of OAuth authentication.
    """

    @abstractmethod
    def version(self):
        """
        Returns the OAuth version.

        This abstract method must be implemented by subclasses to return the OAuth protocol
        version being used (e.g., OAuth 1.0a or OAuth 2.0).

        Raises:
            NotImplementedError: If called directly from the base class.
        """
        raise NotImplementedError()

    init_oauth: bool = var.IBIND_INIT_OAUTH
    """ Whether OAuth should be automatically initialised. """

    init_brokerage_session: bool = var.IBIND_INIT_OAUTH
    """ Whether initialize_brokerage_session should be called automatically on startup. """

    maintain_oauth: bool = var.IBIND_MAINTAIN_OAUTH
    """ Whether OAuth should be automatically maintained. """

    shutdown_oauth: bool = var.IBIND_SHUTDOWN_OAUTH
    """ Whether OAuth should be automatically stopped on termination. """

    def copy(self, **kwargs):
        """
        Returns a shallow copy of the OAuthConfig with optional modifications.

        Args:
            **kwargs: Arbitrary keyword arguments representing attributes to modify in the copy.
        """
        copied = copy.copy(self)
        for kwarg, value in kwargs.items():
            if not hasattr(copied, kwarg):
                raise AttributeError(f'OAuthConfig does not have attribute "{kwarg}"')
            setattr(copied, kwarg, value)
        return copied