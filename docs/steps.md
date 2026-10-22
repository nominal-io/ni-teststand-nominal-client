# Test steps

{.lead}
The test steps put the calls to Nominal in your sequence, so you choose what gets logged and when. They need your API key in `StationGlobals.nominal_api_key`; see [Connect to Nominal](index.md#connect-to-nominal).

The steps follow the lifecycle of the LabVIEW® client: connect with your API key, locate a dataset by RID or find an asset and associate a dataset with it, open a stream, log against that stream, then close the stream and the connection.

For logging, {ts:step}`Stream Points to Channel`, {ts:step}`Stream Array to Channel`, and {ts:step}`Stream Waveform to Channel` cover data your sequence already holds as an array or a waveform. When a sequence produces one reading at a time, the point buffer and batch buffer collect values and flush them in a single call, which keeps array manipulation out of TestStand®. The batch buffer stores a channel name per series, so it suits several instruments at once, while the point buffer is the simpler choice for a single one.

The [example sequence](examples/index.md#test-steps) shows the whole arrangement end to end. The [Reference](ref/index.md) lists every step and its parameters.

## Variables the steps expect

Each step's parameters default to these variables, so a sequence that declares them can use the steps without changing their parameters.

| Variable | Type | Holds |
| --- | --- | --- |
| `StationGlobals.nominal_api_key` | String | Your API key |
| `Locals.nominal` | Object Reference | The connection to Nominal |
| `Locals.asset`, `Locals.dataset`, `Locals.channel`, `Locals.run`, `Locals.event` | Object Reference | The asset, dataset, channel, run or event a step finds or creates |
| `Locals.stream` | Number | The stream |
| `Locals.pointbuffer`, `Locals.buffer` | Number | The point buffer and the batch buffer |
