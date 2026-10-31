"""Read SFNT cmap coverage using stdlib; no font installation or extra dependency."""
from functools import lru_cache
from pathlib import Path
import struct


@lru_cache(maxsize=32)
def codepoints(filename, mtime, size):
    data = Path(filename).read_bytes()
    def u16(p): return struct.unpack_from('>H', data, p)[0]
    def u32(p): return struct.unpack_from('>I', data, p)[0]
    # Pillow's default font index is zero, including TTC collections.
    base = u32(12) if data[:4] == b'ttcf' else 0
    tables = {data[p:p+4]: u32(p+8) for p in range(base+12, base+12+16*u16(base+4), 16)}
    cmap = tables[b'cmap']; result = set()
    for p in range(cmap+4, cmap+4+8*u16(cmap+2), 8):
        platform, encoding, offset = struct.unpack_from('>HHI', data, p)
        if platform != 0 and not (platform == 3 and encoding in (1, 10)):
            continue
        sub = cmap+offset; fmt = u16(sub)
        if fmt == 12:
            for q in range(sub+16, sub+16+12*u32(sub+12), 12):
                start, end, glyph = struct.unpack_from('>III', data, q)
                if end > 0x10ffff or end < start:
                    raise ValueError('Invalid font cmap range')
                result.update(range(start+(glyph == 0), end+1))
        elif fmt == 4:
            n = u16(sub+6)//2; ends = sub+14; starts = ends+2*n+2
            deltas = starts+2*n; offsets = deltas+2*n
            for i in range(n):
                start, end, delta, shift = u16(starts+2*i), u16(ends+2*i), u16(deltas+2*i), u16(offsets+2*i)
                for cp in range(start, min(end, 0xfffe)+1):
                    glyph = u16(offsets+2*i+shift+2*(cp-start)) if shift else cp
                    glyph = (glyph+delta)&0xffff if glyph or not shift else 0
                    if glyph: result.add(cp)
    return frozenset(result)


def require_glyphs(path, text):
    path = Path(path)
    try:
        stat = path.stat()
        available = codepoints(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except (OSError, KeyError, IndexError, struct.error) as exc:
        raise ValueError(f'Cannot verify font coverage: {path.name}; choose a readable TTF/OTF/TTC font.') from exc
    missing = sorted({c for c in text if not c.isspace() and ord(c) not in available})
    if missing:
        raise ValueError(f'Font {path.name} is missing actual label glyphs: {"".join(missing[:16])}; choose a CJK-capable regular/bold font.')
