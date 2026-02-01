# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import math

from japanese_arrows.models import Puzzle


def read_puzzle(file_path: str) -> Puzzle:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Puzzle.from_string(content)


def write_puzzle(puzzle: Puzzle, file_path: str) -> None:
    if file_path.endswith(".svg"):
        write_puzzle_as_svg(puzzle, file_path)
    else:
        content = puzzle.to_string()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


def write_puzzle_as_svg(puzzle: Puzzle, file_path: str, cell_size: int = 120) -> None:
    width = puzzle.cols * cell_size
    height = puzzle.rows * cell_size

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        "  <style>",
        "    text { font-family: 'Noto Serif JP', 'serif'; pointer-events: none; }",
        "    .candidate { font-size: 14px; fill: #222; font-weight: bold; }",
        "    .number { font-size: 34px; font-weight: bold; fill: black; }",
        "  </style>",
        "</defs>",
        # Background
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]

    # Draw cells
    for r in range(puzzle.rows):
        for c in range(puzzle.cols):
            cell = puzzle.grid[r][c]
            cx = c * cell_size + cell_size / 2
            cy = r * cell_size + cell_size / 2

            lines.append(f'<g transform="translate({cx},{cy})">')

            # Arrow Rotation
            dr, dc = cell.direction.delta
            angle_rad = math.atan2(dr, dc)
            angle_deg = math.degrees(angle_rad)

            lines.append(f'<g transform="rotate({angle_deg})">')
            lines.append(
                '<path d="M -45 -25 Q -12 -30 20 -28 L 20 -48 Q 40 -25 55 0 Q 40 25 20 48 '
                'L 20 28 Q -12 30 -45 25 Q -40 0 -45 -25 Z" '
                'fill="white" stroke="#333333" stroke-width="3"/>'
            )
            lines.append("</g>")

            # Content
            if cell.number is not None:
                lines.append(
                    f'<text x="0" y="0" text-anchor="middle" dominant-baseline="central" '
                    f'class="number">{cell.number}</text>'
                )
            elif cell.candidates:
                sorted_cands = sorted(list(cell.candidates))
                all_digits = all(0 <= x <= 9 for x in sorted_cands)

                if all_digits:
                    # 3x3 layout
                    # Spacing 18px to fit in -30..30 box comfortably
                    spacing = 18
                    for val in sorted_cands:
                        if val == 0:
                            dx, dy = 0, spacing
                        else:
                            row_idx = (val - 1) // 3
                            col_idx = (val - 1) % 3
                            dx = (col_idx - 1) * spacing
                            dy = (row_idx - 1) * spacing
                        lines.append(
                            f'<text x="{dx}" y="{dy}" text-anchor="middle" dominant-baseline="central" '
                            f'class="candidate">{val}</text>'
                        )
                else:
                    # Fallback for large numbers
                    cand_str = ",".join(str(x) for x in sorted_cands)
                    fs = 14 if len(cand_str) < 8 else 10
                    lines.append(
                        f'<text x="0" y="0" text-anchor="middle" dominant-baseline="central" '
                        f'font-size="{fs}" font-weight="bold">{cand_str}</text>'
                    )

            lines.append("</g>")

    lines.append("</svg>")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
