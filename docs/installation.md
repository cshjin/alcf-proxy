# Installation

alcf-proxy runs on **Linux, macOS, and Windows** and requires **Python ≥ 3.10**. All dependencies
(including `globus-sdk` for auth) install automatically — you do **not** need ALCF's
`inference_auth_token.py`.

## From PyPI (recommended)

=== "pip"

    ```bash
    pip install alcf-proxy
    ```

=== "uv / uvx"

    ```bash
    # run without installing
    uvx alcf-proxy serve

    # or install as a tool
    uv tool install alcf-proxy
    ```

=== "pipx"

    ```bash
    pipx install alcf-proxy
    ```

Verify:

```bash
alcf-proxy --help
```

## From source (development)

```bash
git clone https://github.com/cshjin/alcf-proxy
cd alcf-proxy
pip install -e .            # editable install
pip install -e ".[dev]"     # + test/build tooling
pip install -e ".[docs]"    # + docs tooling (mkdocs)
```

!!! note "Editable installs are path-bound"
    An editable install records the absolute path of the checkout. If you move or rename the
    directory, re-run `pip install -e .`.

## Platform notes

- **Windows / macOS / Linux** are all first-class. Config and token paths are resolved per-OS
  automatically (via `platformdirs` and `globus-sdk`) — no hard-coded `~/.globus` or `~/.config`
  assumptions.
- Config file location:
    - Linux: `~/.config/alcf-proxy/config.yaml`
    - macOS: `~/Library/Application Support/alcf-proxy/config.yaml`
    - Windows: `%APPDATA%\alcf-proxy\config.yaml`

Next: [Authentication](authentication.md).
