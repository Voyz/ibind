import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ibind import var


@dataclass
class OAuthConfig(ABC):
    """ Base Dataclass encapsulating OAuth configuration parameters. """

    @abstractmethod
    def version(self):
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