# backend/tests/integration/test_sandbox_security.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.sandbox.runner import run_in_sandbox

pytestmark = pytest.mark.asyncio

async def test_sandbox_path_traversal():
    """Validates the normalization engine actively blocks host traversal."""
    files = {"../../etc/shadow": "stolen"}
    with pytest.raises(ValueError, match="Path traversal detected"):
        await run_in_sandbox(files, ["python", "-c", "print('test')"])

@patch('app.sandbox.runner.asyncio.create_subprocess_exec')
async def test_sandbox_docker_hardening_flags(mock_exec):
    """Validates that the docker command contains the required security boundaries."""
    
    # Mock the process and its streams
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.wait = AsyncMock()
    
    mock_stdout = AsyncMock()
    mock_stdout.read = AsyncMock(side_effect=[b"SUCCESS", b""]) # Return bytes, then EOF
    mock_process.stdout = mock_stdout
    
    mock_stderr = AsyncMock()
    mock_stderr.read = AsyncMock(side_effect=[b""])
    mock_process.stderr = mock_stderr
    
    mock_exec.return_value = mock_process
    
    files = {"test.py": "print('ok')"}
    await run_in_sandbox(files, ["python", "test.py"])
    
    # Verify the command arguments
    mock_exec.assert_called_once()
    called_args = mock_exec.call_args[0]
    
    assert "docker" in called_args
    assert "run" in called_args
    assert "--network=none" in called_args
    assert "--cap-drop=ALL" in called_args
    assert "--security-opt=no-new-privileges:true" in called_args
    assert "--read-only" in called_args
    assert "--pids-limit=64" in called_args

@patch('app.sandbox.runner.asyncio.create_subprocess_exec')
async def test_sandbox_output_truncation(mock_exec):
    """Validates runaway output loops are caught before causing OOM on the host."""
    
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.wait = AsyncMock()
    
    # Simulate a massive stream of data (exceeding 100KB)
    mock_stdout = AsyncMock()
    large_chunk = b"A" * 60000 # 60KB per read
    # Two reads will equal 120KB, surpassing the 100KB limit
    mock_stdout.read = AsyncMock(side_effect=[large_chunk, large_chunk, b""]) 
    mock_process.stdout = mock_stdout
    
    mock_stderr = AsyncMock()
    mock_stderr.read = AsyncMock(side_effect=[b""])
    mock_process.stderr = mock_stderr
    
    mock_exec.return_value = mock_process

    files = {"flood.py": "print('A' * 150000)"}
    result = await run_in_sandbox(files, ["python", "flood.py"])
    
    assert "TRUNCATED_BY_SANDBOX_QUOTA" in result.stdout
    assert len(result.stdout) < 110000 # 100KB limit + TRUNCATED message overhead