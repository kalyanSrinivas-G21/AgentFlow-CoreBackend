# backend/app/sandbox/runner.py
import asyncio
import io
import tarfile
import tempfile
import uuid
import os
from pathlib import Path

class SandboxResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

MAX_OUTPUT_BYTES = 100 * 1024  # 100 KB output limit

async def _read_stream_limited(stream: asyncio.StreamReader, limit: int) -> bytes:
    output = bytearray()
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        output.extend(chunk)
        if len(output) > limit:
            output = output[:limit]
            output.extend(b"\n...[TRUNCATED_BY_SANDBOX_QUOTA]...")
            break
    return bytes(output)

async def run_in_sandbox(files: dict[str, str], command: list[str], timeout_s: float = 30.0) -> SandboxResult:
    container_name = f"sandbox_{uuid.uuid4().hex}"
    
    for filename in files.keys():
        norm_path = os.path.normpath(filename)
        if norm_path.startswith("/") or norm_path.startswith("..") or ".." in norm_path:
            raise ValueError(f"Path traversal detected and blocked: {filename}")

    with tempfile.TemporaryDirectory() as temp_dir:
        host_workspace = Path(temp_dir) / "workspace"
        
        host_workspace.mkdir(parents=True, exist_ok=True)
        
        for filename, content in files.items():
            file_path = host_workspace / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as tar:
            for filename, content in files.items():
                data = content.encode("utf-8")
                entry = tarfile.TarInfo(filename)
                entry.size = len(data)
                entry.mode = 0o444
                tar.addfile(entry, io.BytesIO(data))
        archive_data = archive.getvalue()
            
        docker_cmd = [
            "docker", "create",
            "-i",
            f"--name={container_name}",
            "--network=none",
            "--memory=256m",
            "--cpus=0.5",
            "--pids-limit=64",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--read-only",
            "--tmpfs", "/workspace:rw,mode=1777",
            "--tmpfs", "/tmp",
            "-w", "/workspace",
            "ps26117-sandbox-base",
            "sh", "-c",
            "tar -xf - -C /workspace && find /workspace -type f -exec chmod a-w {} + && exec \"$@\"",
            "sandbox"
        ] + command
        
        try:
            create_process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, create_stderr = await create_process.communicate()
            if create_process.returncode != 0:
                return SandboxResult("", create_stderr.decode("utf-8", errors="replace"), create_process.returncode)

            process = await asyncio.create_subprocess_exec(
                "docker", "start", "-a", "-i", container_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            process.stdin.write(archive_data)
            await process.stdin.drain()
            process.stdin.close()
            
            try:
                stdout_task = asyncio.create_task(_read_stream_limited(process.stdout, MAX_OUTPUT_BYTES))
                stderr_task = asyncio.create_task(_read_stream_limited(process.stderr, MAX_OUTPUT_BYTES))
                
                await asyncio.wait_for(process.wait(), timeout=timeout_s)
                
                stdout_bytes = await stdout_task
                stderr_bytes = await stderr_task
                
                return SandboxResult(
                    stdout=stdout_bytes.decode("utf-8", errors="replace"),
                    stderr=stderr_bytes.decode("utf-8", errors="replace"),
                    exit_code=process.returncode
                )
            except asyncio.TimeoutError:
                stdout_task.cancel()
                stderr_task.cancel()
                kill_proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container_name,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await kill_proc.communicate()
                raise
            except asyncio.CancelledError:
                # Step 10.3: Active Docker sandbox termination on cancellation signal
                stdout_task.cancel()
                stderr_task.cancel()
                kill_proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container_name,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await kill_proc.communicate()
                raise
        finally:
            cleanup_proc = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", container_name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await cleanup_proc.communicate()