"""Audio blob storage backed by Supabase Storage.

Scope: object-level operations (upload, download, signed URL, existence,
deletion) on a single bucket. Bucket provisioning, content validation and
Postgres metadata are explicitly out of scope — see ADR-003.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client


class AudioRepositoryError(RuntimeError):
    """Raised when a Supabase Storage operation fails."""


_DEFAULT_BUCKET = "audio"
_DEFAULT_SIGNED_URL_TTL = 3600
_SIGNED_URL_KEYS = ("signedURL", "signed_url", "signedUrl")


class AudioRepository:
    """Read/write audio blobs in a Supabase Storage bucket.

    The repository receives an already-constructed ``Client`` (see
    :func:`radio_transforma.storage.supabase_client.get_supabase_client`)
    and never instantiates it — this keeps the class trivially mockable
    and free of configuration concerns.
    """

    def __init__(self, client: Client, bucket: str = _DEFAULT_BUCKET) -> None:
        if not isinstance(bucket, str) or not bucket.strip():
            raise ValueError("bucket must be a non-empty string")
        self._client = client
        self._bucket = bucket

    @property
    def bucket(self) -> str:
        return self._bucket

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def upload(self, path: str, data: bytes, *, content_type: str) -> str:
        """Upload ``data`` to ``path`` and return the stored path.

        Fails if the object already exists (``upsert=false``).
        """
        self._validate_path(path)
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes")
        if not isinstance(content_type, str) or not content_type.strip():
            raise ValueError("content_type must be a non-empty string")

        try:
            self._storage().upload(
                path,
                bytes(data),
                file_options={
                    "content-type": content_type,
                    "upsert": "false",
                },
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as domain error
            raise AudioRepositoryError(f"upload failed for {path!r}: {exc}") from exc
        return path

    def download(self, path: str) -> bytes:
        """Return the raw bytes stored at ``path``."""
        self._validate_path(path)
        try:
            payload = self._storage().download(path)
        except Exception as exc:  # noqa: BLE001
            raise AudioRepositoryError(f"download failed for {path!r}: {exc}") from exc

        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, bytearray):
            return bytes(payload)
        raise AudioRepositoryError(f"unexpected download payload type: {type(payload).__name__}")

    def create_signed_url(
        self,
        path: str,
        *,
        expires_in: int = _DEFAULT_SIGNED_URL_TTL,
    ) -> str:
        """Return a time-limited signed URL for ``path``."""
        self._validate_path(path)
        if not isinstance(expires_in, int) or expires_in <= 0:
            raise ValueError("expires_in must be a positive integer")

        try:
            response = self._storage().create_signed_url(path, expires_in)
        except Exception as exc:  # noqa: BLE001
            raise AudioRepositoryError(f"create_signed_url failed for {path!r}: {exc}") from exc

        url = self._extract_signed_url(response)
        if not url:
            raise AudioRepositoryError(f"signed URL missing in response for {path!r}: {response!r}")
        return url

    def exists(self, path: str) -> bool:
        """Return ``True`` iff an object exists at ``path``."""
        self._validate_path(path)
        parent, _, name = path.rpartition("/")

        try:
            entries = self._storage().list(parent) or []
        except Exception as exc:  # noqa: BLE001
            raise AudioRepositoryError(f"exists failed for {path!r}: {exc}") from exc

        return any(isinstance(entry, dict) and entry.get("name") == name for entry in entries)

    def delete(self, path: str) -> None:
        """Delete the object at ``path``. No-op if it does not exist."""
        self._validate_path(path)
        try:
            self._storage().remove([path])
        except Exception as exc:  # noqa: BLE001
            raise AudioRepositoryError(f"delete failed for {path!r}: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _storage(self) -> Any:
        return self._client.storage.from_(self._bucket)

    @staticmethod
    def _validate_path(path: str) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty string")
        if path.startswith("/"):
            raise ValueError("path must be relative (no leading slash)")
        if ".." in path.split("/"):
            raise ValueError("path must not contain '..' segments")

    @staticmethod
    def _extract_signed_url(response: Any) -> str | None:
        if isinstance(response, dict):
            for key in _SIGNED_URL_KEYS:
                value = response.get(key)
                if isinstance(value, str) and value:
                    return value
            return None
        for attr in _SIGNED_URL_KEYS:
            value = getattr(response, attr, None)
            if isinstance(value, str) and value:
                return value
        return None
