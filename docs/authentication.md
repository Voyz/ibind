# Authentication 

There currently are two ways you can authenticate with IBKR CP Web API:

1. Using [Client Portal Gateway](#gateway)
1. Using [OAuth 1.0a](#oauth1a)

Few observations to help you chose:
* [Client Portal Gateway][gateway] has been available for longer and [IBeam][ibeam] greatly simplifies its setup and maintenance, making this a quicker solution to get started than OAuth 1.0a.
* However, using the Gateway comes with quirks of its own, as you may need to automate 2FA for production, while the connection can sometimes become unstable.
* [OAuth 1.0a][ibkr-oauth1a] is a more modern solution which removes the need to run the additional software.
* Basic setup is more involved than that of setting up the Gateway, requiring you to generate, upload and download a bunch of keys. You also need to enable it and wait approximately 24 hours for it to be approved.
* However, once set up correctly, it will likely be a more reliable solution.

Hence:
* Consider starting with IBeam to run some early paper trading tests if you want a quick pre-packaged solution.
* Use OAuth 1.0a if there is no urgency and you can set it up correctly.


## <a name="gateway"></a> Client Portal Gateway Dependency

You need to have a running Java-based [Client Portal Gateway][gateway] in order to successfully communicate with the IBKR CP Web API.

We recommend using [IBeam][ibeam] to automate and simplify starting the Gateway and keeping it alive.
<p align="left">
    <a id="ibeam" href="https://github.com/Voyz/ibeam">
        <img src="https://github.com/Voyz/ibeam/blob/master/media/ibeam_logo.png" alt="IBeam logo" title="IBeam logo" width="300"/>
    </a>
</p>

[IBeam][ibeam] (the authentication tool) is also built and maintained by the authors of IBind (this Python client library), and the two projects are meant to support one another.

## <a name="oauth1a"></a> OAuth 1.0a

See [OAuth 1.0a][oauth1a] page for how to set it up with IBind.



[gateway]: https://www.interactivebrokers.com/docs/web-api/authentication/introduction#client-portal-gateway
[ibkr-oauth1a]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#oauth-10a
[ibeam]: https://github.com/Voyz/ibeam
[oauth1a]: ./oauth/oauth_1a.md
