# Measure a processing run

The current CLI does not register `bench` or `benchmark`. For throughput, time
an ordinary processing command on representative inputs and record peak RSS,
input counts, backend settings, and cache state. See
[Performance](../performance.md#measure-your-workload).

To assess transcription accuracy, first [transcribe](transcribe.md), then
[compare against checked reference transcripts](compare.md).
