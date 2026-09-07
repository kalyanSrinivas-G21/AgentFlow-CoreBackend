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
    
    # 1. Setup Mock for main docker run process
    mock_process = MagicMock()
    
    # Make wait() hang cooperatively so it can be cleanly cancelled
    async def hang_wait():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        return 0
        
    mock_process.wait = AsyncMock(side_effect=hang_wait)
    
    # Make streams return empty to close the read tasks instantly (preventing infinite loops)
    mock_process.stdout.read = AsyncMock(return_value=b"")
    mock_process.stderr.read = AsyncMock(return_value=b"")
    
    # 2. Setup Mock for the docker rm -f kill process
    mock_kill_proc = MagicMock()
    mock_kill_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_kill_proc.wait = AsyncMock(return_value=0)
    
    # Sequence: First call returns run proc, second returns kill proc
    mock_exec.side_effect = [mock_process, mock_kill_proc]
    
    # 3. Execute
    files = {"main.py": "print('Simulation payload')"}
    command = ["python", "main.py"]
    
    task = asyncio.create_task(run_in_sandbox(files, command))
    
    # Let it start
    await asyncio.sleep(0.1)
    
    # Send active cancellation signal
    task.cancel()
    
    with pytest.raises(asyncio.CancelledError):
        await task
        
    # 4. Verify
    assert mock_exec.call_count == 2
    
    kill_call = mock_exec.call_args_list[1][0]
    assert kill_call[0] == "docker"
    assert kill_call[1] == "rm"
    assert kill_call[2] == "-f"
    assert kill_call[3].startswith("sandbox_")