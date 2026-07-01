SendForge Admin - Build EXE (v0.3.3)

The project folder can be moved, but a Python .venv cannot. The builder now detects
a .venv copied from another folder, removes it, and creates a clean local one.
It also runs PyInstaller through Python instead of the non-portable
Scripts\pyinstaller.exe launcher.

Steps:
1. Apply this patch over the current sendforge-admin folder.
2. Double-click build_exe.bat.
3. Wait for PyInstaller to finish.
4. Open: dist\SendForge Admin.exe or use the desktop shortcut created by the builder.

Do not copy or commit the .venv, build, or dist folders. They are machine-local
outputs and are excluded by .gitignore.

The app does not store the admin password in code.
Login flow:
- login email/ID
- password
- MFA code sent by the backend
