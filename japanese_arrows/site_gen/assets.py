import math
from pathlib import Path

from japanese_arrows.models import Direction

DEFAULT_ASSETS_DIR = Path("web/assets/arrows")
CELL_SIZE = 120


def generate_arrow_svg(direction: Direction, output_dir: Path) -> None:
    width = CELL_SIZE
    height = CELL_SIZE
    cx = width / 2
    cy = height / 2

    dr, dc = direction.delta
    # atan2(y, x). y=dr, x=dc.
    angle_rad = math.atan2(dr, dc)
    angle_deg = math.degrees(angle_rad)

    # Updated Arrow Shape for less whitespace
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

    filename = f"arrow_{direction.name}.svg"
    with open(output_dir / filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_all_arrow_assets(output_dir: Path = DEFAULT_ASSETS_DIR) -> None:
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating arrow assets in {output_dir}...")
    for d in Direction:
        generate_arrow_svg(d, output_dir)
    print("Done generating assets.")
