"""Shared fixtures for MSSQL-backed tests.

Every test gets:
- Reset settings and DB singletons
- An isolated MSSQL database (created per test, dropped after)
- For unit tests that don't need the DB, the fixture still runs but we can skip if needed.

We use Docker to run a temporary MSSQL server.
"""
from __future__ import annotations

import os
import time
from typing import Generator

import docker
import pytest
import pyodbc
from docker.models.containers import Container

from src.config import settings as settings_module
from src.db import session as session_module

# Mutate the global state to reset singletons between tests
@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    """Reset cached settings + engine so env patches take effect per test."""
    settings_module._settings = None
    if session_module._engine is not None:
        session_module._engine.dispose()
    session_module._engine = None
    session_module._SessionLocal = None


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    """Provide a Docker client for the session."""
    return docker.from_env()


@pytest.fixture(scope="session")
def mssql_container(docker_client: docker.DockerClient) -> Generator[Container, None, None]:
    """Start a temporary MSSQL container for the test session.

    Uses the official Microsoft SQL Server 2022 Express image.
    """
    from docker.errors import ImageNotFound

    container = None
    try:
        # Pull the image if not present (optional, but ensures we have it)
        try:
            docker_client.images.get("mcr.microsoft.com/mssql/server:2022-latest")
        except ImageNotFound:
            print("Pulling mcr.microsoft.com/mssql/server:2022-latest...")
            docker_client.images.pull("mcr.microsoft.com/mssql/server:2022-latest")

        # Container configuration
        container = docker_client.containers.run(
            "mcr.microsoft.com/mssql/server:2022-latest",
            name=f"mssql-test-{int(time.time())}",
            environment={
                "SA_PASSWORD": "YourStrong!Passw0rd",
                "ACCEPT_EULA": "Y",
                "MSSQL_PID": "Express",
            },
            ports={"1433/tcp": ("127.0.0.1", 0)},  # Random host port
            detach=True,
            auto_remove=True,
        )
        # Wait for SQL Server to be ready
        # Poll until we can connect or timeout after 30 seconds
        timeout = time.time() + 30
        while time.time() < timeout:
            container.reload()
            if container.status == "running":
                # Try to connect to the port
                ports = container.attrs["NetworkSettings"]["Ports"]
                host_port = ports["1433/tcp"][0]["HostPort"]
                try:
                    # Use pyodbc to test connection
                    conn_str = (
                        f"Driver={{ODBC Driver 17 for SQL Server}};"
                        f"Server=127.0.0.1,{host_port};"
                        f"UID=sa;PWD=YourStrong!Passw0rd;"
                    )
                    with pyodbc.connect(conn_str, timeout=5):
                        break
                except Exception:
                    pass
            time.sleep(0.5)
        else:
            raise RuntimeError("MS SQL Server did not become ready in time")

        yield container
    finally:
        if container:
            container.stop()


@pytest.fixture
def mssql_db(mssql_container: Container, monkeypatch) -> Generator[str, None, None]:
    """Create a temporary database on the MSSQL server for a single test.

    Yields a SQLAlchemy URL for the database.
    After the test, the database is dropped.
    """
    import subprocess

    # Get the host port from the container
    client = docker.from_env()
    container = client.containers.get(mssql_container.id)
    container.reload()
    ports = container.attrs["NetworkSettings"]["Ports"]
    host_port = ports["1433/tcp"][0]["HostPort"]

    # Generate a unique database name
    db_name = f"testdb_{int(time.time() * 1000)}"

    # SQL Server ODBC driver 17 connection string for pyodbc
    odbc_str = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server=127.0.0.1,{host_port};"
        f"UID=sa;PWD=YourStrong!Passw0rd;"
    )

    # Create the database
    with pyodbc.connect(odbc_str, autocommit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE [{db_name}]")
        cursor.commit()

    # Build the SQLAlchemy URL
    # Format: mssql+pyodbc://sa:password@host:port/dbname?driver=ODBC+Driver+17+for+SQL+Server
    sqlalchemy_url = (
        f"mssql+pyodbc://sa:YourStrong!Passw0rd@127.0.0.1:{host_port}/{db_name}"
        f"?driver=ODBC+Driver+17+for+SQL+Server"
    )

    # Set the environment variable for the app
    monkeypatch.setenv("AGENT_DATABASE_URL", sqlalchemy_url)

    # Run migrations to set up the schema
    # We use alembic command line via subprocess
    env = os.environ.copy()
    # Ensure we use the same python and virtual environment
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic upgrade failed: {result.stderr}")

    try:
        yield sqlalchemy_url
    finally:
        # Drop the database
        with pyodbc.connect(odbc_str, autocommit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE [{db_name}]")
            cursor.commit()


# Keep the existing no_keys fixture for tests that want to simulate missing keys
@pytest.fixture()
def no_keys(monkeypatch):
    """Simulate 'no provider key configured' regardless of the user's .env.

    Env vars override .env values in pydantic-settings, so empty strings are
    enough — the file itself is never touched.
    """
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_LLM_MODEL", "")
    monkeypatch.setenv("AGENT_ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("AGENT_GEMINI_API_KEY", "")
    monkeypatch.setenv("AGENT_OPENROUTER_API_KEY", "")
    yield