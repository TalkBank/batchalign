"""Platform-specific compatibility for the supported Transformers 4 loader."""
import sys


def configure_windows_loading() -> None:
    """Read safetensors incrementally instead of reserving a full COW mapping.

    Windows charges copy-on-write mappings against RAM + pagefile immediately.
    Large NLLB checkpoints can crash in torch.storage before inference starts.
    Safetensors 0.8's pread backend avoids that reservation; Transformers 4
    does not expose the backend selection through from_pretrained.
    See https://github.com/huggingface/transformers/issues/48285.
    """
    if sys.platform != "win32":
        return
    from functools import partial
    from safetensors import safe_open
    from transformers import modeling_utils

    # Always wrap the original entrypoint, making repeated/concurrent calls
    # idempotent. This affects model loading in this process only.
    modeling_utils.safe_open = partial(safe_open, backend="pread")
