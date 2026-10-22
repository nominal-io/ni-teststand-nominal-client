"""The Reference page, generated from the LabVIEW export in ``docs/lvdocs`` and the step type palette.

The LabVIEW tool in ``docs/lvdocs`` (the same one labview-client uses) writes ``lvdocstring.json``,
one entry per VI and typedef in the steps' library that isn't marked to leave out, and their icons
under ``assets/``. VIs no step calls, and the typedefs, get sections of their own after the steps. Its format is in
``_ext/lvdocstring.schema.json``. The step types, their names and the VI each one calls come from
the type palette, ``teststand public directory/Components/TypePalettes/Nominal_Core_Stream_Types.ini``.
The palette puts every step in one group, so the groups on the page come from ``GROUPS`` below.

At ``builder-inited`` this writes ``ref/index.md``, gitignored and only when its content changes (so
live preview doesn't loop). It also adds the ``ts`` domain: each step registers itself, so
``{ts:step}`Create Point Buffer``` (by menu name or step type name) links to it.

Adapted from labview-client's docs/_ext/labview.py, which writes a page per VI on its palettes.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Iterator

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.domains import Domain, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

logger = logging.getLogger(__name__)

# group heading -> step type names, in page order
GROUPS = {
    "Connection": ["Nominal_Core_Open", "Nominal_Core_Close"],
    "Assets": ["Nominal_Create_Asset", "Nominal_Get_Asset", "Nominal_Update_Asset"],
    "Datasets": ["Nominal_Create_Asset_Dataset", "Nominal_Get_Dataset_by_RID"],
    "Streams and channels": [
        "Nominal_Create_Stream_from_Dataset",
        "Nominal_Find_or_Create_Stream_Channel",
        "Nominal_Update_Channel_Metadata",
        "Nominal_Destroy_Stream",
    ],
    "Writing data": [
        "Nominal_Stream_Array_to_Channel",
        "Nominal_Stream_Points_to_Channel",
        "Nominal_Stream_Waveform_to_Channel",
    ],
    "Point buffer": [
        "Nominal_Create_Point_Buffer",
        "Nominal_Add_to_Point_Buffer",
        "Nominal_Flush_Point_Buffer_to_Channel",
        "Nominal_Destroy_Point_Buffer",
    ],
    "Batch buffer": [
        "Nominal_Create_Batch_Buffer",
        "Nominal_Add_Point_to_Batch_Buffer",
        "Nominal_Flush_Batch_Buffer",
        "Nominal_Destroy_Batch_Buffer",
    ],
    "Runs": [
        "Nominal_Create_Run",
        "Nominal_Create_Run_on_Asset",
        "Nominal_Update_Run_Metadata",
        "Nominal_Update_Run_Start",
        "Nominal_Update_Run_Stop",
    ],
    "Events": [
        "Nominal_Create_Event_on_Run",
        "Nominal_Create_Event_on_Asset",
        "Nominal_Update_Event_Metadata",
        "Nominal_Update_Event_Timing",
    ],
}

_ERROR_LABELS = re.compile(r"^error (in|out)\b", re.I)
_SCALARS = {"I8", "I16", "I32", "I64", "U8", "U16", "U32", "U64", "SGL", "DBL", "EXT", "CSG", "CDB", "CXT"}


# -- The export ---------------------------------------------------------------------------------


@dataclass
class Terminal:
    label: str
    caption: str
    direction: str
    type: str
    default: str
    description: str
    tip: str
    rule: str

    @property
    def name(self) -> str:
        return self.caption or self.label

    @property
    def is_error(self) -> bool:
        return bool(_ERROR_LABELS.match(self.label)) and self.type.startswith("Cluster")


@dataclass
class VI:
    id: str
    path: str  # relative to the repo root, with backslashes
    description: str
    icon: str
    terminals: list[Terminal]

    @property
    def file(self) -> str:
        return PureWindowsPath(self.path).name


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _file(path: str) -> str:
    """The file name of an export path; "" for none."""
    return "" if not path or path.startswith("<") else PureWindowsPath(path).name


def _load_vis(export: Path) -> list[VI]:
    if not (export / "lvdocstring.json").exists():
        raise RuntimeError(f"{export / 'lvdocstring.json'} is missing: run the LabVIEW export in docs/lvdocs")
    rows = json.loads((export / "lvdocstring.json").read_text(encoding="utf-8"))
    vis: dict[str, VI] = {}
    for r in rows:
        if r["id"] in vis:
            continue
        vis[r["id"]] = VI(
            id=r["id"],
            path=r["path"],
            description=r["description"],
            icon=_file(r["icon"]),
            terminals=[
                Terminal(
                    label=t["label"],
                    caption=t["caption"],
                    direction=t["direction"],
                    type=t["type"].replace("\r\n", "").strip(),
                    default=t["default"],
                    description=t["description"],
                    tip=t["tip strip"],
                    rule=t["wiring rule"].lower(),
                )
                for t in r["terminals"]
            ],
        )
    return list(vis.values())


# -- The palette ----------------------------------------------------------------------------------


@dataclass
class Step:
    type_name: str  # "Nominal_Core_Open"
    title: str  # the step type's menu name, "Open Connection to Nominal Core"
    default_name: str  # the name a new step gets, "Nominal Connect"
    vi_file: str  # "nominal open.vi"
    vi: VI | None = None


def _menu_fallback(type_name: str) -> str:
    return type_name.removeprefix("Nominal_").replace("_", " ")


def _load_steps(palette: Path) -> dict[str, Step]:
    """The palette's step types by name, in palette order. The palette is in TestStand's XML or
    binary format (Station Options > File > File Format Options)."""
    raw = palette.read_bytes()
    if raw.lstrip(b"\xef\xbb\xbf").startswith(b"<?xml"):
        return _load_steps_xml(palette)
    return _load_steps_binary(palette, raw)


def _literal(expr: str) -> str:
    """A TestStand string expression's text: '"Nominal Connect"' -> 'Nominal Connect'."""
    expr = expr.strip()
    return expr[1:-1] if len(expr) > 1 and expr[0] == expr[-1] == '"' else expr


