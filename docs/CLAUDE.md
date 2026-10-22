# docs/

These pages build here and are published on the Nominal docs hub (nominal-io/pub-docs) at
`/ni/teststand/`. The repo's CLAUDE.md brings in the hub's writing rules, and those apply
here in full. This file adds what is specific to the pages.

## Where the facts come from

Quote labels and messages exactly as the source has them, labels in bold.

- The steps: the type palette,
  `teststand public directory/Components/TypePalettes/Nominal_Core_Stream_Types.ini`, has each step
  type's menu name, default step name, the VI it calls and its default variables. The VIs are in
  `teststand steps support/`.
- The result plugin: `teststand public directory/Components/Models/ModelPlugins/Nominal_Core_Result_Streamer.seq`
  and the VIs in `teststand model seq support/`, including its configuration dialog
  (`nominal teststand model options dialog.vi`) and its timestamp handling.
- Worked examples: `example nominal core sequence.seq` and `example nominal reporting sequence.seq`.
- README.md, which must agree with these pages.

The palette is saved as XML (Station Options > File > File Format Options), which
`_ext/teststand.py` reads; it also reads the older binary format. The .seq files are binary: a
`TOF1` header, then `PMCZ` and 4 bytes, then a zlib stream whose strings can be read without
TestStand. Don't open or save .seq, .ini or .vi files in TestStand or LabVIEW to check a
fact; ask your human.

## The reference

`ref/index.md` is generated at build time from the LabVIEW export in `lvdocs/` and the palette, and
is gitignored. To change what a step's entry says, change the VI's description (VI Properties >
Documentation) or its inputs' and outputs' descriptions, then re-export with the tool in
`lvdocs/`. The palette has no submenus, so the groups are `GROUPS` in `_ext/teststand.py`. The
build fails when a step isn't in `GROUPS` or its VI isn't in the export. VIs that no step calls,
such as typedefs, are left out.

## Examples

`examples/index.md` is written by hand. Its `{download}` links point at the example files in the
repo root, and the build copies them into the site, so the hub serves them. What the page says each
example does and which globals to set comes from the sequences themselves, so check it when they
change.

## Rules for these pages

- Readers know TestStand and LabVIEW. Explain only what is Nominal's.
- State only what the source shows or what has been run. TestStand's own behavior, such as its
  menu labels, needs a check in TestStand before a page relies on it.
- Link a step by name with {ts:step}`Create Point Buffer` (its menu name or step type name).
- Link to other projects on the hub as `[text](site:/{lang}/{project}/{page}/)`, never with an
  absolute URL, so the hub's offline copy works.
- The guide marks NI's trademarks with ® and ends with a Trademarks section. Keep both.

## Building

`just build-docs` builds into `docs/_build/dirhtml`, with warnings failing the build as in CI.
Run it before calling a change done. `just serve-docs` serves a live preview on
http://127.0.0.1:8000.

`.github/workflows/docs-check.yml` builds every pull request. `deploy-docs.yml` deploys every
push to `main` to this repo's GitHub Pages, and pub-docs pulls that deploy.
