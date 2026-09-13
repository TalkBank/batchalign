# Add a processing command

1. Identify the input/output types and task sequence. Reuse a recipe in
   `python/batchalign/recipes.py` or add one that constructs `Pipeline`.
2. Implement a command module under `python/batchalign/cli/`. Use `resolve_inputs`
   for multiple paths and file lists, and `cli_options(ctx)` for global settings.
3. Pass `opts.parallel` as the recipe's `workers` value. Use `Interface` for
   progress and the shared output helpers for outcomes where their contract fits.
4. Register the module in `_LAZY_SUBCOMMANDS` in `cli/__init__.py`. A file under
   `cli/hidden/` is not automatically a public command.
5. Test help, argument validation, output destinations, and failures. Exercise a
   real invocation through `just batchalign cli`.
6. Add a task-focused how-to page and update the [CLI reference](../user-guide/cli-reference.md).

`morphotag.py` demonstrates staged CHAT preprocessing; `convert.py` demonstrates
output collision checks. Use the example that matches the new command's behavior.
See [Pipeline architecture](../architecture/command-lifecycles.md) for the runtime.
