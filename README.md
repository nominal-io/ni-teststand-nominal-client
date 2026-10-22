# NI TestStand® Integration for Nominal Core
Provides two integration options for using Nominal in NI TestStand®.

- **Test steps** which wrap the LabVIEW® Nominal client, making integration of test results from NI TestStand® into Nominal Core easier.
- **A report model plugin** which automatically logs `Additional Results` to Nominal Core.

The report model plugin is an alpha release and supports single-point numeric properties only. Other data types, such as waveforms, are straightforward to add but are not supported yet; use the test steps for those.

The full docs are at [nominal-io.github.io/pub-docs/ni/teststand](https://nominal-io.github.io/pub-docs/ni/teststand/).

## Requirements
The steps and model plugin depend on this VIPM package in order to build:
 - [Nominal.io Client](https://www.vipm.io/package/nominal_lib_nominal_io_client/)

## Install
Download a release from the sidebar or clone this repo and move the contents of the zip or the contents of the folder `teststand public directory` to the TestStand® public directory. For TestStand® 2026 (64-bit), this should be `C:\Users\Public\Documents\National Instruments\TestStand 2026 (64-bit)`. Refer to product documentation for any deviations from that path.

## Configuration
The steps and the model plugin both require an API key and an RID to operate. Both support dataset RIDs, binding to a specific asset by RID, or creation of assets and their associated RIDs.

### Nominal API Key
This key can be generated as described in the [nominal SDK documentation](https://docs.nominal.io/core/sdk/python-client/authentication#generating-an-api-key). Keep this key secret.

### Nominal RIDs
A dataset can be created by [first creating an asset](https://docs.nominal.io/core/documentation/platform/data/creating-an-asset#create-an-asset) and then by [creating and/or associating a dataset](https://docs.nominal.io/core/documentation/platform/data/creating-an-asset#add-a-data-source) with the asset. This value is an identifier, not a secret. Depending on your precise needs you can create an asset from the test steps, allow the model plugin to generate an asset for each UUT, or use a fixed asset or dataset to log to.


## Usage

### Test Steps
The test steps provided are a light wrapper around the LabVIEW® API for Nominal. The sequence `example nominal core sequence.seq` provides a sample entry point for how to use the code which consists of:
1. Connect to Nominal by API key
2. Locate a dataset by RID or find/create an asset and then associate a dataset with that asset
3. Create a stream to that dataset
4. Perform normal operations on the stream:
    * Log points or waveforms
    * Create events or runs
    * Use the point and batch buffers to buffer and then flush data to nominal
5. Close the stream
6. Close the connection to Nominal

#### Buffers
The steps contain two helper buffers:

- **Point buffer**: implemented by `Create Point Buffer`, `Add to Point Buffer`, `Flush Point Buffer to Channel`, and `Destroy Point Buffer`. This buffer stores a sequence of (time, value) points which can later be flushed to a specified channel. If you have a single instrument you are monitoring over the course of a test, this is easiest to use as it avoids array manipulation in TestStand®.
- **Batch buffer**: implemented by `Create Batch Buffer`, `Add Point to Batch Buffer`, `Flush Batch Buffer to Nominal`, and `Destroy Batch Buffer`. This buffer is a mapping of channel[str] to points[array of (time, value)] which can be flushed to Nominal automatically. If you have multiple long-lived instruments you are collecting data from, this provides a single-sample interface you can use to collect data rather than having to do array manipulation in TestStand®.

In both cases, the purpose is to provide a single-point interface for sequences with granular test steps. If your test steps already provide a waveform or array of (time, value) data points, you can use `Stream Points to Channel` [array of (time, value) points], `Stream Array to Channel` [array of times, array of values], or `Stream Waveform to Channel` [standard LabVIEW® waveforms with a T0, dt, and list of values].

#### Conventions for Ease of Use
The test steps are developed as basic LabVIEW® test steps -- they are more like pre-configured steps that you made yourself vs other published test steps which may provide an additional configuration dialog for configuring a hidden Action step. This means the usage is more flexible than other tools, but requires some effort to configure variables used by the steps and to route data as needed. To make this as easy as possible, the test steps are written with certain variable conventions in mind:

* The steps expect the API key to be stored as a station global: `StationGlobals.nominal_api_key` of type string
* The steps expect the Nominal connection reference to be stored as a Object Reference called `Locals.nominal`
* Similarly, runs are stored as Object References called `Locals.run`, assets as `Locals.asset`, datasets as `Locals.dataset`, channels as `Locals.channel`, and events as `Locals.event`, with the assumption that any bulk operations may be performed on a For Loop where the loop variable is stored as one of those locals.
* Streams and buffers expect to be stored as `Locals.stream`, `Locals.buffer`, or `Locals.pointbuffer`; since these are Data Value References (DVRs) the correct data type is "Number" (while it feels strange to associate a pointer to a floating point number, TestStand handles this case gracefully)

The Variables section of the example sequence can be seen here:
<img width="817" height="384" alt="image" src="https://github.com/user-attachments/assets/058f9f99-a6b3-490a-86db-61a410fb316e" />

#### Example
The sequence `example nominal core sequence.seq` is the easiest way to get a feel for how the test steps can be used. The `setup` section demonstrates construction of a connection and stream, `Cleanup` shows the reverse, and `Main` shows several common functions using a point-by-point sine wave generation function. The central `For Each` simulates 4 channels generating data and storing that data in both a batch buffer (flushed at the end of the `For Each`) and a point buffer (flushed at the end of each iteration of the `For Each`, once for each "channel"). It also demonstrates the usage of `Run`-related steps and the creation of a single `Event` on the 3rd iteration of the `For Each`.

<img width="912" height="699" alt="image" src="https://github.com/user-attachments/assets/7b2011ee-fd32-41bc-b4d2-1fb9efc3cbe7" />


### Report Model Plugin
The report plugin accepts single point values as additional results. The theory of operation is to look through every `Additional Result` value, identify numerics, and push those to Nominal using the user-specified result name as the channel name. That is, you can specify an Additional Result as having the name "station_psu_voltage" anywhere from 1 to N times through the run of your test sequence and every value will be stored in the same channel in Nominal.

#### Accurate TimeStamps
By default, the timestamp used is the timestamp of the step itself. Since this is imprecise (especially for longer-running steps), you can override this by producing a second result with any of the following suffixes: `_ts`, `_time`, or `_timestamp`. That is, station_psu_voltage_ts or station_psu_voltage_time or station_psu_voltage_timestamp, stored in the same `Additional Results` record, will be used if present. The timestamp format can be either numeric or string:
* If string, it expects the standard format used by TestStand® for timestamps and returned by the `Date()` and `Time()` functions but will permit either date-first or time-first so both "12:07:19 PM 7/30/2026" and "7/30/2026 12:07:19 PM" will work fine
* If numeric, the matching is more complex due to how TestStand® handles time:
  * Test step timestamps are recorded using the built-in function `Seconds(True)` which returns `Engine.SecondsSinceStart` -- this is the current time minus the time the engine started. If a numeric value with one of the timestamp suffixes has a value between 0 (seconds since the start of the engine) and the current value of `Engine.SecondsSinceStart`, the report generation will assume the timestamp is in this format. To convert, the code will sum the value with `Engine.SecondsAtStartIn1970UniversalCoordinatedTime` and then convert between the 1970 epoch and the LabVIEW® 1904 epoch to determine the correct time in the native LabVIEW® data format.
  * The code next attempts to fix the timestamp within the TestStand®-native epoch. If the time value stored is between `Engine.SecondsAtStartIn1970UniversalCoordinatedTime` and `Seconds(False)` [the absolute number of seconds that have elapsed between the 1970 epoch and the current time], the code will assume that the time value stored is in the 1970 epoch and will directly convert to the 1904 epoch used by LabVIEW®.
  * If both of the above range checks fail, the code assumes the time value is already in the native LabVIEW® format (since Today-1904 >>> Today-1970) and will simply use the primitive `[Number] To Time Stamp`.
If you have a native LabVIEW® time stamp when you acquire your data and need precision, the best approach is to use the native timestamp<>string functionality.

#### Configuration
Once installed to the TestStand® public directory and the application is reloaded, the plugin should appear as a normal result plugin under Configure >> Result Processing...

<img width="303" height="348" alt="image" src="https://github.com/user-attachments/assets/04a58195-1a9c-4da6-b213-7e038eff85f8" />

Press the `>` (Insert New) button and add the Nominal Core Result Streamer:

<img width="511" height="224" alt="image" src="https://github.com/user-attachments/assets/6ba50b09-b787-4145-9684-07e7b12cef49" />

Finally, hit the configuration gear to configure the addon. All three modes require an API key, but the additional data required depends on the Mode:

<img width="904" height="687" alt="image" src="https://github.com/user-attachments/assets/6f3721a7-3f0a-4a72-9475-524b432715c5" />

The dialog should provide a description of the behavior which is replicated here:
* `direct to dataset` - "All results are streamed directly to a dataset which you have pre-configured within Nominal Core to be bound to an asset or set of assets"
* `stream to asset` - "Uses an asset RID to find an asset in Nominal. If a dataset *name* is specified, it will be used; otherwise, the asset RID will be reused as the *name* of the dataset. The model steps will automatically locate or create that dataset by *name* and then associate a stream with it. The code will also generate a Run object for the asset for every "UUT" tested in TestStand®."
* `generate asset per test` - "Creates an asset for each UUT by concatenating the prefix specified here with the UUT serial number. Then a dataset called "TestStand" will be generated and a run will be generated on the new asset. Each UUT will have its own asset, dataset, and stream."

#### Example
The below example images show a valid usage of the report generation functionality. First, in a step that is operating on several values:
<img width="2234" height="433" alt="image" src="https://github.com/user-attachments/assets/7d40d166-f621-45a8-bdc7-647d65ff0996" />
Note in this example each of the timestamp suffixes is used and each of the three main time formats are used. The offsets hardcoded in the image above are purely for verification purposes, to ensure the times are being handled as expected.

Later, the sequence stores another set of additional results. By using different names, they are stored in different channels:
<img width="1136" height="476" alt="image" src="https://github.com/user-attachments/assets/98382a40-0d61-4075-a15f-8f5058186e9b" />
For this result, the timestamp used will be the native step timestamp.

To store those results under the original channel names, the result names would need to match as shown here:
<img width="1086" height="405" alt="image" src="https://github.com/user-attachments/assets/73966a93-d269-4ddd-b929-f0844b125cdd" />

The different approaches can be seen in `example nominal reporting sequence.seq` in this repository. If you have configured the plugin appropriately you should see:
<img width="2193" height="1161" alt="image" src="https://github.com/user-attachments/assets/5707f403-2afe-4797-bad5-e58896d33a5a" />
Note that the third waveform is expected due to the low time resolution used on that segment's time source

## Building from source

The steps and model plugin depend on the [Nominal.io Client](https://www.vipm.io/package/nominal_lib_nominal_io_client/) VIPM package in order to build.


------

NI® (National Instruments®), NI TestStand®, and NI LabVIEW® are registered trademarks of NI®. All other trademarks are the property of their respective owners.
