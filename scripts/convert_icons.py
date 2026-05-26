#!/usr/bin/env python3
"""
Convert SVG icons ->PNG ->LVGL CF_TRUE_COLOR_ALPHA C arrays.

Step 1 (SVG ->PNG): uses Inkscape to rasterise icons/*.svg at the sizes
  defined in SVG_SIZES, writing PNGs to icons/out/.
Step 2 (PNG ->C):   converts icons/out/ (and loose icons/*.png) to C array
  files in src/display/ui/default/lvgl/images/.

Usage:
    python scripts/convert_icons.py            # SVG→PNG then PNG→C
    python scripts/convert_icons.py --png-only # skip SVG→PNG step
    python scripts/convert_icons.py --list     # show icon name ->C file mapping
    python scripts/convert_icons.py --check    # dry run, no files written

Requirements:
    pip install Pillow
    Inkscape installed (for SVG→PNG step)
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)

IMAGES_DIR = Path("src/display/ui/default/lvgl/images")
ICONS_DIR  = Path("icons")
OUT_DIR    = Path("icons/out")

# Maps SVG filename ->list of pixel sizes to export.
# Each entry produces icons/out/<base>-<N>x<N>.png
SVG_SIZES = {
    "angle-down.svg":        [40],
    "angle-left.svg":        [40],
    "angle-right.svg":       [40],
    "angle-up.svg":          [40],
    "bluetooth-alt.svg":     [20],
    "check.svg":             [40],
    "clock.svg":             [40],
    "clock-future-past.svg": [40],
    "coffee-bean.svg":       [80],
    "disk.svg":              [30],
    "dropdown-bar.svg":      [40],
    "equality.svg":          [40],
    "floppy-disks.svg":      [30],
    "meter-droplet.svg":     [40],
    "minus-small.svg":       [40],
    "mug-hot-alt.svg":       [80, 40],
    "pause.svg":             [40],
    "play.svg":              [40],
    "plus-small.svg":        [40],
    "power.svg":             [40],
    "raindrops.svg":         [80, 40],
    "refresh.svg":           [20],
    "settings.svg":          [40],
    "tachometer-fast.svg":   [40],
    "tap.svg":               [60],
    "thermometer-half.svg":  [40],
    "time-check.svg":        [40],
    "wifi.svg":              [20],
    "wind.svg":              [80, 40],
}

INKSCAPE_CANDIDATES = [
    "inkscape",                                          # on PATH (any OS)
    r"C:\Program Files\Inkscape\bin\inkscape.exe",      # Windows default
    r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
    "/Applications/Inkscape.app/Contents/MacOS/inkscape",  # macOS
]


def find_inkscape() -> str | None:
    for candidate in INKSCAPE_CANDIDATES:
        if shutil.which(candidate) or Path(candidate).is_file():
            return candidate
    return None


def svg_to_png(inkscape: str, dry_run: bool) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    converted = 0
    for svg_name, sizes in SVG_SIZES.items():
        svg_path = ICONS_DIR / svg_name
        if not svg_path.exists():
            print(f"  SKIP   {svg_name} (not found in icons/)")
            continue
        for size in sizes:
            base   = svg_path.stem
            output = OUT_DIR / f"{base}-{size}x{size}.png"
            if dry_run:
                print(f"  WOULD  {svg_name} ->{output.name}  ({size}x{size})")
            else:
                cmd = [inkscape, f"-w{size}", f"-h{size}", str(svg_path), "-o", str(output)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"  ERROR  {svg_name}: {result.stderr.strip()}")
                else:
                    print(f"  OK     {svg_name:<35} ->{output.name}")
            converted += 1
    return converted


def build_asset_map() -> dict:
    """Return {asset_basename: (c_path, var_name)} from existing C files."""
    asset_map = {}
    for c_file in sorted(IMAGES_DIR.glob("*.c")):
        text = c_file.read_text(encoding="utf-8")
        m = re.search(r"// IMAGE DATA: assets/(.+)", text)
        if not m:
            continue
        asset_name = m.group(1).strip()
        vm = re.search(r"const lv_img_dsc_t (\w+) =", text)
        if not vm:
            continue
        asset_map[asset_name] = (c_file, vm.group(1))
    return asset_map


def find_png(asset_name: str) -> Path | None:
    for d in [OUT_DIR, ICONS_DIR]:
        p = d / asset_name
        if p.exists():
            return p
    return None


def rgb_to_rgb565(r: int, g: int, b: int) -> tuple[int, int]:
    low  = ((g >> 2 & 0x07) << 5) | (b >> 3)
    high = (r >> 3) << 3 | (g >> 5)
    return low, high


def generate_c(png_path: Path, var_name: str, asset_name: str) -> str:
    img    = Image.open(png_path).convert("RGBA")
    w, h   = img.size
    pixels = list(img.getdata())

    hex_bytes = []
    for r, g, b, a in pixels:
        lo, hi = rgb_to_rgb565(r, g, b)
        hex_bytes += [f"0x{lo:02X}", f"0x{hi:02X}", f"0x{a:02X}"]

    lines = []
    for i in range(0, len(hex_bytes), 21):
        lines.append("    " + ", ".join(hex_bytes[i:i + 21]) + ",")
    if lines:
        lines[-1] = lines[-1].rstrip(",")

    data_name = f"{var_name}_data"
    pad       = " " * (len(f"const lv_img_dsc_t {var_name} = ") - 1)

    return (
        f"// This file was generated by scripts/convert_icons.py\n"
        f"// LVGL version: 8.3.11\n"
        f"// Project name: GaggiMate\n"
        f"\n"
        f'#include "../ui.h"\n'
        f"\n"
        f"#ifndef LV_ATTRIBUTE_MEM_ALIGN\n"
        f"#define LV_ATTRIBUTE_MEM_ALIGN\n"
        f"#endif\n"
        f"\n"
        f"// IMAGE DATA: assets/{asset_name}\n"
        f"const LV_ATTRIBUTE_MEM_ALIGN uint8_t {data_name}[] = {{\n"
        f"{chr(10).join(lines)}\n"
        f"}};\n"
        f"\n"
        f"const lv_img_dsc_t {var_name} = {{.header.always_zero = 0,\n"
        f"{pad} .header.w = {w},\n"
        f"{pad} .header.h = {h},\n"
        f"{pad} .data_size = sizeof({data_name}),\n"
        f"{pad} .header.cf = LV_IMG_CF_TRUE_COLOR_ALPHA,\n"
        f"{pad} .data = {data_name}}};\n"
    )


def png_to_c(asset_map: dict, dry_run: bool) -> tuple[int, int]:
    converted = skipped = 0
    for asset_name, (c_path, var_name) in sorted(asset_map.items()):
        png = find_png(asset_name)
        if not png:
            skipped += 1
            continue
        img  = Image.open(png)
        size = f"{img.width}x{img.height}"
        if dry_run:
            print(f"  WOULD  {png.name:<40} ->{c_path.name}  ({size})")
        else:
            c_path.write_text(generate_c(png, var_name, asset_name), encoding="utf-8")
            print(f"  OK     {png.name:<40} ->{c_path.name}  ({size})")
        converted += 1
    return converted, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--png-only", action="store_true", help="Skip SVG->PNG, only run PNG->C")
    parser.add_argument("--list",     action="store_true", help="Show icon name -> C file mapping")
    parser.add_argument("--check",    action="store_true", help="Dry run, no files written")
    parser.add_argument("--inkscape", metavar="PATH",      help="Path to inkscape executable")
    args = parser.parse_args()

    asset_map = build_asset_map()

    if args.list:
        print(f"{'Asset name':<45} {'C file':<35} PNG found")
        print("-" * 100)
        for asset_name, (c_path, var_name) in sorted(asset_map.items()):
            found = find_png(asset_name)
            print(f"{asset_name:<45} {c_path.name:<35} {found or '(not found)'}")
        return

    if not args.png_only:
        inkscape = args.inkscape or find_inkscape()
        if not inkscape:
            print("Inkscape not found - skipping SVG->PNG step.")
            print("Install Inkscape or place pre-rendered PNGs in icons/out/ and use --png-only.")
        else:
            print(f"SVG -> PNG  (inkscape: {inkscape})")
            svg_to_png(inkscape, dry_run=args.check)
            print()

    print("PNG -> C arrays")
    converted, skipped = png_to_c(asset_map, dry_run=args.check)
    print(f"\n{converted} converted, {skipped} skipped (no PNG found - run --list to see names).")


if __name__ == "__main__":
    main()
