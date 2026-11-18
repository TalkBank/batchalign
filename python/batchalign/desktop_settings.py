"""Local desktop credentials. Responses never include secret values."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, SecretStr
import os

from batchalign import config

router = APIRouter()


def _local_only() -> None:
    from batchalign import api
    if not api._allow_paths():
        raise HTTPException(403, "desktop settings require local filesystem access")


class RevKey(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: SecretStr


@router.get("/desktop/settings/revai")
def rev_status() -> dict[str, bool]:
    _local_only()
    return {"configured": bool(config.get_api_key("revai", path=config.CONFIG_PATH)),
            "from_environment": bool(os.environ.get("BATCHALIGN_REVAI_KEY"))}


@router.put("/desktop/settings/revai")
def save_rev_key(request: RevKey) -> dict[str, bool]:
    _local_only()
    if os.environ.get("BATCHALIGN_REVAI_KEY"):
        raise HTTPException(409, "Rev.AI key is supplied by BATCHALIGN_REVAI_KEY. "
                            "Remove that environment variable to manage it in Settings.")
    key = request.key.get_secret_value().strip()
    if not key or any(character.isspace() for character in key):
        raise HTTPException(400, "Enter a nonempty Rev.AI key without whitespace.")
    try:
        config._persist(config.CONFIG_PATH, "asr", "engine.rev.key", key)
    except Exception:
        # Config-parser exceptions may contain existing credentials.
        raise HTTPException(500, "Could not save credentials. Check that ~/.batchalign.ini "
                            "is valid and writable.") from None
    return rev_status()
