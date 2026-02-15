# Build Bubbly Executables

Runtime and build dependencies are separated:
- Runtime: `requirements.txt`
- Build-only: `build/requirements.txt`

## Linux

```bash
bash build/build_linux.sh
```

Output:
- `build/dist/linux/bubbly_<version-or-tag>`

## Windows

Run in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\build\build_windows.ps1
```

Output:
- `build/dist/windows/bubbly_<version-or-tag>.exe`

## Notes

- Build scripts bundle:
  - `templates/`
- Runtime config stays external (not bundled into the binary). Build scripts copy `default_conf.json` next to the executable as a starting point.
- Build artifacts are written under `build/dist`, `build/work`, and `build/spec`.
- Build on the target OS for best results (Linux on Linux, Windows on Windows).