def _load_steps_xml(palette: Path) -> dict[str, Step]:
    """Each step type is an element named for it under ``typelist/typedef``, with its default step
    name in ``DefaultNameFormat``, its menu name in ``Menu``'s ``ItemName`` (empty when it's the
    default name) and its VI in ``VIPath``."""
    root = ET.parse(palette).getroot()
    ns = root.tag[: root.tag.index("}") + 1] if root.tag.startswith("{") else ""
    steps: dict[str, Step] = {}
    for typedef in root.iterfind(f"{ns}typelist/{ns}typedef"):
        for el in typedef:
            name = el.tag.removeprefix(ns)
            vi_path = el.findtext(f".//{ns}VIPath/{ns}value") or ""
            if not name.startswith("Nominal_") or not vi_path:
                continue
            default_name = _literal(el.findtext(f".//{ns}DefaultNameFormat/{ns}value") or "")
            title = _literal(el.findtext(f".//{ns}Menu//{ns}ItemName/{ns}value") or "") or default_name
            if not title:
                logger.warning("TestStand palette: no menu name found for %s", name)
            steps[name] = Step(name, title or _menu_fallback(name), default_name, PureWindowsPath(vi_path).name)
    return steps


def _load_steps_binary(palette: Path, raw: bytes) -> dict[str, Step]:
    """TestStand's binary format, which NI doesn't document: a ``TOF1`` header, then ``PMCZ`` and
    4 bytes, then a zlib stream. In that stream each step type's name comes first, then its
    properties, then the path of the VI it calls. Among the properties are two quoted expressions,
    its default step name and then its menu name. A string the stream already holds isn't stored
    again, so a menu name equal to the default name appears once, and a shared expression such as
    ``"%ModuleDescription"`` only under the first step.
    """
    start = raw.find(b"PMCZ")
    if not raw.startswith(b"TOF1") or start < 0:
        raise RuntimeError(f"{palette} is in neither TestStand format _load_steps reads")
    strings = [m.group().decode("ascii") for m in re.finditer(rb"[ -~]{4,}", zlib.decompress(raw[start + 8:]))]
    steps: dict[str, Step] = {}
    current: Step | None = None
    names: list[str] = []
    for s in strings:
        if s == "TypeGroups":  # the menu layout follows the types
            break
        if re.fullmatch(r"Nominal_\w+", s):
            current, names = Step(s, "", "", ""), []
        elif current is None or current.vi_file:
            continue
        elif s.startswith('"') and s.endswith('"') and "%" not in s:
            names.append(s[1:-1])
        elif m := re.fullmatch(r"NominalCoreSteps\.lvlibp\\(.+\.vi)", s):
            current.vi_file = m.group(1)
            if not names:
                logger.warning("TestStand palette: no menu name found for %s", current.type_name)
            current.title = names[-1] if names else _menu_fallback(current.type_name)
            current.default_name = names[0] if names else ""
            steps[current.type_name] = current
    return steps


