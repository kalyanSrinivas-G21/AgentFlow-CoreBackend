# backend/tests/integration/test_cancellation_propagation.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

pytestmark = pytest.mark.asyncio

@patch("app.sandbox.runner.asyncio.create_subprocess_exec")
async def test_sandbox_cancellation_kills_container(mock_exec):
    """
    Verifies that when a worker task is actively cancelled by an API request,
    the CancellationError properly cascades down into the Sandbox Runner,
    terminating the orphaned Docker container with an explicit `docker rm -f`.
    """
    from app.sandbox.runner import run_in_sandbox
    
    # 1. Setup Mock for docker create process
    mock_create_proc = MagicMock()
    mock_create_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_create_proc.returncode = 0
    
    # 2. Setup Mock for docker start process (this will hang to allow cancellation)
    mock_start_proc = MagicMock()
    
    # Make wait() hang cooperatively so it can be cleanly cancelled
    cancelled_event = asyncio.Event()
    
    async def hang_wait():
        try:
            # Wait for cancellation signal
            await cancelled_event.wait()
            raise asyncio.CancelledError()
        except asyncio.CancelledError:
            raise
        return 0
        
    mock_start_proc.wait = AsyncMock(side_effect=hang_wait)
    
    # Make streams hang to ensure we're in the middle of execution when cancelled
    async def hang_read():
        try:
            await cancelled_event.wait()
            raise asyncio.CancelledError()
        except asyncio.CancelledError:
            raise
        return b""
    
    mock_start_proc.stdout = MagicMock()
    mock_start_proc.stdout.read = AsyncMock(side_effect=hang_read)
    mock_start_proc.stderr = MagicMock()
    mock_start_proc.stderr.read = AsyncMock(side_effect=hang_read)
    mock_start_proc.stdin = MagicMock()
    mock_start_proc.stdin.write = MagicMock()
    mock_start_proc.stdin.drain = AsyncMock()
    mock_start_proc.stdin.close = MagicMock()
    
    # 3. Setup Mock for the docker rm -f kill process (used in cancellation handler)
    mock_kill_proc = MagicMock()
    mock_kill_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_kill_proc.wait = AsyncMock(return_value=0)
    
    # 4. Setup Mock for the docker rm -f cleanup process (used in finally block)
    mock_cleanup_proc = MagicMock()
    mock_cleanup_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_cleanup_proc.wait = AsyncMock(return_value=0)
    
    # Sequence: create, start, kill (cancellation), cleanup (finally)
    mock_exec.side_effect = [mock_create_proc, mock_start_proc, mock_kill_proc, mock_cleanup_proc]
    
    # 5. Execute
    files = {"main.py": "print('Simulation payload')"}
    command = ["python", "main.py"]
    
    task = asyncio.create_task(run_in_sandbox(files, command))
    
    # Let it start
    await asyncio.sleep(0.1)
    
    # Send active cancellation signal
    task.cancel()
    cancelled_event.set()
    
    with pytest.raises(asyncio.CancelledError):
        await task
        
    # 6. Verify that docker rm -f was called (cancellation handler)
    assert mock_exec.call_count >= 3  # create, start, and at least one rm -f
    
    # Find the docker rm -f call
    rm_calls = [call for call in mock_exec.call_args_list if call[0][0] == "docker" and call[0][1] == "rm"]
    assert len(rm_calls) >= 1, "Expected at least one docker rm -f call"
    
    kill_call = rm_calls[0][0]
    assert kill_call[0] == "docker"
    assert kill_call[1] == "rm"
    assert kill_call[2] == "-f"
    assert kill_call[3].startswith("sandbox_") or kill_call[3].startswith("pytest-sandbox-")