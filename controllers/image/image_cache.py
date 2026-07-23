from __future__ import annotations

import io
import threading
from collections import OrderedDict
from dataclasses import dataclass

from PIL import Image

from controllers.image.image_downloader import ImageDownloader
from controllers.image.image_errors import ImageDecodeError


@dataclass(frozen=True, slots=True)
class ImageCacheKey:
    """
    Identifies one cached image variant.
    """

    url: str
    width: int | None
    height: int | None


class ImageCache:
    """
    Downloads, decodes, resizes, and caches images.

    Cached images are stored using a least-recently-used eviction policy.
    """

    def __init__(
        self,
        downloader: ImageDownloader | None = None,
        *,
        max_entries: int = 64,
    ) -> None:
        if max_entries <= 0:
            raise ValueError(
                "max_entries must be greater than zero"
            )

        self._downloader = downloader or ImageDownloader()
        self._max_entries = max_entries

        self._images: OrderedDict[
            ImageCacheKey,
            Image.Image,
        ] = OrderedDict()

        self._lock = threading.RLock()

    @property
    def max_entries(self) -> int:
        """Return the maximum number of decoded images retained.

        @return Positive cache-entry limit.
        """
        return self._max_entries

    @property
    def entry_count(self) -> int:
        """Return the number of images currently cached.

        @return Current count of URL/dimension variants.
        """
        with self._lock:
            return len(self._images)

    def get(
        self,
        url: str,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> Image.Image:
        """Return an image from the cache or download it.

        When width or height is supplied, the image is resized while
        preserving its aspect ratio.

        A copy of the cached image is returned so callers cannot mutate the
        cached instance.

        @param url Non-empty HTTP or HTTPS image URL.
        @param width Optional positive bounding width in pixels.
        @param height Optional positive bounding height in pixels.
        @return Caller-owned copy of the decoded image.
        @raises ValueError if the URL or dimensions are invalid.
        @raises ImageDownloadError if downloading or decoding fails.
        """
        normalized_url = url.strip()

        if not normalized_url:
            raise ValueError("url cannot be empty")

        self._validate_dimensions(width, height)

        key = ImageCacheKey(
            url=normalized_url,
            width=width,
            height=height,
        )

        with self._lock:
            cached = self._images.get(key)

            if cached is not None:
                self._images.move_to_end(key)
                return cached.copy()

        image = self._download_and_decode(
            normalized_url,
            width=width,
            height=height,
        )

        with self._lock:
            existing = self._images.get(key)

            if existing is not None:
                self._images.move_to_end(key)
                return existing.copy()

            self._images[key] = image
            self._evict_if_needed()

            return image.copy()

    def contains(
        self,
        url: str,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> bool:
        """Return whether a matching decoded image is cached.

        @param url Image URL used as part of the cache key.
        @param width Optional bounding width used as part of the cache key.
        @param height Optional bounding height used as part of the cache key.
        @retval True An exact URL/dimension variant is cached.
        @retval False No exact variant is cached.
        """
        key = ImageCacheKey(
            url=url.strip(),
            width=width,
            height=height,
        )

        with self._lock:
            return key in self._images

    def remove(self, url: str) -> int:
        """Remove every cached image variant for a URL.

        @param url URL whose dimension variants should be removed.
        @return Number of removed cache entries.
        """
        normalized_url = url.strip()

        with self._lock:
            matching_keys = [
                key
                for key in self._images
                if key.url == normalized_url
            ]

            for key in matching_keys:
                image = self._images.pop(key)
                image.close()

            return len(matching_keys)

    def clear(self) -> None:
        """
        Remove all cached images.
        """
        with self._lock:
            for image in self._images.values():
                image.close()

            self._images.clear()

    def _download_and_decode(
        self,
        url: str,
        *,
        width: int | None,
        height: int | None,
    ) -> Image.Image:
        downloaded = self._downloader.download(url)

        try:
            with Image.open(
                io.BytesIO(downloaded.data)
            ) as source:
                source.load()

                image = source.convert("RGBA")

        except (OSError, ValueError) as exc:
            raise ImageDecodeError(
                f"Unable to decode image from {url}"
            ) from exc

        if width is not None or height is not None:
            target_width = (
                width if width is not None else image.width
            )
            target_height = (
                height if height is not None else image.height
            )

            image.thumbnail(
                (target_width, target_height),
                Image.Resampling.LANCZOS,
            )

        return image

    def _evict_if_needed(self) -> None:
        while len(self._images) > self._max_entries:
            _, image = self._images.popitem(
                last=False
            )
            image.close()

    @staticmethod
    def _validate_dimensions(
        width: int | None,
        height: int | None,
    ) -> None:
        if width is not None and width <= 0:
            raise ValueError(
                "width must be greater than zero"
            )

        if height is not None and height <= 0:
            raise ValueError(
                "height must be greater than zero"
            )