# -- Text -----------------------------------------------------------------------------------------

_ESCAPE = re.compile(r"([\\*_\[\]<>{}|&])")
_BOLD = re.compile(r"<\s*(/?)\s*b\s*>", re.I)
# bold around nothing but spaces, which LabVIEW leaves behind; as ** ** it would read as a rule
_EMPTY_BOLD = re.compile(r"<\s*b\s*>(\s*)<\s*/\s*b\s*>", re.I)


def _inline(line: str) -> str:
    """One line of LabVIEW text as Markdown: <b> becomes bold, `code` stays code, the rest is literal."""
    out = []
    for i, part in enumerate(re.split(r"(`[^`\n]*`)", line)):
        if i % 2:
            out.append(part)
        else:
            out.append(_ESCAPE.sub(r"\\\1", part).replace("\x02", "**"))
    return "".join(out)


def lv_text(text: str) -> str:
    """A LabVIEW description as Markdown, with its line breaks kept, as Context Help shows them."""
    text = _EMPTY_BOLD.sub(r"\1", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = _BOLD.sub("\x02", text).strip()
    paragraphs = re.split(r"\n\s*\n", text)
    return "\n\n".join("  \n".join(_inline(line.strip()) for line in p.split("\n") if line.strip()) for p in paragraphs if p.strip())


def _indent(text: str, by: str = "  ") -> str:
    return "\n".join(by + line if line else "" for line in text.split("\n"))


# -- Types and defaults ---------------------------------------------------------------------------


@dataclass
class TypeInfo:
    text: str
    elements: list[tuple[str, TypeInfo]]


def _value(xml: str) -> ET.Element | None:
    """The typed element of a terminal's <LvVariant> default."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    return next((c for c in root if c.tag != "Name"), None)


def _describe(el: ET.Element) -> TypeInfo:
    tag = el.tag
    if tag in _SCALARS or tag in ("Boolean", "String", "Path", "Timestamp"):
        return TypeInfo(tag, [])
    if tag == "EW":
        return TypeInfo("Enum", [])
    if tag == "DBLWaveform":
        return TypeInfo("Waveform", [])
    if tag == "Object":
        return TypeInfo(el.findtext("Class") or el.findtext("Name") or "Class", [])
    if tag == "Cluster":
        elements = [((c.findtext("Name") or "").strip(), _describe(c)) for c in el if c.tag not in ("Name", "NumElts")]
        return TypeInfo("Cluster", elements)
    if tag == "Array":
        dims = len(el.findall("Dimsize"))
        inner = next((c for c in el if c.tag not in ("Name", "Dimsize")), None)
        info = _describe(inner) if inner is not None else TypeInfo("?", [])
        return TypeInfo(f"{dims}D Array of {info.text}", info.elements)
    return TypeInfo(tag, [])


def _type(t: Terminal) -> TypeInfo:
    if t.is_error:
        return TypeInfo("Error cluster", [])
    if t.type.startswith("Map{"):
        return TypeInfo("Map (" + t.type[4:-1].replace("->", "→ ").replace("  ", " ") + ")", [])
    if t.type.startswith("enum["):
        return TypeInfo("Enum", [])
    el = _value(t.default)
    if el is None or el.tag in ("Default", "Map") or (el.tag == "Object" and t.type.endswith(".lvclass")):
        return TypeInfo(t.type, [])
    info = _describe(el)
    if m := re.match(r"Cluster\[(.+?)\]", t.type):  # a typedef
        info.text += f" ({m.group(1).split(':')[-1]})"
    return info


def _number(value: str) -> str:
    try:
        return f"{float(value):g}"
    except ValueError:
        return value


def _choices(t: Terminal) -> tuple[list[str], int]:
    el = _value(t.default)
    if el is None or el.tag != "EW":
        return [], -1
    try:
        selected = int(el.findtext("Val") or -1)
    except ValueError:
        selected = -1
    return [c.text or "" for c in el.findall("Choice")], selected


def _default(t: Terminal) -> str:
    """The default of an optional or recommended input, as text; "" when it isn't worth showing."""
    if t.direction != "input" or t.rule == "required" or t.is_error:
        return ""
    el = _value(t.default)
    if el is None:
        return ""
    value = el.findtext("Val") or ""
    if el.tag in _SCALARS:
        return _number(value) if value else ""
    if el.tag == "Boolean":
        return "TRUE" if value == "1" else "FALSE"
    if el.tag in ("String", "Path"):
        return value
    if el.tag == "EW":
        choices, selected = _choices(t)
        return choices[selected] if 0 <= selected < len(choices) else ""
    return ""


def _code(text: str) -> str:
    """Inline code that may itself contain backticks."""
    ticks = "``" if "`" in text else "`"
    pad = " " if ticks == "``" else ""
    return f"{ticks}{pad}{text}{pad}{ticks}"


def _elements(elements: list[tuple[str, TypeInfo]], depth: int = 0) -> list[str]:
    lines = []
    for name, info in elements:
        label = f"{_code(name)} " if name else ""
        lines.append("  " * depth + f"- {label}{_inline(info.text)}")
        lines += _elements(info.elements, depth + 1)
    return lines


# -- The page -------------------------------------------------------------------------------------


class Pages:
    def __init__(self, app: Sphinx) -> None:
        self.srcdir = Path(app.srcdir)
        self.export = Path(app.config.teststand_export_dir)
        self.root = Path(app.config.teststand_repo_root)
        self.palette = self.root / app.config.teststand_palette
        self.github = app.config.teststand_github_url.rstrip("/")
        try:
            self.images = "/" + self.export.relative_to(self.srcdir).as_posix() + "/assets"
        except ValueError:
            raise RuntimeError(f"teststand_export_dir ({self.export}) must be inside the docs folder") from None
        self.written: set[Path] = set()

    def source_url(self, path: str) -> str:
        return f"{self.github}/blob/HEAD/{urllib.parse.quote(PureWindowsPath(path).as_posix())}"

    def image(self, name: str) -> str | None:
        """The docs path of an exported image, or None (with a warning) if the file is missing."""
        if not name:
            return None
        if not (self.export / "assets" / name).exists():
            logger.warning("LabVIEW export: assets/%s is missing", name)
            return None
        return f"{self.images}/{name}"

    def write(self, rel: str, content: str) -> None:
        path = self.srcdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
        self.written.add(path)

    def prune(self, folder: str) -> None:
        """Remove generated files from an earlier build that this build didn't write."""
        base = self.srcdir / folder
        for path in sorted(base.rglob("*"), reverse=True):
            if path.is_file() and path not in self.written:
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    def terminals(self, vi: VI) -> list[str]:
        out: list[str] = []
        for direction, title in (("input", "Inputs"), ("output", "Outputs")):
            # exported in connector pane order; reversed, they read top to bottom as on the pane
            terms = [t for t in reversed(vi.terminals) if t.direction == direction]
            terms.sort(key=lambda t: t.is_error)
            if not terms:
                continue
            out += [f"```{{rubric}} {title}", "```", ""]
            for t in terms:
                badge = {"required": " {bdg-primary-line}`required`", "optional": " {bdg-secondary-line}`optional`"}
                out.append(f"**{_inline(t.name)}**{badge.get(t.rule, '') if direction == 'input' else ''}")
                info = _type(t)
                first = _code(info.text)
                if default := _default(t):
                    first += f" · default {_code(default)}"
                body = [first]
                if info.elements:
                    body += ["", *_elements(info.elements)]
                choices, _ = _choices(t)
                if choices:
                    body += ["", "One of " + ", ".join(_code(c) for c in choices) + "."]
                text = "" if t.is_error else lv_text(t.description or t.tip)
                if text:
                    body += ["", text]
                out.append(": " + body[0])
                out += [_indent(line) if line else "" for line in "\n".join(body[1:]).split("\n")] if len(body) > 1 else []
                out.append("")
        return out

    def step(self, step: Step) -> list[str]:
        vi = step.vi
        assert vi is not None
        meta = [_code(step.type_name)]
        if step.default_name and step.default_name != step.title:
            meta.append(f"New steps are named **{_inline(step.default_name)}**")
        meta.append(f"Calls [{_code(vi.file)}]({self.source_url(vi.path)})")
        lines = [
            f"### {_inline(step.title)}",
            "",
            f"```{{ts:step}} {step.type_name}",
            f":title: {step.title}",
            "```",
            "",
            "{.lv-meta}",
            " · ".join(meta),
            "",
        ]
        return lines + self.header(vi) + self.terminals(vi)

    def other(self, vi: VI) -> list[str]:
        """A VI or typedef in the export that no step calls."""
        title = re.sub(r"\.(vim?|ctl)$", "", vi.file)
        lines = [f"### {_inline(title)}", "", "{.lv-meta}", f"[{_code(vi.file)}]({self.source_url(vi.path)})", ""]
        return lines + self.header(vi) + self.terminals(vi)

    def header(self, vi: VI) -> list[str]:
        lines = ["::::{container} lv-header"]
        if icon := self.image(vi.icon):
            lines += [f"![]({icon}){{.lv-icon}}", ""]
        if text := lv_text(vi.description):
            lines += [":::{container} lv-description", text, ":::"]
        return lines + ["::::", ""]

    def generate(self) -> None:
        steps = _load_steps(self.palette)
        by_file = {vi.file.casefold(): vi for vi in _load_vis(self.export)}
        for step in steps.values():
            step.vi = by_file.pop(step.vi_file.casefold(), None)
            if step.vi is None:
                logger.warning("LabVIEW export: %s, which %s calls, isn't in lvdocstring.json", step.vi_file, step.type_name)
        # what's left is in the export but called by no step: VIs, and typedefs (.ctl)
        others = sorted(by_file.values(), key=lambda vi: vi.file.casefold())
        typedefs = [vi for vi in others if vi.file.casefold().endswith(".ctl")]
        others = [vi for vi in others if vi not in typedefs]
        grouped = [name for names in GROUPS.values() for name in names]
        for name in grouped:
            if name not in steps:
                logger.warning("TestStand reference: %s is in GROUPS but not in the palette", name)
        for name in steps:
            if name not in grouped:
                logger.warning("TestStand reference: add %s to GROUPS in _ext/teststand.py", name)

        rest = " and ".join(part for part, items in (("the other VIs", others), ("the types", typedefs)) if items)
        lead = ("The steps in the **Nominal Core** step group. Each one calls a VI, and that VI's inputs and "
                "outputs are the step's parameters.")
        if rest:
            lead += f" {rest[0].upper()}{rest[1:]} in the steps' library follow."
        lines = ["# Reference", "", "{.lead}", lead, ""]
        for group, names in GROUPS.items():
            lines += [f"## {group}", ""]
            for name in names:
                if (step := steps.get(name)) and step.vi:
                    lines += self.step(step)
        if others:
            lines += ["## Other VIs", "", "VIs in the steps' library that no step calls.", ""]
            for vi in others:
                lines += self.other(vi)
        if typedefs:
            lines += ["## Types", "", "Type definitions in the steps' library.", ""]
            for vi in typedefs:
                lines += self.other(vi)
        self.write("ref/index.md", "\n".join(lines).rstrip() + "\n")
        self.prune("ref")
        missing = sum(1 for s in steps.values() if s.vi and not s.vi.description.strip())
        logger.info("TestStand reference: %d steps in %d groups, %d without a description; %d other VIs, %d types",
                    len(steps), len(GROUPS), missing, len(others), len(typedefs))


# -- The ts domain --------------------------------------------------------------------------------


class StepDirective(SphinxDirective):
    """Registers a step type documented on this page: ``{ts:step} <step type name>`` with ``:title:``."""

    required_arguments = 1
    final_argument_whitespace = True
    option_spec = {"title": directives.unchanged}

    def run(self) -> list[nodes.Node]:
        name = self.arguments[0].strip()
        title = self.options.get("title") or name
        anchor = "ts-" + _slugify(name)
        target = nodes.target("", "", ids=[anchor])
        self.state.document.note_explicit_target(target)
        index = addnodes.index(entries=[("single", f"{title} (TestStand step)", anchor, "", None)])
        self.env.get_domain("ts").note_step(name, title, self.env.docname, anchor)  # type: ignore[attr-defined]
        return [index, target]


class TestStandDomain(Domain):
    name = "ts"
    label = "TestStand"
    object_types = {"step": ObjType("step", "step")}
    directives = {"step": StepDirective}
    roles = {"step": XRefRole()}
    initial_data: dict[str, Any] = {"steps": {}}  # step type name -> (docname, anchor, title)

    def note_step(self, name: str, title: str, docname: str, anchor: str) -> None:
        self.data["steps"][name] = (docname, anchor, title)

    def clear_doc(self, docname: str) -> None:
        for name, (doc, _, _) in list(self.data["steps"].items()):
            if doc == docname:
                del self.data["steps"][name]

    def merge_domaindata(self, docnames: Any, otherdata: dict[str, Any]) -> None:
        for name, entry in otherdata["steps"].items():
            if entry[0] in docnames:
                self.data["steps"][name] = entry

    def _find(self, target: str) -> tuple[str, str, str] | None:
        steps = self.data["steps"]
        if target in steps:
            return steps[target]
        by_title = [e for e in steps.values() if e[2].casefold() == target.casefold()]
        return by_title[0] if len(by_title) == 1 else None

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder, typ: str, target: str,
                     node: addnodes.pending_xref, contnode: nodes.Element) -> nodes.reference | None:
        found = self._find(target)
        if found is None:
            logger.warning("no TestStand step named %r (use its menu name or step type name)", target, location=node)
            return None
        doc, anchor, title = found
        return make_refnode(builder, fromdocname, doc, anchor, contnode, title)

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder, target: str,
                         node: addnodes.pending_xref, contnode: nodes.Element) -> list[tuple[str, nodes.reference]]:
        found = self._find(target)
        if found is None:
            return []
        doc, anchor, title = found
        return [("ts:step", make_refnode(builder, fromdocname, doc, anchor, contnode, title))]

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        for name, (doc, anchor, title) in self.data["steps"].items():
            yield name, title, "step", doc, anchor, 1


def setup(app: Sphinx) -> dict[str, object]:
    here = Path(__file__).resolve().parent.parent
    app.add_config_value("teststand_export_dir", str(here / "lvdocs"), "env")
    app.add_config_value("teststand_repo_root", str(here.parent), "env")
    app.add_config_value(
        "teststand_palette", "teststand public directory/Components/TypePalettes/Nominal_Core_Stream_Types.ini", "env"
    )
    app.add_config_value("teststand_github_url", "https://github.com/nominal-io/ni-teststand-nominal-client", "env")
    app.add_domain(TestStandDomain)
    app.connect("builder-inited", lambda app: Pages(app).generate())
    return {"version": "0.1", "parallel_read_safe": True, "parallel_write_safe": True}
