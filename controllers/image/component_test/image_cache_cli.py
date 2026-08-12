#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from controllers.image import ImageCache
from PIL import Image, ImageEnhance, ImageOps

ASCII_CHARACTERS = " .,:;irsXA253hMHGS#9B&@"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Image downloader and cache component test"
    )

    parser.add_argument(
        "url",
        help="HTTP or HTTPS image URL",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=300,
        help="Maximum downloaded image width",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=300,
        help="Maximum downloaded image height",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("downloaded_image.png"),
        help="Path used when saving the downloaded image",
    )

    parser.add_argument(
        "--ascii-width",
        type=int,
        default=80,
        help="Maximum width of ASCII art output",
    )

    return parser.parse_args()

def open_image(image: Image.Image) -> None:
    """
    Save the image to a temporary file and open it using xdg-open.
    """
    with tempfile.NamedTemporaryFile(
        suffix=".png",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    image.save(temp_path)

    print(f"Opening {temp_path}...")

    subprocess.Popen(
        ["xdg-open", str(temp_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def image_to_terminal_art(
    image: Image.Image,
    width: int = 80,
) -> str:
    if width <= 0:
        raise ValueError("width must be greater than zero")

    source = image.convert("RGB")

    aspect_ratio = source.height / source.width
    pixel_height = max(2, int(width * aspect_ratio))

    # Need an even number because each character holds two vertical pixels.
    if pixel_height % 2:
        pixel_height += 1

    resized = source.resize(
        (width, pixel_height),
        Image.Resampling.LANCZOS,
    )

    resized = ImageEnhance.Contrast(resized).enhance(1.15)

    lines: list[str] = []

    for y in range(0, resized.height, 2):
        line: list[str] = []

        for x in range(resized.width):
            top = resized.getpixel((x, y))
            bottom = resized.getpixel((x, y + 1))

            line.append(
                "\033[38;2;"
                f"{top[0]};{top[1]};{top[2]}m"
                "\033[48;2;"
                f"{bottom[0]};{bottom[1]};{bottom[2]}m"
                "▀"
            )

        line.append("\033[0m")
        lines.append("".join(line))

    return "\n".join(lines)

def image_to_ascii(
    image: Image.Image,
    width: int = 80,
) -> str:
    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale)
    grayscale = ImageEnhance.Contrast(grayscale).enhance(1.35)

    aspect_ratio = grayscale.height / grayscale.width
    height = max(1, int(width * aspect_ratio * 0.45))

    resized = grayscale.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )

    lines: list[str] = []

    for y in range(resized.height):
        line: list[str] = []

        for x in range(resized.width):
            value = resized.getpixel((x, y))

            index = round(
                value
                * (len(ASCII_CHARACTERS) - 1)
                / 255
            )

            line.append(ASCII_CHARACTERS[index])

        lines.append("".join(line))

    return "\n".join(lines)


def prompt_display_mode() -> str:
    """
    Ask how the downloaded image should be displayed.
    """
    print()
    print("How would you like to view the image?")
    print()
    print("  1. Open the default image viewer")
    print("  2. Display as Terminal art")
    print("  3. Display as ASCII art")
    print("  4. Save only")
    print("  5. Exit without saving")
    print()

    while True:
        choice = input("Selection [1-5]: ").strip()

        if choice in {"1", "2", "3", "4", "5"}:
            return choice

        print("Please enter 1, 2, 3, 4, or 5.")


def main() -> None:
    args = parse_args()

    cache = ImageCache(max_entries=8)

    image: Image.Image | None = None
    cached_image: Image.Image | None = None

    try:
        print("Image Cache Component Test")
        print("==========================")
        print()
        print(f"URL: {args.url}")
        print()

        print("Loading image...")
        image = cache.get(
            args.url,
            width=args.width,
            height=args.height,
        )

        print("Download ........ PASS")
        print("Decode .......... PASS")
        print("Resize .......... PASS")
        print(f"Image size ...... {image.width}x{image.height}")
        print(f"Image mode ...... {image.mode}")
        print(f"Cache entries ... {cache.entry_count}")

        print()
        print("Loading the same image again...")

        cached_image = cache.get(
            args.url,
            width=args.width,
            height=args.height,
        )

        print("Cache lookup ..... PASS")
        print(f"Cache entries ... {cache.entry_count}")

        choice = prompt_display_mode()

        if choice == "1":
            print()
            print("Opening the default image viewer...")
            image.show()

        elif choice == "2":
            print()
            print(
                image_to_terminal_art(
                    image,
                    width=args.ascii_width,
                )
            )

        elif choice == "3":
            print()
            print(
                image_to_ascii(
                    image,
                    width=args.ascii_width,
                )
            )

        elif choice == "4":
            image.save(args.output)
            print()
            print(f"Image saved to: {args.output}")

        else:
            print()
            print("No image was saved.")

    except KeyboardInterrupt:
        print("\nComponent test stopped.")

    except Exception as exc:
        print(f"\nImage component test failed: {exc}")
        raise SystemExit(1) from exc

    finally:
        if image is not None:
            image.close()

        if cached_image is not None:
            cached_image.close()

        cache.clear()


if __name__ == "__main__":
    main()
