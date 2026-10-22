"""Sphinx configuration for the NI TestStand docs.

Built with `just build-docs`. .github/workflows/deploy-docs.yml deploys the build to this
repo's GitHub Pages, and the Nominal docs hub (nominal-io/pub-docs) pulls it from there and
serves it at /ni/teststand/. The reference comes from the LabVIEW export in lvdocs/ and the
step type palette (see _ext/teststand.py).
"""

import sys
from pathlib import Path

from nominal_sphinx_theme import theme_options

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "_ext"))

project = "NI TestStand"  # the name in the header, after the Nominal Docs logo
copyright = "Nominal, Inc."

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "nominal_sphinx_theme",
    "teststand",  # ref/: every step, from the LabVIEW export and the step type palette
    "site_links",  # [text](site:/quickstart/...) links to other projects on the docs hub
]

myst_enable_extensions = ["colon_fence", "deflist", "attrs_inline", "attrs_block", "fieldlist"]
# links to other sites open in a new tab
myst_links_external_new_tab = True
myst_heading_anchors = 6

# CLAUDE.md holds the rules for writing these pages; lvdocs/ holds the LabVIEW export and the
# tool that writes it. Neither is a page.
exclude_patterns = ["_build", "CLAUDE.md", "lvdocs"]

html_theme = "shibuya"
html_title = "NI TestStand"  # browser tabs and search results
html_copy_source = False
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_context = {
    "source_type": "github",
    "source_user": "nominal-io",
    "source_repo": "ni-teststand-nominal-client",
    "source_version": "main",
    "source_docs_path": "/docs/",
}
html_theme_options = theme_options(
    github_url="https://github.com/nominal-io/ni-teststand-nominal-client",
    nav_links=[
        {"title": "Guides", "url": "index"},
        {"title": "Examples", "url": "examples/index"},
        {"title": "Reference", "url": "ref/index"},
    ],
)
