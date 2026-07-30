# ni-teststand-nominal-client
Provides two integration options for using Nominal in NI TestStand®:

 * Test steps which wrap the LabVIEW® nominal client, making integration of test results from NI TestStand® into nominal core easier.
 * A report model plugin which allows users to automatically log `Additional Results` to Nominal Core.

## Dependencies
The steps and model plugin depend on this VIPM package in order to build:
 - [Nominal.io Client](https://www.vipm.io/package/nominal_lib_nominal_io_client/)

## Shared Configuration Requirements
The steps and model plugin require an API key and an RID to operate. 

Both the steps and the model plugin support database RIDs, being bound to specific assets by RID, or creation of assets and associated RIDs.

### Nominal API Key
This key can be generated as described in the [nominal SDK documentation](https://docs.nominal.io/core/sdk/python-client/authentication#generating-an-api-key). Keep this key secret.

### Nominal RIDs
A dataset can be created by [first creating an asset](https://docs.nominal.io/core/documentation/platform/data/creating-an-asset#create-an-asset) and then by [creating and/or associating a dataset](https://docs.nominal.io/core/documentation/platform/data/creating-an-asset#add-a-data-source) with the asset. This key is just an identifier, not a secret. Depending on your precise needs you can create an asset from the test steps, allow the model plugin to generate an asset for each UUT, or use a fixed asset or dataset to log to.


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
* Point buffer: implemented by `Create Point Buffer`, `Add to Point Buffer`, `Flush Point Buffer to Channel`, and `Destroy Point Buffer`, this buffer is simply a way to store a sequence of (time, value) points which can later be flushed to a specified channel. If you have a single instrument you are monitoring over the course of a test, this is easiest to use as it avoids array manipulation in TestStand. If you have multiple instruments, it is simpler to use the batch buffer because the name of the channel is stored in that buffer and so multiple buffers do not need to be managed.
* Batch buffer: implemented by `Create Batch Buffer`, `Add Point to Batch Buffer`, `Flush Batch Buffer to Nominal`, and `Destroy Batch Buffer`, this buffer is a sequence of channel[str] to points[array of (time, value)] which can be flushed to Nominal automatically. If you have multiple long-lived instruments you are collecting data from, this provides a single-sample interface you can use to collect data rather than having to do array manipulation in TestStand.

In both cases, the purpose is to help provide a single-point interface for sequences with granular test steps. If your test steps already provide a waveform or array of (time, value) data points, you can simply use `Stream Points to Channel` [array of (time, value) points], `Stream Array to Channel` [array of times, array of values], or `Stream Waveform to Channel` [standard LabVIEW® waveforms with a T0, dt, and list of values].

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





NI® (National Instruments®), NI TestStand®, and NI LabVIEW® are registered trademarks of NI®. All other trademarks are the property of their respective owners.
