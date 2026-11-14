from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from pprint import pprint
from shutil import copytree

import pygame

# ---------------------------------------------------------------------------
# Packing contract
#
# Input: a folder (plus its individual/ subfolder if organized); only *.png is
# considered (sibling .gif exports are validation sources, then deleted by
# --organize). Every PNG is a horizontal-strip spritesheet: frame height ==
# strip height (always), frame width varies per animation.
#
# Frame width resolution (explicit, never guessed):
#   1. listed in FRAME_WIDTHS (keyed by file stem) -> must divide strip width
#   2. otherwise the square default applies: width == strip height
# A strip fitting neither raises ValueError.
#
# Cross-check: while a sibling .gif exists, cols must equal the gif's frame
# count, so a wrong (or missing) FRAME_WIDTHS entry fails loudly instead of
# packing on a bad assumption. Gifs are deleted only AFTER packing validates.
#
# Animations are grouped by resolved frame size; each group packs into one
# sheet (rows = animations, uniform cells, short rows padded transparent)
# plus a manifest recording row/cols/cell/content_bounds per animation.
#
# Effect sheets are packed like any other animation.
# ---------------------------------------------------------------------------
FRAME_WIDTHS: dict[str, int] = {
    # dark-knight: wide heavy-combo frames (672x210; verified against gifs
    # before organize removed them)
    "dark-knight-heavy-combo-a": 672,
    "dark-knight-heavy-combo-b": 672,
    "dark-knight-heavy-combo-c": 672,
    "dark-knight-heavy-combo-a-effect": 672,
    "dark-knight-heavy-combo-b-effect": 672,
    "dark-knight-heavy-combo-c-effect": 672,
    "dark-knight-heavy-combo-leap-effect-a": 672,
    "dark-knight-heavy-combo-leap-effect-b": 672,
    "dark-knight-heavy-combo-leap-effect-c": 672,
    "dark-knight-heavy-combo-with-effect-a": 672,
    "dark-knight-heavy-combo-with-effect-b": 672,
    "dark-knight-heavy-combo-with-effect-c": 672,
    "dark-knight-dead-ground": 168,
    # chest: 11-frame open animation of 57x42 (gif: 11 frames)
    "blue-chest": 57,
    "green-chest": 57,
    "red-chest": 57,
    # demon-gunner: taller lunge frames 240x219 (gif: 10 frames)
    "demon-gunner-shoot": 240,
    # demon-swordsman: wide attack frames 240x192 (gif: 6 / 3 frames)
    "demon-swordsman-attack-landed": 240,
    "demon-swordsman-attack-prepare-leap": 240,
    # door: 4 frames of 96x48 (gif: 4) -- NOT the square default (48 -> 8)
    "door-blue": 96,
    "door-green": 96,
    "door-red": 96,
    # portal: 6 frames of 171x114 (gif: 6)
    "blue-portal": 171,
    "green-portal": 171,
    "red-portal": 171,
    # single-frame statics (gif: 1 frame) -- frame width == image width
    "key-blue": 39,
    "key-green": 39,
    "key-red": 39,
    "demon-heart-blue": 27,
    "demon-heart-green": 27,
    "demon-heart-red": 27,
    "blue-potion-large": 27,
    "green-potion-large": 27,
    "red-potion-large": 27,
    "blue-rune-tablet": 33,
    "green-rune-tablet": 33,
    "red-rune-tablet": 33,
    "energy-bar": 6,
    "hp-bar": 6,
    "one-bar-container": 207,
    "two-bar-container": 207,
}

# Whole-sheet render scales baked at pack time. heavy-combo frames are ~2x
# the pixel size of the 192x192 set; keys are original frame sizes.
GROUP_RENDER_SCALES: dict[tuple[int, int], float] = {
    (672, 210): 0.5,
}

# Never re-ingested as inputs.
_OUTPUT_RE = re.compile(r"-\d+x\d+\.png$")

# pixramen-valley folders to pack. prefix glob per folder; None = all *.png.
# Skipped: "small-potion" (pending -- no png exports yet, gifs only) and
# "tilesheet" (tilemap atlas consumed by tilemap-parser, not an animation).
PIXRAMEN_PATTERNS: dict[str, str] = {
    "chest": "*.png",
    "dark-knight": "dark-knight*.png",
    "demon-bat": "demon-bat*.png",
    "demon-gunner": "demon-gunner*.png",
    "demon-heart": "*.png",
    "demon-hound": "demon-hound*.png",
    "demon-swordsman": "demon-swordsman*.png",
    "door": "*.png",
    "hp_energy_bar": "*.png",
    "key": "*.png",
    "large-potion": "*.png",
    "portal": "*.png",
    "rune-tablet": "*.png",
}


def unpack_3x(path: Path, target_root: Path):
    if not path.is_dir():
        return
    if not any(path.iterdir()):
        return
    if path.name.lower() == "3x":
        dir_target = target_root / path.parent.parent.name
        dir_target.mkdir(exist_ok=True)
        copytree(path, dir_target, dirs_exist_ok=True)
        pprint(f"DRY: src={path}, target={dir_target}")
        return
    for child in path.iterdir():
        unpack_3x(child, target_root)


