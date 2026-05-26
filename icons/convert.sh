#!/usr/bin/env bash
# Rasterise SVG icons to PNG at the sizes expected by the LVGL image converter.
# Output goes to icons/out/ — then run: python scripts/convert_icons.py
#
# Requires Inkscape:
#   Linux:  apt install inkscape
#   macOS:  brew install --cask inkscape

set -euo pipefail

if command -v inkscape &>/dev/null; then
    INKSCAPE="inkscape"
elif [[ -x "/Applications/Inkscape.app/Contents/MacOS/inkscape" ]]; then
    INKSCAPE="/Applications/Inkscape.app/Contents/MacOS/inkscape"
else
    echo "Inkscape not found. Install it or convert SVGs to PNG manually."
    exit 1
fi

mkdir -p out

convert() {
    local input="$1"
    local size="$2"
    local base="${input%.*}"
    local output="out/${base}-${size}x${size}.png"
    echo "  $input → $output"
    "$INKSCAPE" -w "$size" -h "$size" "$input" -o "$output"
}

convert "angle-down.svg"        40
convert "angle-left.svg"        40
convert "angle-right.svg"       40
convert "angle-up.svg"          40
convert "bluetooth-alt.svg"     20
convert "check.svg"             40
convert "clock.svg"             40
convert "clock-future-past.svg" 40
convert "coffee-bean.svg"       80
convert "disk.svg"              30
convert "dropdown-bar.svg"      40
convert "equality.svg"          40
convert "floppy-disks.svg"      30
convert "meter-droplet.svg"     40
convert "minus-small.svg"       40
convert "mug-hot-alt.svg"       80
convert "mug-hot-alt.svg"       40
convert "pause.svg"             40
convert "play.svg"              40
convert "plus-small.svg"        40
convert "power.svg"             40
convert "raindrops.svg"         80
convert "raindrops.svg"         40
convert "refresh.svg"           20
convert "settings.svg"          40
convert "tachometer-fast.svg"   40
convert "tap.svg"               60
convert "thermometer-half.svg"  40
convert "time-check.svg"        40
convert "wifi.svg"              20
convert "wind.svg"              80
convert "wind.svg"              40

echo "Done. Run: python scripts/convert_icons.py"
