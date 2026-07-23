from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass

from controllers.image.image_errors import ImageDownloadError


@dataclass(frozen=True, slots=True)
class DownloadedImage:
    """
    Raw image data returned by an image download.
    """

    url: str
    data: bytes
    content_type: str | None = None

    @property
    def size_bytes(self) -> int:
        """Return the downloaded payload size.

        @return Length of `data` in bytes.
        """
        return len(self.data)


class ImageDownloader:
    """
    Downloads image data over HTTP or HTTPS.
    """

    DEFAULT_USER_AGENT = "PythonImageDownloader/1.0"

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_size_bytes: int = 10 * 1024 * 1024,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        if max_size_bytes <= 0:
            raise ValueError(
                "max_size_bytes must be greater than zero"
            )

        if not user_agent:
            raise ValueError("user_agent cannot be empty")

        self._timeout_seconds = timeout_seconds
        self._max_size_bytes = max_size_bytes
        self._user_agent = user_agent

    def download(self, url: str) -> DownloadedImage:
        """Download raw image data from a URL.

        @param url Non-empty HTTP or HTTPS URL.
        @return Final response URL, raw bytes, and reported content type.
        @raises ValueError if the URL is empty or uses another scheme.
        @raises ImageDownloadError if the request fails, the response is not
            an image, or the payload exceeds the configured size limit.
        """
        normalized_url = url.strip()

        if not normalized_url:
            raise ValueError("url cannot be empty")

        if not normalized_url.startswith(("http://", "https://")):
            raise ValueError(
                "url must use HTTP or HTTPS"
            )

        request = urllib.request.Request(
            normalized_url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "image/*",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                content_type = response.headers.get_content_type()
                content_length = response.headers.get(
                    "Content-Length"
                )

                if content_length is not None:
                    try:
                        expected_size = int(content_length)
                    except ValueError:
                        expected_size = 0

                    if expected_size > self._max_size_bytes:
                        raise ImageDownloadError(
                            "Image exceeds maximum allowed size: "
                            f"{expected_size} bytes"
                        )

                data = response.read(
                    self._max_size_bytes + 1
                )

        except urllib.error.HTTPError as exc:
            raise ImageDownloadError(
                f"Image download returned HTTP {exc.code}: "
                f"{normalized_url}"
            ) from exc

        except urllib.error.URLError as exc:
            raise ImageDownloadError(
                f"Unable to download image: {exc}"
            ) from exc

        except OSError as exc:
            raise ImageDownloadError(
                f"Image download failed: {exc}"
            ) from exc

        if len(data) > self._max_size_bytes:
            raise ImageDownloadError(
                "Image exceeds maximum allowed size: "
                f"{self._max_size_bytes} bytes"
            )

        if not data:
            raise ImageDownloadError(
                "Image download returned no data"
            )

        if (
            content_type is not None
            and not content_type.startswith("image/")
        ):
            raise ImageDownloadError(
                f"URL did not return an image: {content_type}"
            )

        return DownloadedImage(
            url=normalized_url,
            data=data,
            content_type=content_type,
        )
