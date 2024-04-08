from typing import TYPE_CHECKING

from requests import ConnectTimeout

from ibind.base.rest_client import Result
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class SessionMixin():
    def authentication_status(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.post('iserver/auth/status')

    def initialize_brokerage_session(self: 'IbkrClient', publish: bool, compete: bool) -> Result:  # pragma: no cover
        return self.post('iserver/auth/ssodh/init', {'publish': publish, 'compete': compete})

    def logout(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.post('logout')

    def tickle(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.post('tickle', log=False)

    def reauthenticate(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.post('iserver/reauthenticate')

    def validate(self: 'IbkrClient') -> Result:  # pragma: no cover
        return self.get('/sso/validate')

    def check_health(self: 'IbkrClient'):
        """
        Verifies the health and authentication status of the IBKR Gateway server.

        This method checks if the Gateway server is alive and whether the user is authenticated.
        It also checks for any competing connections and the connection status.

        Returns:
            bool: True if the Gateway server is authenticated, not competing, and connected, False otherwise.

        Raises:
            AttributeError: If the Gateway health check request returns invalid data.
        """
        try:
            result = self.tickle()
        except Exception as e:
            if isinstance(e, ExternalBrokerError) and e.status_code == 401:
                _LOGGER.info(f'Gateway session is not authenticated.')
            elif isinstance(e, ConnectTimeout):
                _LOGGER.error(f'ConnectTimeout raised when communicating with the Gateway. This could indicate that the Gateway is not running or other connectivity issues.')
            else:
                _LOGGER.error(f'Tickle request failed: {e}')
            return False

        if result.data.get('iserver', {}).get('authStatus', {}).get('authenticated', None) is None:
            raise AttributeError(f'Health check requests returns invalid data: {result}')

        auth_status = result.data['iserver']['authStatus']

        authenticated = auth_status['authenticated']
        competing = auth_status['competing']
        connected = auth_status['connected']

        return authenticated and (not competing) and connected
