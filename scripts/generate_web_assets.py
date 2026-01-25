import math
import os

from japanese_arrows.models import Direction

OUTPUT_DIR = "web/assets/arrows"
CELL_SIZE = 120


def generate_arrow_svg(direction: Direction, filename: str) -> None:
    width = CELL_SIZE
    height = CELL_SIZE
    cx = width / 2
    cy = height / 2

    dr, dc = direction.delta
    # atan2(y, x). y=dr, x=dc.
    angle_rad = math.atan2(dr, dc)
    angle_deg = math.degrees(angle_rad)

    # Updated Arrow Shape for less whitespace
    # Tail from -45 to 20. Width +/- 28 (total 56).
    # Head from 20 to 55. Width +/- 48 (total 96) at base.

    # We essentially wrap the single arrow in an SVG
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<g transform="translate({cx},{cy})">',
        f'<g transform="rotate({angle_deg})">',
        '<path d="M -45 -28 L 20 -28 L 20 -48 L 55 0 L 20 48 L 20 28 L -45 28 Z" '
        'fill="white" stroke="black" stroke-width="2"/>',
        "</g>",
        "</g>",
        "</svg>",
    ]

    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {filename}")


def main() -> None:
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for d in Direction:
        # e.g. NORTH -> arrow_NORTH.svg
        # But wait, the frontend has unicode characters.
        # I should probably use the direction name in the filename.
        filename = f"arrow_{d.name}.svg"
        generate_arrow_svg(d, filename)


if __name__ == "__main__":
    main()
