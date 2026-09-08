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
    
    # Mock the docker create process
    mock_create_proc = MagicMock()
    mock_create_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_create_proc.returncode = 0
    
    # Mock the docker start process
    mock_start_proc = MagicMock()
    mock_start_proc.returncode = 0
    mock_start_proc.wait = AsyncMock()
    
    mock_stdout = MagicMock()
    mock_stdout.read = AsyncMock(side_effect=[b"SUCCESS", b""]) # Return bytes, then EOF
    mock_start_proc.stdout = mock_stdout
    
    mock_stderr = MagicMock()
    mock_stderr.read = AsyncMock(side_effect=[b""])
    mock_start_proc.stderr = mock_stderr
    
    mock_start_proc.stdin = MagicMock()
    mock_start_proc.stdin.write = MagicMock()
    mock_start_proc.stdin.drain = AsyncMock()
    mock_start_proc.stdin.close = MagicMock()
    
    # Mock the cleanup process
    mock_cleanup_proc = MagicMock()
    mock_cleanup_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_cleanup_proc.wait = AsyncMock(return_value=0)
    
    # Sequence: create, start, cleanup
    mock_exec.side_effect = [mock_create_proc, mock_start_proc, mock_cleanup_proc]
    
    files = {"test.py": "print('ok')"}
    await run_in_sandbox(files, ["python", "test.py"])
    
    # Verify the docker create command arguments (first call)
    create_args = mock_exec.call_args_list[0][0]
    
    assert "docker" in create_args
    assert "create" in create_args
    assert "--network=none" in create_args
    assert "--cap-drop=ALL" in create_args
    assert "--security-opt=no-new-privileges:true" in create_args
    assert "--read-only" in create_args
    assert "--pids-limit=64" in create_args

@patch('app.sandbox.runner.asyncio.create_subprocess_exec')
async def test_sandbox_output_truncation(mock_exec):
    """Validates runaway output loops are caught before causing OOM on the host."""
    
    # Mock the docker create process
    mock_create_proc = MagicMock()
    mock_create_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_create_proc.returncode = 0
    
    # Mock the docker start process
    mock_start_proc = MagicMock()
    mock_start_proc.returncode = 0
    mock_start_proc.wait = AsyncMock()
    
    # Simulate a massive stream of data (exceeding 100KB)
    mock_stdout = MagicMock()
    large_chunk = b"A" * 60000 # 60KB per read
    # Two reads will equal 120KB, surpassing the 100KB limit
    mock_stdout.read = AsyncMock(side_effect=[large_chunk, large_chunk, b""]) 
    mock_start_proc.stdout = mock_stdout
    
    mock_stderr = MagicMock()
    mock_stderr.read = AsyncMock(side_effect=[b""])
    mock_start_proc.stderr = mock_stderr
    
    mock_start_proc.stdin = MagicMock()
    mock_start_proc.stdin.write = MagicMock()
    mock_start_proc.stdin.drain = AsyncMock()
    mock_start_proc.stdin.close = MagicMock()
    
    # Mock the cleanup process
    mock_cleanup_proc = MagicMock()
    mock_cleanup_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_cleanup_proc.wait = AsyncMock(return_value=0)
    
    # Sequence: create, start, cleanup
    mock_exec.side_effect = [mock_create_proc, mock_start_proc, mock_cleanup_proc]

    files = {"flood.py": "print('A' * 150000)"}
    result = await run_in_sandbox(files, ["python", "flood.py"])
    
    assert "TRUNCATED_BY_SANDBOX_QUOTA" in result.stdout
    assert len(result.stdout) < 110000 # 100KB limit + TRUNCATED message overhead