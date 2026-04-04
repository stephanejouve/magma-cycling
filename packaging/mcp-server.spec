# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for magma-cycling MCP server standalone executable."""

import os
import sys
from pathlib import Path

block_cipher = None

# Project root
PROJECT_ROOT = Path(SPECPATH).parent

# Collect all magma_cycling submodules
a = Analysis(
    [str(PROJECT_ROOT / "magma_cycling" / "mcp_server.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Data files that must be bundled
        (str(PROJECT_ROOT / "magma_cycling" / "config" / "athlete_context.yaml"),
         "magma_cycling/config"),
        (str(PROJECT_ROOT / "magma_cycling" / "external" / "seed_data" / "zwift_workouts.json"),
         "magma_cycling/external/seed_data"),
        (str(PROJECT_ROOT / "magma_cycling" / "workflows" / "planner" / "templates" / "peaks_methodology.md"),
         "magma_cycling/workflows/planner/templates"),
        # Prompt files
        (str(PROJECT_ROOT / "magma_cycling" / "prompts"),
         "magma_cycling/prompts"),
    ],
    hiddenimports=[
        # AI providers (loaded dynamically)
        "magma_cycling.ai.providers.anthropic_provider",
        "magma_cycling.ai.providers.mistral_provider",
        "magma_cycling.ai.providers.openai_provider",
        "magma_cycling.ai.providers.ollama_provider",
        # MCP handlers (registered dynamically)
        "magma_cycling._mcp",
        "magma_cycling._mcp.handlers",
        "magma_cycling._mcp.schemas",
        # Workflows
        "magma_cycling.workflows",
        "magma_cycling.terrain",
        # Dependencies
        "mcp",
        "mcp.server",
        "mcp.server.stdio",
        "mcp.types",
        "pydantic",
        "dotenv",
        "yaml",
        "httpx",
        "anyio",
        "starlette",
        "uvicorn",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not needed at runtime
        "tkinter",
        "matplotlib",
        "PIL",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "black",
        "ruff",
        "isort",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="mcp-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # MCP uses stdio — must be console app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
