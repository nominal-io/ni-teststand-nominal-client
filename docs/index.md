% Ported from fern-docs 1dbaeb46 (fern/docs/pages/developers/documentation/connectors-and-sdks/teststand.mdx).

# NI TestStand

Publish results from your NI TestStand® sequences to Nominal. The TestStand® client offers two integration paths: ready-made test steps that wrap the Nominal LabVIEW® client, and a report model plugin that logs a sequence's `Additional Results` without changing the sequence itself.

Releases and source code are on [GitHub](https://github.com/nominal-io/ni-teststand-nominal-client).

```{toctree}
:hidden:
:caption: Guides

Overview <self>
steps
result-plugin
```

```{toctree}
:hidden:
:caption: Examples

examples/index
```

```{toctree}
:hidden:
:caption: Reference

ref/index
```

Pick the path that matches how much control you need:

- **[Test steps](steps.md)** put the calls in your sequence, so you choose what gets logged and when. They stream points and waveforms, create runs and events, and buffer readings between steps.
- **[Report model plugin](result-plugin.md)** runs as a result processor, scanning each `Additional Result` for numeric values and streaming every one to a channel named after the result. The sequence itself stays untouched.

## Requirements

- NI TestStand®
- The LabVIEW® 2020 Run-Time Engine

Building the steps and the plugin from source also needs LabVIEW® with the [Nominal client for LabVIEW](site:/ni/labview/).

## Connect to Nominal

Both paths authenticate with a Nominal API key; see [API keys setup](site:/quickstart/quickstart/api-keys-setup/). Each also needs somewhere to write, which can be a [dataset RID](site:/quickstart/quickstart/quick/quick-dataset-rid/), an asset RID, or neither if you let the integration create the asset for you. See [Creating asset metadata](site:/quickstart/quickstart/quick/quick-asset/).

The test steps read the API key from the station global `StationGlobals.nominal_api_key`. The report plugin uses the key in its **Nominal Core API Key** setting, or that station global when the setting is empty.

## Install

1. Download a release from [GitHub](https://github.com/nominal-io/ni-teststand-nominal-client), or clone the repository to get the example sequences alongside the source.
2. Copy the contents of `teststand public directory` into your TestStand® public directory. For TestStand® 2026 (64-bit) that is `C:\Users\Public\Documents\National Instruments\TestStand 2026 (64-bit)`. Check your product documentation if your installation differs.
3. Restart TestStand® so it picks up the new step types and the result processor.

## Trademarks

NI®, NI LabVIEW®, and NI TestStand® are registered trademarks of NI®. All other trademarks are the property of their respective owners.
