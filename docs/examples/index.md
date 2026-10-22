# Examples

{.lead}
Example sequences for the [test steps](../steps.md) and the [report plugin](../result-plugin.md), saved with TestStand® 2026. Both call `example sequence single sample gen.vi` to generate data, so download it with either sequence and save them in the same folder.

## Test steps

{download}`example nominal core sequence.seq <../../example nominal core sequence.seq>` · {download}`example sequence single sample gen.vi <../../example sequence single sample gen.vi>`

The sequence logs a simulated sine wave on several channels. **Setup** connects to Nominal and opens a stream, **Cleanup** closes them again, and **Main** uses the other steps: a `For Each` loop generates points for each channel one at a time, adds every point to both a point buffer and a batch buffer, and flushes the buffers to Nominal. It also starts and stops a run, and creates an event on the third channel.

Before you run it, set your API key in `StationGlobals.nominal_api_key`, and set the sequence file's globals to a dataset or asset of yours:

- `dataset_rid`: the dataset to log to, while `useDatasetRid` is True;
- `asset_rid` and `dataset_name`: an asset, and the name of its dataset to find or create, while `useDatasetRid` is False.

## Report plugin

{download}`example nominal reporting sequence.seq <../../example nominal reporting sequence.seq>` · {download}`example sequence single sample gen.vi <../../example sequence single sample gen.vi>`

The sequence records generated points as `Additional Results`, which the [report plugin](../result-plugin.md) streams to a channel per result name. Alongside them it records a `_timestamp` result in each of the time formats the plugin accepts. Add and configure the plugin before you run it.
