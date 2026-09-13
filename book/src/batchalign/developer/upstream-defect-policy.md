# Handle a model-library defect

1. Reduce the failure to a small reproducible input and record library/model
   versions and configuration.
2. Determine whether the error originates in the model, a vendor adapter,
   token reconciliation, or CHAT result application.
3. Add a regression at that boundary. Test a nearby valid case so a workaround
   does not merely suppress a class of outputs.
4. Implement a narrowly scoped correction where the required information is
   available. Stanza token processing/rendering lives in the Python backend;
   typed CHAT injection lives in the Rust morphology runner.
5. Re-run the affected command on representative inputs and compare semantic
   output. Record known limits rather than claiming a universal linguistic fix.
6. If behavior affects cached outputs, update backend identity as appropriate;
   compiled build identity also participates in result-cache keys.

Historical model probes are useful evidence, but rerun a relevant case against
the current pinned environment before treating an old mitigation table as active.