def gif_frame_count(path: Path) -> int | None:
    """Frame count of a .gif via minimal block parsing (no Pillow needed)."""
    data = path.read_bytes()
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        return None
    i = 6
    flags = data[10]
    i += 7
    if flags & 0x80:
        i += 3 * (2 << (flags & 7))
    frames = 0
    while i < len(data):
        b = data[i]
        if b == 0x21:  # extension: label byte + sub-blocks
            i += 2
            while i < len(data) and data[i] != 0:
                i += 1 + data[i]
            i += 1
        elif b == 0x2C:  # image descriptor = one frame
            frames += 1
            i += 9
            f = data[i]
            i += 1
            if f & 0x80:
                i += 3 * (2 << (f & 7))
            i += 1  # LZW min code size
            while i < len(data) and data[i] != 0:
                i += 1 + data[i]
            i += 1
        elif b == 0x3B:
            break
        else:
            i += 1
    return frames


def collect_animation_sheets(folder: Path, pattern: str) -> list[Path]:
    """Animation strip PNGs of a folder and its individual/ subfolder.

    Excludes this script's outputs. Effect sheets are included like any
    other animation.
    """
    sources = [folder]
    individual = folder / "individual"
    if individual.is_dir():
        sources.append(individual)

    files: list[Path] = []
    seen: set[str] = set()
    for src in sources:
        for f in sorted(src.glob(pattern)):
            if f.name in seen:
                continue
            seen.add(f.name)
            if _OUTPUT_RE.search(f.name) or f.name == f"{folder.name}-index.png":
                continue
            files.append(f)
    return sorted(files, key=lambda p: p.name)


def resolve_frame_width(stem: str, strip_w: int, strip_h: int) -> int:
    listed = FRAME_WIDTHS.get(stem)
    if listed is not None:
        if strip_w % listed != 0:
            raise ValueError(
                f"{stem}: strip width {strip_w} is not divisible by documented "
                f"frame width {listed}"
            )
        return listed
    if strip_w % strip_h == 0:
        return strip_h  # documented square default
    raise ValueError(
        f"{stem}: strip {strip_w}x{strip_h} does not match the square default "
        f"(width % height != 0); document its real frame width in FRAME_WIDTHS"
    )


def pack_group(
    folder: str,
    cell: tuple[int, int],
    entries: list[tuple[str, Path, int]],
) -> tuple[pygame.Surface, str, dict, list[dict]]:
    """Pack one frame-size group: rows = animations, uniform cells.

    Returns (packed Surface, sheet file name, sheet metadata, manifest rows).
    """
    fw, fh = cell
    scale = GROUP_RENDER_SCALES.get(cell, 1.0)
    cols_max = max(cols for _, _, cols in entries)
    packed = pygame.Surface((cols_max * fw, len(entries) * fh), pygame.SRCALPHA)
    packed.fill((0, 0, 0, 0))

    animations: list[dict] = []
    for row, (name, fpath, cols) in enumerate(entries):
        strip = pygame.image.load(str(fpath)).convert_alpha()
        bounds: pygame.Rect | None = None
        for c in range(cols):
            frame = strip.subsurface(pygame.Rect(c * fw, 0, fw, fh))
            packed.blit(frame, (c * fw, row * fh))
            b = frame.get_bounding_rect()
            if b.width and b.height:
                bounds = b if bounds is None else bounds.union(b)
        if bounds is None:  # fully transparent fallback: whole cell
            bounds = pygame.Rect(0, 0, fw, fh)

        animations.append(
            {
                "name": name,
                "sheet": None,  # filled below
                "row": row,
                "cols": cols,
                "cell": [round(fw * scale), round(fh * scale)],
                "content_bounds": [
                    round(bounds.x * scale),
                    round(bounds.y * scale),
                    round(bounds.width * scale),
                    round(bounds.height * scale),
                ],
            }
        )

    if scale != 1.0:
        packed = pygame.transform.scale_by(packed, scale)

    cell_out = (round(fw * scale), round(fh * scale))
    sheet_name = f"{folder}-{cell_out[0]}x{cell_out[1]}.png"
    sheet_meta = {"cell": list(cell_out), "rows": len(entries), "cols": cols_max}
    for anim in animations:
        anim["sheet"] = sheet_name
    return packed, sheet_name, sheet_meta, animations


