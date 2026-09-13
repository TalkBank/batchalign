# Coreference API

The Python API defines a `Coref` backend interface and a
`ba.recipes.coref(coref_backend=...)` recipe. This build does not bundle a concrete
coreference backend. The stub under `cli/hidden/` is not registered as a public
command.

An integration must supply its own implementation of the interface in
`python/batchalign/backends/base.py`. See [Add an inference backend](../../developer/adding-engines.md)
and [Python API](../python-api.md).
