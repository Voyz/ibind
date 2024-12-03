from typing import TYPE_CHECKING

from requests import ConnectTimeout

from ibind.base.rest_client import Result
from ibind.support.errors import ExternalBrokerError
from ibind.support.logs import project_logger

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class SessionMixin():
    """
    https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#session
    """

    def authentication_status(self: 'IbkrClient') -> Result:  # pragma: no cover
        """
        Current Authentication status to the Brokerage system. Market Data and Trading is not possible if not authenticated, e.g. authenticated shows false.
        """
        return self.post('iserver/auth/status')

    def initialize_brokerage_session(self: 'IbkrClient', publish: bool, compete: bool) -> Result:  # pragma: no cover
        """
        After retrieving the access token and subsequent Live Session Token, customers can initialize their brokerage session with the ssodh/init endpoint.
        NOTE: This is essential for using all /iserver endpoints, including access to trading and market data.

        Parameters:
            publish (Boolean): Determines if the request should be sent immediately. Users should always pass true. Otherwise, a ‘500’ response will be returned.
            compete (Boolean): Determines if other brokerage sessions should be disconnected to prioritize this connection.
        """
        return self.post(path='iserver/auth/ssodh/init', params={'publish': publish, 'compete': compete})

    def logout(self: 'IbkrClient') -> Result:  # pragma: no cover
        """
        Logs the user out of the gateway session. Any further activity requires re-authentication.
        """
        return self.post('logout')

    def tickle(self: 'IbkrClient') -> Result:  # pragma: no cover
        """
        If the gateway has not received any requests for several minutes an open session will automatically timeout. The tickle endpoint pings the server to prevent the session from ending. It is expected to call this endpoint approximately every 60 seconds to maintain the connection to the brokerage session.
        """
        return self.post('tickle', log=False)

    def reauthenticate(self: 'IbkrClient') -> Result:  # pragma: no cover
        """
        When using the CP Gateway, this endpoint provides a way to reauthenticate to the Brokerage system as long as there is a valid brokerage session.
        All interest in reauthenticating the gateway session should be handled using the /iserver/auth/ssodh/init endpoint.
        """
        return self.post('iserver/reauthenticate')

    def validate(self: 'IbkrClient') -> Result:  # pragma: no cover
        """
        Validates the current session for the SSO user.
        """
        return self.get('/sso/validate')

    def check_health(self: 'IbkrClient') -> bool:
        """
        Verifies the health and authentication status of the IBKR Gateway server.

        This method checks if the Gateway server is alive and whether the user is authenticated.
        It also checks for any competing connections and the connection status.

        Returns:
            bool: True if the Gateway server is authenticated, not competing, and connected, False otherwise.

        Raises:
            AttributeError: If the Gateway health check request returns invalid data.

        Note:
            - This method returns a boolean directly without the `Result` dataclass.
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
