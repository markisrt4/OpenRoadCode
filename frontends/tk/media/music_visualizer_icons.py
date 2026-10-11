# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Small vector previews for native and browser visualizer selection."""
import math

from PIL import Image, ImageDraw, ImageTk

from ui.music_visualizer import MusicVisualizationMode


def visualizer_icon(master, mode, color):
    """Render a crisp, antialiased pictogram without platform-specific glyphs."""
    image = Image.new('RGBA', (104, 104))
    draw = ImageDraw.Draw(image)

    def line(points, width=5):
        draw.line(points, fill=color, width=width, joint='curve')

    def circle(x, y, radius, width=4):
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=width)

    if mode is MusicVisualizationMode.FREQUENCY_TUNNEL:
        for inset in (8, 24, 38):
            draw.rounded_rectangle((inset, inset, 104-inset, 104-inset), radius=9,
                                   outline=color, width=4)
        for x, y in ((8, 8), (96, 8), (8, 96), (96, 96)):
            line([(x, y), (52, 52)], 3)
    elif mode in (MusicVisualizationMode.SPECTRUM, MusicVisualizationMode.BOOMBOX):
        heights = (24, 47, 77, 59, 35)
        for i, height in enumerate(heights):
            x = 12 + i * 17
            if mode is MusicVisualizationMode.BOOMBOX:
                for y in range(90, 90-height, -10):
                    draw.rectangle((x, y-6, x+10, y), fill=color)
            else:
                draw.rectangle((x, 90-height, x+10, 90), fill=color)
        line([(7, 94), (97, 94)], 3)
    elif mode is MusicVisualizationMode.ORBITING_PLANETS:
        draw.ellipse((6, 25, 98, 79), outline=color, width=3)
        circle(52, 52, 15)
        circle(15, 36, 7)
        circle(88, 69, 9)
    elif mode is MusicVisualizationMode.ELECTRIC_FREEWAY:
        line([(7, 94), (43, 15)])
        line([(97, 94), (61, 15)])
        for y in (35, 57, 88):
            line([(52, y-9), (52, y)], 4)
        line([(12, 61), (92, 61)], 3)
    elif mode is MusicVisualizationMode.EXPLOSION_FIELD:
        for i in range(8):
            angle = i * math.tau / 8
            line([(52+math.cos(angle)*18, 52+math.sin(angle)*18),
                  (52+math.cos(angle)*43, 52+math.sin(angle)*43)])
        circle(52, 52, 9)
    elif mode is MusicVisualizationMode.STAR_DANCE:
        for x, y, radius in ((29, 30, 17), (74, 62, 22), (22, 84, 8)):
            points = [(x+math.sin(i*math.pi/5)*(radius if i % 2 == 0 else radius*.4),
                       y-math.cos(i*math.pi/5)*(radius if i % 2 == 0 else radius*.4))
                      for i in range(10)]
            draw.polygon(points, outline=color, width=3)
    elif mode is MusicVisualizationMode.ELECTRIC_RINGS:
        for radius in (13, 28, 43):
            circle(52, 52, radius)
    elif mode is MusicVisualizationMode.NEON_RIBBON:
        for offset in (-12, 0, 12):
            line([(x, 52+offset+math.sin(x/15)*22) for x in range(7, 98)], 4)
    else:
        for i in range(6):
            angle = i * math.tau / 6
            points = [(52, 52)]
            points += [(52+math.cos(angle+delta)*r, 52+math.sin(angle+delta)*r)
                       for delta, r in ((-.3, 28), (0, 45), (.3, 28))]
            points += [(52, 52)]
            line(points, 3)
    return ImageTk.PhotoImage(image.resize((26, 26), Image.Resampling.LANCZOS), master=master)
