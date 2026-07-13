# Authentication

alcf-proxy authenticates to ALCF via Globus, **built in** — no external script. You log in once per
machine; the proxy then caches the access token and refreshes it automatically as it nears its ~48h
expiry.

## One-time login

```bash
alcf-proxy auth login
```

This opens your default browser for Globus OAuth and starts a short-lived local callback server to
receive the result, then stores the refresh + access tokens (the refresh token lasts months) in
globus-sdk's standard per-platform location.

Check status any time:

```bash
alcf-proxy auth status
```

```json
{"authenticated": true, "token_hours_left": 45.7, "token_path": "/…/tokens.json"}
```

## Where the token is stored

The path is chosen by `globus-sdk` per-OS — alcf-proxy never hard-codes it. `auth status` prints the
exact path. Typical locations:

| OS | Location |
|----|----------|
| Linux | `~/.globus/app/.../inference_app/tokens.json` |
| macOS | `~/.globus/app/.../inference_app/tokens.json` |
| Windows | under `%LOCALAPPDATA%` |

!!! warning "Keep the token private"
    The refresh token is a long-lived credential. Never commit `tokens.json` to git or copy it to a
    shared directory. On Unix it is created with `-rw-------` (owner-only) — keep it that way.

## Platform-specific login

=== "Desktop (Windows / macOS / Linux)"

    Works out of the box. `alcf-proxy auth login` opens the browser and the local callback completes
    automatically.

=== "Headless / remote (SSH, no browser)"

    The local-callback flow needs a browser that can reach `localhost` on the **login machine**.
    On a headless box you have two options:

    1. **Log in on a machine with a browser** using the same OS user profile, then reuse the token
       directory, **or**
    2. **Forward the callback port over SSH** so the remote flow can complete in your local browser:

        ```bash
        # the local server flow uses a localhost port on the remote host; forward it, then run login
        ssh -L 8000:localhost:8000 user@remote-host
        # in that SSH session:
        alcf-proxy auth login
        ```

    !!! note
        A copy-paste device-code fallback is not yet implemented. If you need it, open an issue.

## Token lifecycle

- **Access token** rotates ~every 48h. The proxy caches it and refetches only when < 5 min from
  expiry (thread-safe).
- **Refresh token** silently renews the access token and lasts months. Only if it dies (~6 months
  idle) do you need to run `alcf-proxy auth login` again.
- The token lives **only in the proxy process memory** and is injected as an `Authorization: Bearer`
  header. Your CLIs send a dummy key; they never see the real token.

Next: [Quickstart](quickstart.md).