def pack_sheet_group_files(
    folder: Path, pattern: str, organize: bool = False
) -> dict:
    """Pack one asset folder; returns its manifest dict (or None if empty)."""
    if not folder.is_dir():
        raise ValueError(f"not a directory: {folder}")
    files = collect_animation_sheets(folder, pattern)
    if not files:
        return None

    pygame.init()
    pygame.display.set_mode((0, 0))
    name = folder.name

    groups: dict[tuple[int, int], list[tuple[str, Path, int]]] = {}
    for f in files:
        strip = pygame.image.load(str(f)).convert_alpha()
        sw, sh = strip.get_size()
        fw = resolve_frame_width(f.stem, sw, sh)
        cols = sw // fw
        gif = f.with_suffix(".gif")
        n = gif_frame_count(gif) if gif.exists() else None
        if n is not None and cols != n:
            raise ValueError(
                f"{f.name}: resolved cols {cols} != sibling gif frame count {n}; "
                f"fix FRAME_WIDTHS"
            )
        groups.setdefault((fw, sh), []).append((f.stem, f, cols))

    manifest: dict = {"prefix": name, "sheets": {}, "animations": []}
    for cell in sorted(groups):
        entries = sorted(groups[cell], key=lambda e: e[0])
        packed, sheet_name, meta, anims = pack_group(name, cell, entries)
        pygame.image.save(packed, str(folder / sheet_name))
        manifest["sheets"][sheet_name] = meta
        manifest["animations"].extend(anims)
        print(f"{name}/{sheet_name}: {meta} ({len(anims)} animations)")

    out = folder / f"{name}-manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"{name}/manifest: {len(manifest['animations'])} animations")

    build_index(folder, name, manifest)

    legacy = folder / "spritesheet.png"
    if legacy.exists():
        legacy.unlink()
        print(f"{name}: removed legacy spritesheet.png")

    if organize:
        organize_folder(folder, pattern)

    pygame.quit()
    return manifest


def organize_folder(folder: Path, pattern: str) -> None:
    """Post-pack cleanup: permanently delete the .gif exports, then move the
    packed source strips into individual/ (exists_ok=True), so the folder
    root keeps only packed artifacts. Re-runs read from individual/ too."""
    gifs = sorted(folder.glob(pattern.replace(".png", ".gif")))
    for gif in gifs:
        gif.unlink()
    print(f"{folder.name}: removed {len(gifs)} gif files")

    target = folder / "individual"
    target.mkdir(exist_ok=True)
    moved = 0
    for f in collect_animation_sheets(folder, pattern):
        f.replace(target / f.name)
        moved += 1
    print(f"{folder.name}: moved {moved} source strips to individual/")


def build_index(
    folder: Path,
    name: str,
    manifest: dict,
    thumb_h: int = 48,
    font_size: int = 16,
) -> None:
    """Human-readable contact sheet: first frame of every animation as a
    thumbnail (whole cell, scaled), with row number, name, frame count and
    cell size, plus a red content-bounds debug rectangle. Purely for
    eyeballing; runtime sheets stay untouched."""
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        font = pygame.font.SysFont(None, font_size)
    except Exception:
        font = pygame.font.SysFont(None, font_size)

    sheets: dict[str, pygame.Surface] = {}
    rows: list[tuple[pygame.Surface, pygame.Surface]] = []
    for anim in manifest["animations"]:
        sname = anim["sheet"]
        if sname not in sheets:
            sheets[sname] = pygame.image.load(str(folder / sname)).convert_alpha()
        cw, ch = anim["cell"]
        frame = sheets[sname].subsurface(pygame.Rect(0, anim["row"] * ch, cw, ch))
        thumb_w = max(1, round(cw * thumb_h / ch))
        thumb = pygame.transform.smoothscale(frame, (thumb_w, thumb_h))
        bx, by, bw, bh = anim["content_bounds"]
        sx, sy = thumb_w / cw, thumb_h / ch
        pygame.draw.rect(
            thumb,
            (255, 60, 60, 255),
            pygame.Rect(round(bx * sx), round(by * sy), max(1, round(bw * sx)), max(1, round(bh * sy))),
            1,
        )
        text = font.render(
            f"{anim['row']:>2}  {anim['name']}  {anim['cols']}f  {cw}x{ch}",
            True,
            (240, 240, 240),
        )
        rows.append((thumb, text))

    if not rows:
        return
    pad, gap = 6, 12
    width = pad * 2 + max(t.get_width() + gap + tx.get_width() for t, tx in rows)
    row_h = max(thumb_h, max(tx.get_height() for _, tx in rows)) + pad
    index = pygame.Surface((width, pad + row_h * len(rows)), pygame.SRCALPHA)
    index.fill((24, 24, 28, 255))
    y = pad
    for thumb, text in rows:
        ty = y + (row_h - pad - max(thumb.get_height(), text.get_height())) // 2
        index.blit(thumb, (pad, ty))
        index.blit(text, (pad + thumb.get_width() + gap, ty))
        y += row_h
    out = folder / f"{name}-index.png"
    pygame.image.save(index, str(out))
    print(f"{name}/index: {len(rows)} rows")


def main(organize: bool = False, only: str | None = None) -> None:
    root = Path("data/assets/pixramen-valley")
    for folder_name, pattern in PIXRAMEN_PATTERNS.items():
        if only is not None and folder_name != only:
            continue
        print(f"== {folder_name}")
        pack_sheet_group_files(root / folder_name, pattern, organize=organize)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pack pixramen-valley animation strips into per-frame-size group sheets.")
    parser.add_argument("--only", metavar="FOLDER", help="pack a single pixramen-valley folder")
    parser.add_argument(
        "--organize",
        action="store_true",
        help="after packing: permanently delete .gif exports and move source strips into individual/",
    )
    args = parser.parse_args()
    main(organize=args.organize, only=args.only)
