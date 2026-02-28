"""
Sphinx configuration for magma-cycling documentation.

Metadata:
    Created: 2025-12-27
    Author: Magma Cycling Team
    Category: DOCS
    Status: Production
    Priority: P1
    Version: 1.0.0
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Project information
project = "Magma Cycling"
copyright = "2025-2026, Stéphane Jouve"
author = "Stéphane Jouve"
release = "2.3.0"
version = "2.3"

# Extensions
extensions = [
    "sphinx.ext.autodoc",  # Auto-generate docs from docstrings
    "sphinx.ext.napoleon",  # Google/NumPy style support
    "sphinx.ext.viewcode",  # Link to source code
    "sphinx.ext.intersphinx",  # Link to other projects
    "sphinx.ext.todo",  # Support for Todo sections
]

# Napoleon settings (Google Style)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = [("Metadata", "params_style")]

# Mock imports that fail at import time (MCP, HTTP transport)
autodoc_mock_imports = ["mcp", "mcp_http_transport"]

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
autodoc_typehints = "description"

# HTML output
html_theme = "sphinx_rtd_theme"
html_static_path = []

# Todo extension
todo_include_todos = True

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
