# Docker Desktop installation and engine check — 2026-10-07

Installed at the user's request from Docker's official Windows installer (`https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe`) using per-user mode and the `wsl-2` backend. Docker's official Windows installation guide documents per-user installation and WSL 2 backend flags: <https://docs.docker.com/desktop/setup/install/windows-install/>.

- Docker Desktop: 4.94.0 (241994), installed under `%LOCALAPPDATA%\Programs\DockerDesktop`.
- WSL: 2.6.1.
- Docker Desktop process: running.
- Docker client/server: 29.8.2 / 29.8.2.
- Engine OS type: `linux`.
- User PATH now includes the Docker Desktop CLI directory; the already-running PowerShell/tool process has a stale PATH and needs a new shell before `docker` resolves by name.
- `docker` was not found inside the Ubuntu WSL distribution during a read-only check, so that distribution's WSL integration remains off/unverified. This is not required to launch from Windows PowerShell; enable it in Docker Desktop Settings > Resources > WSL Integration if desired.
- No API request or Docker application build was run during installation verification.
