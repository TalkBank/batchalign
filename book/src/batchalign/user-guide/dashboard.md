# Monitor a batch

For command-line processing, use the terminal progress display and final summary.
See [Read processing progress](progress-and-feedback.md).

The [desktop application](desktop-app.md) has its own batch view backed by the
Python HTTP service. Ordinary CLI commands do not open a browser dashboard, and
the current service does not provide the retired Rust server's `/dashboard` UI.
For API clients, job status and events are available through the service's
[documented API](server-setup.md).
