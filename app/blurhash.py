"""A small BlurHash encoder (woltapp/blurhash), implemented here rather than
pulled in as a dependency.

It is ~70 lines of well-known DCT arithmetic, it runs once per book at cache
time on a 32px thumbnail, and §9.6 of the brief asks us to keep the dependency
count deliberately low. Adding a package for this would be a worse trade.

The output is the string the client paints as a cover placeholder while the
real image loads.
"""
from __future__ import annotations

import math

_CHARS = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~"
)


def _srgb_to_linear(value: int) -> float:
    v = value / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(value: float) -> int:
    v = max(0.0, min(1.0, value))
    if v <= 0.0031308:
        return int(v * 12.92 * 255 + 0.5)
    return int((1.055 * (v ** (1 / 2.4)) - 0.055) * 255 + 0.5)


def _sign_pow(value: float, exponent: float) -> float:
    return math.copysign(abs(value) ** exponent, value)


def _base83(value: int, length: int) -> str:
    out = []
    for i in range(1, length + 1):
        digit = (value // (83 ** (length - i))) % 83
        out.append(_CHARS[digit])
    return "".join(out)


def encode_rgb(
    pixels: list[tuple[int, int, int]],
    width: int,
    height: int,
    x_components: int = 4,
    y_components: int = 3,
) -> str:
    """Encode a flat row-major list of RGB tuples."""
    if not 1 <= x_components <= 9 or not 1 <= y_components <= 9:
        raise ValueError("components must be between 1 and 9")
    if width <= 0 or height <= 0 or len(pixels) < width * height:
        raise ValueError("pixel buffer does not match the given size")

    linear = [
        (_srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b))
        for r, g, b in pixels[: width * height]
    ]

    components: list[tuple[float, float, float]] = []
    scale = 1.0 / (width * height)
    for j in range(y_components):
        for i in range(x_components):
            norm = 1.0 if (i == 0 and j == 0) else 2.0
            r = g = b = 0.0
            for y in range(height):
                cos_y = math.cos(math.pi * j * y / height)
                row = y * width
                for x in range(width):
                    basis = norm * math.cos(math.pi * i * x / width) * cos_y
                    pr, pg, pb = linear[row + x]
                    r += basis * pr
                    g += basis * pg
                    b += basis * pb
            components.append((r * scale, g * scale, b * scale))

    dc, ac = components[0], components[1:]

    out = _base83((x_components - 1) + (y_components - 1) * 9, 1)
    if ac:
        actual_max = max(max(abs(c) for c in comp) for comp in ac)
        quantised_max = max(0, min(82, int(actual_max * 166 - 0.5)))
        max_value = (quantised_max + 1) / 166
        out += _base83(quantised_max, 1)
    else:
        max_value = 1.0
        out += _base83(0, 1)

    out += _base83(
        (_linear_to_srgb(dc[0]) << 16) + (_linear_to_srgb(dc[1]) << 8) + _linear_to_srgb(dc[2]),
        4,
    )
    for comp in ac:
        quantised = [
            int(max(0, min(18, math.floor(_sign_pow(c / max_value, 0.5) * 9 + 9.5))))
            for c in comp
        ]
        out += _base83(quantised[0] * 19 * 19 + quantised[1] * 19 + quantised[2], 2)
    return out


def encode_image(image, x_components: int = 4, y_components: int = 3) -> str:
    """Encode a PIL image, thumbnailing first — the hash is 4x3 anyway."""
    small = image.convert("RGB")
    small.thumbnail((32, 32))
    width, height = small.size
    return encode_rgb(list(small.getdata()), width, height, x_components, y_components)
