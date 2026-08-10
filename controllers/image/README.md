# Image Controller

The `image` controller provides reusable image downloading, decoding, resizing, and caching services.

The goal of this component is to allow higher-level applications to display images without needing to manage HTTP requests, image decoding, or caching logic.

## Components

| Component | Description |
|-----------|-------------|
| `ImageDownloader` | Downloads image data from HTTP or HTTPS URLs. |
| `ImageCache` | Downloads, decodes, resizes, caches, and returns Pillow images. |
| `image_errors.py` | Image-specific exception classes. |

## Directory Layout

```text
image/
├── __init__.py
├── image_cache.py
├── image_downloader.py
├── image_errors.py
├── README.md
└── component_test/
    ├── __init__.py
    └── image_cache_cli.py
```

## Features

The image controller provides:

- HTTP/HTTPS image downloading
- Image validation
- Pillow image decoding
- Automatic resizing while preserving aspect ratio
- In-memory image caching
- Least Recently Used (LRU) cache eviction
- Thread-safe cache access
- Atomic persistent source storage through `controllers.cache`

## Dependencies

This component requires Pillow.

Install using:

```bash
python3 -m pip install Pillow
```

## Image Downloader

`ImageDownloader` downloads raw image data.

Features include:

- HTTP and HTTPS support
- Download timeout
- Maximum image size limits
- Content-Type validation
- Custom User-Agent support

Example:

```python
from controllers.image import ImageDownloader

downloader = ImageDownloader()

downloaded = downloader.download(url)

print(downloaded.size_bytes)
```

## Image Cache

`ImageCache` manages downloading, decoding, resizing, and caching.

Images are automatically cached using an LRU eviction policy.

Example:

```python
from controllers.image import ImageCache

cache = ImageCache()

image = cache.get(
    url,
    width=256,
    height=256,
)
```

Repeated requests for the same URL and size return the cached image.

## Returned Images

`ImageCache.get()` returns a Pillow `Image.Image` object.

The caller may:

- Display the image
- Save it to disk
- Convert it to another format
- Convert it into a GUI-specific image type

The image controller does not depend on any GUI framework.

## Exceptions

The image controller may raise:

- `ImageError`
- `ImageDownloadError`
- `ImageDecodeError`

These exceptions indicate failures while downloading or decoding images.

## Component Test

A CLI component test is provided.

Run from the project root:

```bash
python3 -m controllers.image.component_test.image_cache_cli \
    "<image-url>"
```

Example:

```bash
python3 -m controllers.image.component_test.image_cache_cli \
    "https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg"
```

The component test demonstrates:

- Image downloading
- Image decoding
- Image resizing
- Cache reuse
- Viewing the downloaded image
- ASCII art rendering

## Design

This controller is intentionally independent of any specific application or user interface.

Responsibilities include:

- Downloading images
- Decoding images
- Resizing images
- Caching images

Responsibilities that belong outside this component include:

- GUI rendering
- Image widgets
- User interface layout
- Application-specific image selection
- Album artwork logic
- Weather icon selection
- Map tile management

Keeping these responsibilities separate allows the image controller to be reused by any higher-level component requiring image support.

Persistent filesystem mechanics are delegated to `PersistentCache` rather
than generalized inside the image package. Image decoding, resizing, and
decoded-image LRU policy remain image-specific.
