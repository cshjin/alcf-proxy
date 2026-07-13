"""Internalized ALCF Globus authentication (no external inference_auth_token.py).

This is a self-contained, cross-platform port of ALCF's official `inference_auth_token.py`. The
original hard-codes the token path as `~/.globus/...` with forward slashes and only uses it for an
`os.path.isfile` existence check; that check can disagree with where globus_sdk actually stores
tokens on Windows. Here we never hard-code the path: globus_sdk's own `app.token_storage.filepath`
(computed cross-platform) is the single source of truth.

globus_sdk is imported lazily inside functions so the rest of the package (and its tests) import
without requiring globus_sdk to be installed.
"""
from __future__ import annotations

import time

# Globus UserApp name and public inference client / gateway scope (from ALCF's official script).
APP_NAME = "inference_app"
AUTH_CLIENT_ID = "58fdd3bc-e1c3-4ce5-80ea-8d6b87cfb944"
GATEWAY_CLIENT_ID = "681c10cc-f684-4540-bcd7-0b4df3bc26ef"
GATEWAY_SCOPE = f"https://auth.globus.org/scopes/{GATEWAY_CLIENT_ID}/action_all"
# Identity-provider policy that guides the user to the correct login.
SESSION_POLICY = "83732ff2-9c42-4548-b5ce-17e498c84f6a"


def _auth_params():
    import globus_sdk

    return globus_sdk.gare.GlobusAuthorizationParameters(
        session_required_policies=[SESSION_POLICY]
    )


def build_app():
    """Create the Globus UserApp for ALCF inference (reuses stored tokens if present)."""
    import globus_sdk

    class _DomainBasedErrorHandler:
        def __call__(self, app, error):
            print(f"Encountered error '{error}', initiating login...")
            app.login(auth_params=_auth_params())

    return globus_sdk.UserApp(
        APP_NAME,
        client_id=AUTH_CLIENT_ID,
        scope_requirements={GATEWAY_CLIENT_ID: [GATEWAY_SCOPE]},
        config=globus_sdk.GlobusAppConfig(
            request_refresh_tokens=True,
            token_validation_error_handler=_DomainBasedErrorHandler(),
        ),
    )


def token_filepath(app=None) -> str | None:
    """Cross-platform path where globus_sdk stores this app's tokens (source of truth).

    Returns None if the storage backend does not expose a filepath.
    """
    app = app or build_app()
    ts = app.token_storage
    # ValidatingTokenStorage wraps the concrete JSONTokenStorage; unwrap to find the filepath.
    for candidate in (ts, getattr(ts, "token_storage", None), getattr(ts, "_token_storage", None)):
        fp = getattr(candidate, "filepath", None)
        if fp:
            return fp
    return None


def tokens_exist(app=None) -> bool:
    """True if a token file already exists (i.e. the user has authenticated at least once)."""
    import os

    fp = token_filepath(app)
    return bool(fp) and os.path.isfile(fp)


def authenticate():
    """Trigger the interactive (browser) login flow, forcing a fresh login."""
    app = build_app()
    app.login(auth_params=_auth_params())
    return app


def get_authorizer(app=None):
    """Return the gateway authorizer (reusing stored tokens; refreshing as needed)."""
    app = app or build_app()
    return app.get_authorizer(GATEWAY_CLIENT_ID)


def access_token(app=None) -> str:
    """Return a valid access token, refreshing it if necessary."""
    auth = get_authorizer(app)
    auth.ensure_valid_token()
    return auth.access_token


def seconds_until_expiry(app=None) -> float:
    """Seconds until the current access token expires (negative if already expired)."""
    auth = get_authorizer(app)
    return auth.expires_at - time.time()
