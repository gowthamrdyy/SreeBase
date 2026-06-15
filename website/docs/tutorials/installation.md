# Installation

This page shows how to run SreeBase locally.

## Option 1: Install from GitHub

Since SreeBase is actively in development and not yet published to PyPI, you can install the CLI globally directly from the GitHub repository.

**Using `pipx` (Recommended):**
```bash
pipx install git+https://github.com/gowthamrdyy/SreeBase.git
```

**Using `pip`:**
```bash
pip install git+https://github.com/gowthamrdyy/SreeBase.git
```

Start the server:

```bash
sreebase serve
```

By default, the server listens on:

```text
127.0.0.1:6969
```

## Option 2: Run From This Repository

From the project folder:

```bash
python -m sreebase serve
```

If your system uses `python3`:

```bash
python3 -m sreebase serve
```

## Start the CLI

Open a second terminal:

```bash
sreebase shell
```

On a fresh database, create your first admin user:

```sql
create user admin password "supersecret" role admin
```

After that, reconnect with a username:

```bash
sreebase shell -u admin
```

## Where Data Is Stored

By default, SreeBase writes files into:

```text
./data
```

Use another directory:

```bash
sreebase serve --data-dir ./my_data
```

## Docker

```bash
docker compose up --build
```

The compose file maps the server to port `6969` and stores data in a local volume folder.

