# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Desktop OpenGL prototype for the native ORC spectrum and waterfall.

Requires pygame and PyOpenGL; intentionally separate from SDR/DSP contracts.
Uses a compatibility-profile context. EGL/GLES integration is a later milestone.
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from controllers.radio.spectrum.spectrum_analyzer import SpectrumAnalyzer
from controllers.radio.spectrum.spectrum_display_processor import SpectrumDisplayProcessor
from hardware_io.sdr import RtlSdrSource


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_100_000)
    parser.add_argument("--sample-rate", type=int, default=2_400_000)
    parser.add_argument("--fft-size", type=int, default=2048)
    parser.add_argument("--gain", type=float)
    parser.add_argument("--smoothing", type=float, default=0.2)
    parser.add_argument("--waterfall-rows", type=int, default=256)
    parser.add_argument("--waterfall-min-db", type=float, default=-85)
    parser.add_argument("--waterfall-max-db", type=float, default=-15)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    if args.waterfall_rows < 1 or args.fps < 1:
        parser.error("--waterfall-rows and --fps must be positive")
    if args.waterfall_min_db >= args.waterfall_max_db:
        parser.error("waterfall min dB must be below max dB")

    try:
        import pygame
        from OpenGL import GL
    except ImportError as exc:
        raise SystemExit("Install desktop GPU viewer dependencies: pip install pygame PyOpenGL") from exc

    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
    pygame.display.set_mode((1100, 720), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
    pygame.display.set_caption("OpenRoadCode Native SDR | OpenGL")
    print("OpenGL renderer:", GL.glGetString(GL.GL_RENDERER).decode(errors="replace"))
    print("Press R to reset peak hold; Esc to exit.")
    GL.glDisable(GL.GL_DEPTH_TEST)
    GL.glEnable(GL.GL_TEXTURE_2D)
    texture = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    rows = args.waterfall_rows
    bins = args.fft_size
    GL.glTexImage2D(
        GL.GL_TEXTURE_2D, 0, GL.GL_RGB, bins, rows, 0, GL.GL_RGB,
        GL.GL_UNSIGNED_BYTE, np.zeros((rows, bins, 3), dtype=np.uint8),
    )

    # RGB palette: dark -> red -> orange -> yellow -> white.
    stops = np.array([[0, 0, 0], [85, 0, 90], [210, 30, 40],
                      [255, 145, 20], [255, 240, 80], [255, 255, 255]], dtype=float)
    x = np.linspace(0, len(stops) - 1, 256)
    palette = np.stack([np.interp(x, np.arange(len(stops)), stops[:, channel])
                        for channel in range(3)], axis=1).astype(np.uint8)
    analyzer = SpectrumAnalyzer(bins)
    display = SpectrumDisplayProcessor(args.smoothing)
    source = RtlSdrSource()
    write_row = 0
    filled = 0
    running = True
    clock = pygame.time.Clock()

    def quad(y_bottom: float, y_top: float, v_bottom: float, v_top: float) -> None:
        GL.glBegin(GL.GL_QUADS)
        for u, y, v in ((0, y_bottom, v_bottom), (1, y_bottom, v_bottom),
                        (1, y_top, v_top), (0, y_top, v_top)):
            GL.glTexCoord2f(u, v)
            GL.glVertex2f(-0.95 + 1.9 * u, y)
        GL.glEnd()

    def trace(values: tuple[float, ...], color: tuple[float, float, float]) -> None:
        points = np.empty((bins, 2), dtype=np.float32)
        points[:, 0] = np.linspace(-0.95, 0.95, bins)
        points[:, 1] = 0.1 + np.clip((np.asarray(values) + 100) / 100, 0, 1) * 0.85
        GL.glColor3f(*color)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(2, GL.GL_FLOAT, 0, points)
        GL.glDrawArrays(GL.GL_LINE_STRIP, 0, bins)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

    try:
        source.open()
        source.set_sample_rate(args.sample_rate)
        source.set_center_frequency(args.frequency)
        source.set_gain(args.gain)
        source.start()
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        display.reset_peaks()
            if not running:
                break
            frame = analyzer.analyze(source.read_iq())
            traces = display.process(frame)
            power = np.asarray(frame.power_db, dtype=np.float32)
            intensity = np.clip(
                (power - args.waterfall_min_db)
                / (args.waterfall_max_db - args.waterfall_min_db), 0, 1,
            )
            rgb = np.ascontiguousarray(palette[(intensity * 255).astype(np.uint8)])
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
            GL.glTexSubImage2D(
                GL.GL_TEXTURE_2D, 0, 0, write_row, bins, 1,
                GL.GL_RGB, GL.GL_UNSIGNED_BYTE, rgb,
            )
            write_row = (write_row + 1) % rows
            filled = min(filled + 1, rows)
            width, height = pygame.display.get_surface().get_size()
            GL.glViewport(0, 0, width, height)
            GL.glClearColor(0.035, 0.04, 0.055, 1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()
            GL.glDisable(GL.GL_TEXTURE_2D)
            trace(traces.smoothed_db, (0.2, 0.7, 1))
            trace(traces.peak_db, (1, 0.6, 0.2))
            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glColor3f(1, 1, 1)
            # Split texture at ring-buffer wrap: newest row remains at top.
            top = write_row / rows
            quad(-0.9, -0.05, top, top + (rows - write_row) / rows)
            if write_row:
                # The older section occupies the remaining bottom area.
                split = -0.9 + 0.85 * (write_row / rows)
                quad(-0.9, split, 0, top)
                quad(split, -0.05, top, 1)
            pygame.display.flip()
            clock.tick(args.fps)
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
        GL.glDeleteTextures([texture])
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
