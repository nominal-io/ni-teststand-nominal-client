# Report plugin

{.lead}
The report model plugin runs as a result processor. It scans each `Additional Result` for numeric values and streams every one to a channel named after the result, so the sequence itself stays untouched.

:::{warning}
The report model plugin is an alpha release and handles single-point numeric results only. Waveforms and other data types need the [test steps](steps.md).
:::

## Set up the plugin

Once installed, the plugin appears under **Configure > Result Processing**. Add **Nominal Core Result Streamer** with the **Insert New** button, then open its configuration and choose a mode:

| Mode | Behavior |
| --- | --- |
| `direct to dataset` | Streams every result to one dataset you have already bound to an asset in Nominal. |
| `stream to asset` | Takes an asset RID, finds or creates a dataset by name beneath it, and creates a run for each UUT. |
| `generate asset per test` | Creates an asset per UUT from a prefix plus the UUT serial number, each with its own dataset named `TestStand`, run, and stream. Without a serial number, the current time in seconds stands in for it. |

## Timestamps

Each value carries the timestamp of the step that produced it, which is imprecise for long-running steps. To supply your own instead, add a second result with the same name plus `_ts`, `_time`, or `_timestamp`. Its value can be:

- text in the format TestStand®'s `Date()` and `Time()` functions return, date or time first, such as `7/30/2026 12:07:19 PM`;
- seconds since the engine started, as `Seconds(True)` returns;
- seconds since 1970, as `Seconds(False)` returns;
- any other number, read as a LabVIEW® timestamp (seconds since 1904).

The [example sequence](examples/index.md#report-plugin) uses each format.
