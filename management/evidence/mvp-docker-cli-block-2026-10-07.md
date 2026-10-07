# MVP Docker CLI block — 2026-10-07

User-provided output from repository-root `make run` reached the release recipe, then GNU Make failed to create `docker build -t apertus-lab-mvp .` with Windows error `CreateProcess ... The system cannot find the file specified`.

Outcome: Docker CLI was not resolvable by that native Windows Make process. Docker image build did not start and no API request was sent. The user's intended configuration may be available in another shell/runtime; this output only establishes it was unavailable to this PowerShell process.

A read-only attempt by the agent to enumerate WSL distributions and check `docker`/`make` in WSL returned `Wsl/EnumerateDistros/Service/E_ACCESSDENIED`; no conclusion about the user's interactive WSL session is inferred.

Next: in the user's Docker-enabled Linux/WSL shell, check `command -v docker`, `docker version`, and `make --version`; set LLM_* in that same shell and run `make` from the repository root. Keep key input hidden and session-scoped.
