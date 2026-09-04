# backend/app/sandbox/runner.py
import asyncio
import tempfile
import uuid
import os
from pathlib import Path

class SandboxResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

async def run_in_sandbox(files: dict[str, str], command: list[str], timeout_s: float = 30.0) -> SandboxResult:
    """
    Executes a command inside an ephemeral, network-isolated Docker container.
    """
    container_name = f"sandbox_{uuid.uuid4().hex}"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        host_workspace = Path(temp_dir) / "workspace"
        host_scratch = Path(temp_dir) / "scratch"
        
        host_workspace.mkdir(parents=True, exist_ok=True)
        host_scratch.mkdir(parents=True, exist_ok=True)
        
        # Ensure the non-root sandboxuser can write to the scratch volume
        os.chmod(host_scratch, 0o777)
        
        # Write code files to the read-only workspace
        for filename, content in files.items():
            file_path = host_workspace / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            
        docker_cmd = [
            "docker", "run", "--rm",
            f"--name={container_name}",
            "--network=none",
            "--memory=256m",
            "--cpus=0.5",
            "--pids-limit=64",
            "--read-only",
            "--tmpfs", "/tmp",
            "-v", f"{host_workspace.resolve()}:/workspace:ro",
            "-v", f"{host_scratch.resolve()}:/workspace/scratch:rw",
            "-w", "/workspace",
            "ps26117-sandbox-base"
        ] + command
        
        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_s)
                return SandboxResult(
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    exit_code=process.returncode
                )
            except asyncio.TimeoutError:
                # If execution hangs, forcefully kill the rogue container
                kill_proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await kill_proc.communicate()
                raise
        finally:
            pass # TemporaryDirectory context manager auto-cleans temp_dir