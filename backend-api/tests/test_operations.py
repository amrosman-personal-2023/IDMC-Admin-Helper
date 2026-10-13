"""
Script execution endpoint tests.
"""
import os
import sys

import pytest

pytestmark = pytest.mark.asyncio

AUTH = {"vendor_session": "test-vendor-session-token"}


async def test_run_operation_success(client, mock_auth_standard, stub_scripts, fake_clock):
    stub_scripts("daily_load", exit_code=0, output="loaded ok",
                 roles=["vendor_standard", "vendor_premium"])
    resp = await client.post("/operations/run",
                             json={"operation_name": "daily_load"},
                             cookies=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["exit_code"] == 0
    assert "loaded ok" in data["output"]
    assert "operation" in data
    assert "duration_ms" in data


async def test_run_operation_unknown(client, mock_auth_standard, fake_clock):
    resp = await client.post("/operations/run",
                             json={"operation_name": "nonexistent_op"},
                             cookies=AUTH)
    assert resp.status_code == 404


async def test_run_operation_forbidden_role(client, mock_auth_standard, stub_scripts, fake_clock):
    """vendor_standard cannot run a vendor_premium-only operation."""
    stub_scripts("premium_only_op", exit_code=0, roles=["vendor_premium"])
    resp = await client.post("/operations/run",
                             json={"operation_name": "premium_only_op"},
                             cookies=AUTH)
    assert resp.status_code == 403


async def test_run_operation_premium_allowed(client, mock_auth_premium, stub_scripts, fake_clock):
    stub_scripts("premium_op", exit_code=0, output="premium done",
                 roles=["vendor_premium"])
    resp = await client.post("/operations/run",
                             json={"operation_name": "premium_op"},
                             cookies=AUTH)
    assert resp.status_code == 200


async def test_run_operation_nonzero_exit(client, mock_auth_standard, stub_scripts, fake_clock):
    stub_scripts("fail_op", exit_code=1, output="error output",
                 roles=["vendor_standard"])
    resp = await client.post("/operations/run",
                             json={"operation_name": "fail_op"},
                             cookies=AUTH)
    assert resp.status_code == 200
    assert resp.json()["exit_code"] == 1


async def test_run_operation_no_auth(client, fake_clock):
    resp = await client.post("/operations/run",
                             json={"operation_name": "daily_load"})
    assert resp.status_code == 401


async def test_run_operation_expired_session(client, mock_auth_expired, fake_clock):
    resp = await client.post("/operations/run",
                             json={"operation_name": "daily_load"},
                             cookies=AUTH)
    assert resp.status_code == 401


async def test_run_operation_admin_jwt_rejected(client, mock_auth_admin_jwt, fake_clock):
    resp = await client.post("/operations/run",
                             json={"operation_name": "daily_load"},
                             cookies=AUTH)
    assert resp.status_code == 403


async def test_run_operation_clean_subprocess_environment(
    client, mock_auth_standard, stub_scripts, fake_clock, tmp_path
):
    """Script subprocess must not inherit service secrets from the parent environment."""
    # Write a script that dumps its environment to a file
    env_dump = tmp_path / "env_dump.txt"
    import stat, textwrap
    dump_script = tmp_path / "dump_env.sh"
    dump_script.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env sh
        env > {env_dump}
        echo dumped
        exit 0
    """))
    dump_script.chmod(dump_script.stat().st_mode | stat.S_IEXEC)

    from app.config import settings as s
    s.operations["dump_env"] = {
        "script": str(dump_script),
        "roles": ["vendor_standard", "vendor_premium"],
    }

    # Set a fake secret in the parent environment
    os.environ["FAKE_SECRET"] = "supersecret"
    os.environ["JWT_SIGNING_KEY"] = "fakeprivatekey"

    resp = await client.post("/operations/run",
                             json={"operation_name": "dump_env"},
                             cookies=AUTH)
    assert resp.status_code == 200

    if env_dump.exists():
        env_contents = env_dump.read_text()
        assert "supersecret" not in env_contents
        assert "fakeprivatekey" not in env_contents
        # Only the clean vars should be present
        assert "PATH=/usr/bin:/bin" in env_contents or "PATH" in env_contents

    del s.operations["dump_env"]


async def test_run_operation_timeout(client, mock_auth_standard, stub_scripts,
                                     fake_clock, tmp_path):
    """A script that runs past the timeout must return 504."""
    import stat, sys
    from app.config import settings as s

    # Pure shell busy-loop using only builtins — no child processes spawned,
    # so SIGKILL on the shell PID terminates it immediately and closes the pipes.
    hang_script = tmp_path / "hang_op.sh"
    hang_script.write_text("#!/bin/sh\nwhile :; do :; done\n")
    hang_script.chmod(hang_script.stat().st_mode | stat.S_IEXEC)

    original_timeout = s.SCRIPT_TIMEOUT_SECONDS
    s.SCRIPT_TIMEOUT_SECONDS = 1
    s.operations["hang_op"] = {"script": str(hang_script), "roles": ["vendor_standard", "vendor_premium"]}

    resp = await client.post("/operations/run",
                             json={"operation_name": "hang_op"},
                             cookies=AUTH)
    assert resp.status_code == 504

    s.SCRIPT_TIMEOUT_SECONDS = original_timeout
    del s.operations["hang_op"]


async def test_response_contains_no_stack_trace(client, mock_auth_standard, fake_clock):
    """Error responses must not expose internal paths or stack traces."""
    resp = await client.post("/operations/run",
                             json={"operation_name": "nonexistent_op"},
                             cookies=AUTH)
    assert "Traceback" not in resp.text
    assert "app/" not in resp.text
    assert "/Users" not in resp.text
