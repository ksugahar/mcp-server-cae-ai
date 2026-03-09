"""
MTEF (MathType Equation Format) v3 binary format knowledge base.

Specification extracted from the EQNEDT32 equation editor C parser (eq2tex.c)
and validated against 200+ roundtrip-verified MTEF<->LaTeX pairs (59 automated E2E tests).

This knowledge enables Claude to:
- Parse MTEF binary streams into LaTeX
- Generate correct MTEF binary from LaTeX expressions
- Debug MTEF encoding issues

Sources:
  - S:\\00_事務所理系\\Office\\数式3.0\\src\\eq2tex.c (parser, ~2900 lines)
  - S:\\00_事務所理系\\Office\\数式3.0\\tests\\db\\ (159+ verified pairs)
  - Microsoft Equation Editor 3.0 (EQNEDT32.EXE) binary analysis
"""

# ================================================================
# 1. MTEF Stream Header
# ================================================================

MTEF_HEADER = """
# MTEF v3 Binary Stream Header

Every MTEF stream starts with a **5-byte header**:

| Offset | Size | Field       | Value | Description |
|--------|------|-------------|-------|-------------|
| 0      | 1    | version     | 3     | MTEF version |
| 1      | 1    | platform    | 1     | 0=Mac, 1=Windows |
| 2      | 1    | product     | 1     | Product identifier |
| 3      | 1    | prod_ver    | 3     | 3=v3.10 (EQNEDT32), 10=v10.2 (MathType) |
| 4      | 1    | prod_subver | 10    | Sub-version |

Standard header bytes: `03 01 01 03 0a`

## Equation Native Header (OLE)

When MTEF is embedded in an OLE "Equation Native" stream, a 28-byte
header precedes the MTEF data. Detection: first 2 bytes (LE uint16) == 28
and bytes at offset 28-29 look like valid MTEF header (version<=5, platform<=2).
"""

# ================================================================
# 2. Record Tag Byte
# ================================================================

MTEF_RECORD_TAGS = """
# Record Tag Byte Format

Each record begins with a single tag byte:
```
tag = (options << 4) | record_type
```

- Bits [3:0] (low nibble): record type
- Bits [7:4] (high nibble): option flags

## Record Types

| Value | Name    | Description |
|-------|---------|-------------|
| 0     | END     | End-of-list marker (0x00) |
| 1     | LINE    | Line (sequence of objects) |
| 2     | CHAR    | Character |
| 3     | TMPL    | Template (fraction, integral, etc.) |
| 4     | PILE    | Pile (multi-line structure) |
| 5     | MATRIX  | Matrix |
| 6     | EMBELL  | Embellishment (accent) |
| 7     | RULER   | Ruler (tab stops) |
| 8     | FONT    | Font definition |
| 9     | SIZE    | Explicit size change |
| 10    | FULL    | Type-size: full (display) — tag=0x0a |
| 11    | SUB     | Type-size: subscript — tag=0x0b |
| 12    | SUB2    | Type-size: sub-subscript — tag=0x0c |
| 13    | SYM     | Type-size: symbol — tag=0x0d |
| 14    | SUBSYM  | Type-size: sub-symbol — tag=0x0e |

## Option Flags

| Bit | Value | Name           | Applies to |
|-----|-------|----------------|-----------|
| 3   | 0x08  | OPT_NUDGE      | All: nudge data follows |
| 0   | 0x01  | OPT_LINE_NULL  | LINE: no children (null LINE) |
| 2   | 0x04  | OPT_LINE_LSPACE| LINE: line spacing follows |
| 1   | 0x02  | OPT_CHAR_EMBELL| CHAR: embellishment list follows |
| 1   | 0x02  | (PILE)         | PILE: ruler data follows |

## Common Tag Values

| Tag  | Meaning |
|------|---------|
| 0x00 | END marker |
| 0x01 | Normal LINE |
| 0x11 | Null LINE (no children) |
| 0x02 | CHAR (no options) |
| 0x12 | CHAR (with variation TEXT flag: italic/variable) |
| 0x03 | TMPL (no options) |
| 0x04 | PILE |
| 0x0a | SIZE(FULL) — no data, just tag |
| 0x0b | SIZE(SUB) — no data, just tag |
| 0x0d | SIZE(SYM) — no data, just tag |

## End Markers

`0x00` (END) terminates:
- Object lists within a LINE
- Slots within a TMPL
- PILE line lists
- Top-level record stream

Multiple trailing `0x00` bytes at end-of-stream is normal.
"""

# ================================================================
# 3. CHAR Records
# ================================================================

MTEF_CHAR_RECORDS = """
# CHAR Record (record_type = 2)

## Format
```
tag (1 byte) | typeface_byte (1 byte) | char_code (2 bytes LE)
```

- tag: `0x02` (plain) or `0x12` (with TEXT variation for italic variables)
- typeface_byte: font index + 0x80 (128) in v3.10
- char_code: 2-byte little-endian character code

## Typeface Mapping (v3.10: byte = typeface + 128)

| Byte | Typeface | Name      | Usage |
|------|----------|-----------|-------|
| 0x81 | 1  | TEXT      | Roman text (\\text{}) |
| 0x82 | 2  | FUNCTION  | sin, cos, lim etc. |
| 0x83 | 3  | VARIABLE  | Italic variables (a, x, etc.) |
| 0x84 | 4  | LC_GREEK  | Lowercase Greek (alpha, beta) |
| 0x85 | 5  | UC_GREEK  | Uppercase Greek (Omega, Sigma) |
| 0x86 | 6  | SYMBOL    | Math symbols (+, =, integral, etc.) |
| 0x87 | 7  | VECTOR    | Bold vectors |
| 0x88 | 8  | NUMBER    | Digits (0-9) |
| 0x89 | 9  | USER1     | User-defined 1 |
| 0x8a | 10 | USER2     | User-defined 2 |
| 0x8b | 11 | MTEXTRA   | MT Extra font |
| 0x96 | 22 | DISPLAY   | Display chars (fence/bigop glyphs) |

## Character Code Examples

### Variables (typeface 0x83, italic)
```
12 83 61 00  →  a    12 83 78 00  →  x
12 83 41 00  →  A    12 83 4e 00  →  N
```

### Numbers (typeface 0x88)
```
02 88 30 00  →  0    02 88 31 00  →  1    02 88 32 00  →  2
```

### Greek (typeface 0x84=lowercase, 0x85=uppercase)
```
02 84 61 00  →  alpha(α)    02 84 62 00  →  beta(β)
02 85 57 00  →  Omega(Ω)    02 84 6c 00  →  lambda(λ)
02 84 c8 03  →  psi(ψ)      02 84 c6 03  →  phi(φ)
02 86 6c 00  →  lambda(λ) via Symbol font
```

### Symbols (typeface 0x86)
```
02 86 2b 00  →  +       02 86 2d 00  →  -
02 86 3d 00  →  =       02 86 b4 00  →  × (\\times)
02 86 c5 22  →  · (\\cdot, U+22C5)
02 86 c5 00  →  · (\\cdot, 0xC5 in Symbol font)
02 86 d1 00  →  ∇ (\\nabla, 0xD1 in Symbol font)
02 86 b6 00  →  ∂ (\\partial)
02 86 6e 00  →  ν (\\nu via Symbol position)
02 86 73 00  →  σ (\\sigma via Symbol position)
02 86 77 00  →  ω (\\omega via Symbol position)
02 86 07 00  →  ∇ (alternate)
02 86 07 22  →  ∇ (U+2207)
02 86 95 22  →  ⊕ (\\oplus, U+2295)
02 86 29 22  →  ∩ (\\cap, U+2229)
02 86 2a 22  →  ∪ (\\cup, U+222A)
02 86 2b 22  →  ∫ (integral display, U+222B)
```

### Display Characters (typeface 0x96 = 22)
Used for fence/bigop visual glyphs (not content):
```
02 96 28 00  →  ( (left paren display)
02 96 29 00  →  ) (right paren display)
02 96 37 fe  →  overbrace glyph (U+FE37)
02 96 38 fe  →  underbrace glyph (U+FE38)
02 96 09 ec  →  ‖ left (double bar, 0xEC09)
02 96 0a ec  →  ‖ right (double bar, 0xEC0A)
02 96 f0 f8  →  ⌊ (floor left)
02 96 fb f8  →  ⌋ (floor right)
02 96 ee f8  →  ⌈ (ceil left)
02 96 f9 f8  →  ⌉ (ceil right)
02 96 29 23  →  ⟩ (angle right)
02 96 07 ec  →  | (Dirac bar)
02 96 2a 23  →  ⟪ (angle left/right for Dirac)
```

## TEXT typeface (0x81) and FUNCTION typeface (0x82)
```
02 81 44 00  →  D (TEXT: used in \\text{Dirac})
02 82 28 00  →  ( (FUNCTION font parenthesis, NOT a fence template)
02 82 29 00  →  ) (FUNCTION font parenthesis)
02 82 7c 00  →  | (FUNCTION font vertical bar)
```

## Key Insight: Parentheses as Characters vs Templates

EQNEDT32 can represent parentheses two ways:
1. **As characters** (FUNCTION font 0x82): `02 82 28 00` / `02 82 29 00`
   - Simpler, fewer bytes. Used in manual input.
2. **As fence templates** (tmPAREN): `03 01 00 00 ... 02 96 28 00 02 96 29 00`
   - More structured, includes display chars. Used by builder.
Both are valid MTEF. The character approach is more compact.
"""

# ================================================================
# 4. Template Records
# ================================================================

MTEF_TEMPLATES = """
# TMPL Record (record_type = 3)

## Format
```
tag (1 byte) | selector (1 byte) | variation (1-2 bytes) | slot[0]...slot[n]
```

Each slot is an object list terminated by REC_END (0x00).

## Variation Encoding
- If first byte < 128: variation = that byte
- If first byte >= 128: variation = ((first_byte - 128) << 8) | next_byte

## Template Selector Table

### Fences (1 slot each)
| Sel | Name      | LaTeX |
|-----|-----------|-------|
| 0   | tmANGLE   | \\langle ... \\rangle |
| 1   | tmPAREN   | \\left( ... \\right) |
| 2   | tmBRACE   | \\lbrace ... \\rbrace |
| 3   | tmBRACK   | \\left[ ... \\right] |
| 4   | tmBAR     | \\left| ... \\right| |
| 5   | tmDBAR    | \\left\\| ... \\right\\| |
| 6   | tmFLOOR   | \\lfloor ... \\rfloor |
| 7   | tmCEIL    | \\lceil ... \\rceil |

Fence variation: 0=both, 1=left only, 2=right only

### Root (1-2 slots)
| Sel | Name   | Slots | Description |
|-----|--------|-------|-------------|
| 13  | tmROOT | var=0: 1 slot (radicand), var=1: 2 slots (radicand, index) |

### Fraction (2 slots)
| Sel | Name      | Slots | LaTeX |
|-----|-----------|-------|-------|
| 14  | tmFRACT   | 2     | \\dfrac{slot[0]}{slot[1]} |
| 41  | tmSLFRACT | 2     | slot[0]/slot[1] (slashed) |

### Sub/Superscript (2 slots)
| Sel | Name      | Variation | LaTeX |
|-----|-----------|-----------|-------|
| 15  | tmSCRIPT  | var=0: superscript | ^{slot[1]} |
| 15  | tmSCRIPT  | var=1: subscript   | _{slot[0]} |
| 15  | tmSCRIPT  | var=2: both        | _{slot[0]}^{slot[1]} |
| 44  | tmLSCRIPT | var=0/1/2          | Left-side scripts |

### Decorations (1 slot each)
| Sel | Name      | LaTeX |
|-----|-----------|-------|
| 16  | tmUBAR    | \\underline{} |
| 17  | tmOBAR    | \\overline{} |
| 18  | tmLARROW  | \\overleftarrow{} |
| 19  | tmRARROW  | \\overrightarrow{} |
| 20  | tmBARROW  | \\overleftrightarrow{} |

### Integrals (1-3 slots)
| Sel | Name    | LaTeX |
|-----|---------|-------|
| 21  | tmSINT  | \\int (single) |
| 22  | tmDINT  | \\iint (double) |
| 23  | tmTINT  | \\iiint (triple) |
| 24  | tmSSINT | \\int with limits style |
| 25  | tmDSINT | \\iint with limits style |
| 26  | tmTSINT | \\iiint with limits style |

Contour variants: tmSINT var=3 → \\oint, tmDINT var=2 → \\oiint, tmTINT var=2 → \\oiiint

Integral variation bits:
- bit 0 (0x01): has lower limit
- bit 1 (0x02): has upper limit
- Slot count = 1 + (has_lower ? 1 : 0) + (has_upper ? 1 : 0)
- Slot order: [integrand, lower?, upper?]

### Braces (2 slots)
| Sel | Name       | LaTeX |
|-----|------------|-------|
| 27  | tmUHBRACE  | \\overbrace{slot[0]}^{label} |
| 28  | tmLHBRACE  | \\underbrace{slot[0]}_{label} |

### Big Operators (1-3 slots, same variation as integrals)
| Sel | Name      | LaTeX |
|-----|-----------|-------|
| 29  | tmSUM     | \\sum (limits) |
| 30  | tmISUM    | \\sum (nolimits) |
| 31  | tmPROD    | \\prod (limits) |
| 32  | tmIPROD   | \\prod (nolimits) |
| 33  | tmCOPROD  | \\coprod (limits) |
| 35  | tmUNION   | \\bigcup |
| 37  | tmINTER   | \\bigcap |

### Others
| Sel | Name     | Slots | Description |
|-----|----------|-------|-------------|
| 39  | tmLIM    | 2-3   | \\lim |
| 40  | tmLDIV   | 1-2   | Long division |
| 42  | tmINTOP  | var   | Integral over/under |
| 43  | tmSUMOP  | var   | Summation over/under |
| 45  | tmDIRAC  | 1-2   | Dirac bra-ket |
| 48  | tmOARC   | 1     | Over-arc accent |
"""

# ================================================================
# 5. EQNEDT32 Patterns
# ================================================================

MTEF_EQNEDT32_PATTERNS = """
# EQNEDT32 Encoding Patterns

EQNEDT32 uses distinctive patterns that differ from standard MTEF.
Understanding these is essential for generating compatible MTEF.

## Empty Slot[0] Pattern

Most EQNEDT32 templates use:
1. slot[0] = immediate 0x00 (empty)
2. Actual content follows as sibling records or packed into slot[1]
3. Display characters (typeface=22) mark the visual glyphs

This applies to: fences, integrals, bigops, braces, decorations.

## Fence Pattern (tmPAREN, selector=1)

```
03 01 00       TMPL tmPAREN, var=0 (both delimiters)
00             slot[0]: REC_END (empty!)
01             LINE (content — sibling, not child of slot)
  ...content...
00             END LINE
02 96 28 00    ( display char (typeface 22)
02 96 29 00    ) display char (typeface 22)
```

Fence content is placed as a **sibling LINE** after the empty slot[0],
followed by display bracket characters.

## Integral Pattern (tmSINT, selector=0x15=21)

### No limits (var=0x00):
```
03 15 00       TMPL tmSINT, var=0
00             slot[0]: REC_END (empty)
01             LINE (integrand content as sibling)
  ...content...
00             END LINE content
0b             SIZE(SUB) — structural marker
11             null LINE
11             null LINE
0d             SIZE(SYM) — display char follows
02 86 2b 22    ∫ display char (U+222B, symbol font)
```

### With limits (var=0x01 lower, var=0x03 both):
```
03 18 00       TMPL tmSSINT(24), var=0
00             slot[0]: REC_END (empty)
01             LINE (content)
  ...
00             END content
0b             SIZE(SUB)
01             LINE (lower limit)
  02 88 30 00  0
00             END lower
01             LINE (upper limit)
  02 88 31 00  1
00             END upper
0d             SIZE(SYM)
02 86 2b 22    ∫ display
```

## Overbrace Pattern (tmUHBRACE, selector=0x1b=27)

```
03 1b 00       TMPL tmUHBRACE, var=0
00             slot[0]: REC_END (empty)
01             LINE (content)
  12 83 61 00  a
  12 83 62 00  b
  12 83 63 00  c
00             END content
0b             SIZE(SUB) — label follows
01             LINE (label)
  12 83 61 00  a (label text)
00             END label
0a             SIZE(FULL) — back to full size
02 96 37 fe    overbrace display glyph (U+FE37)
```

## Subscript/Superscript Pattern (tmSCRIPT, selector=0x0f=15)

### Superscript only (var=0):
```
03 0f 00       TMPL tmSCRIPT, var=0 (superscript)
00             slot[0]: REC_END (empty)
0b             SIZE(SUB)
11             null LINE
01             LINE (superscript content)
  02 88 32 00  2
00             END super
00             END slot[1]
```

### Both sub and super (var=2):
```
03 0f 02       TMPL tmSCRIPT, var=2 (both)
00             slot[0]: REC_END (empty — EQNEDT32 pattern)
0b             SIZE(SUB)
01             LINE (subscript content)
  12 83 69 00  i
00             END sub
01             LINE (superscript content)
  02 88 32 00  2
00             END super
00             END slot[1]
```

## Fraction Pattern (tmFRACT, selector=0x0e=14)

Fractions use standard slot structure (NOT empty slot[0]):
```
03 0e 00       TMPL tmFRACT, var=0
00             slot[0]: REC_END (EQNEDT32: empty)
01             LINE (numerator — packed in next structure)
  12 83 61 00  a
00             END numerator
01             LINE (denominator)
  12 83 62 00  b
00             END denominator
00             END
```

## Display Data Block Pattern

SIZE markers act as structural delimiters within EQNEDT32's packed slots:

```
SIZE(SUB=0x0b)  →  "subscript-level content follows" (limits, labels)
SIZE(SYM=0x0d)  →  "symbol-level content follows" (display glyphs)
SIZE(FULL=0x0a) →  "return to full size" (end of display data)
```

Typical sequence:
```
0b → LINE(lower) → LINE(upper) → 0d → CHAR(display) → [0a]
```
"""

# ================================================================
# 6. Verified MTEF Examples
# ================================================================

MTEF_EXAMPLES = r"""
# Verified MTEF<->LaTeX Examples

All examples below have been roundtrip-verified through EQNEDT32:
input MTEF → paste → copy → output MTEF (byte-identical).

## Basic: E = mc²
```
LaTeX: E = mc^{2}
Bytes: 03 01 01 03 0a 0a 01
       12 83 45 00           E (variable)
       02 86 3d 00           = (symbol)
       12 83 6d 00           m (variable)
       12 83 63 00           c (variable)
       03 0f 00              tmSCRIPT var=0 (superscript)
       00                    slot[0] empty
       0b 11 01              SIZE(SUB), null LINE, LINE
       02 88 32 00           2 (number)
       00 00 00 00           END markers
```

## Fraction: (a+b)/c
```
LaTeX: \dfrac{a + b}{c}
Bytes: 03 01 01 03 0a 0a 01
       03 0e 00              tmFRACT var=0
       00 01                 slot[0] END, LINE (numerator)
       12 83 61 00           a
       02 86 2b 00           +
       12 83 62 00           b
       00 01                 END num, LINE (denominator)
       12 83 63 00           c
       00 00 00 00           END markers
```

## Subscript+Superscript: x_i^2
```
LaTeX: x_{i}^{2}
Bytes: 03 01 01 03 0a 0a 01
       12 83 78 00           x
       03 0f 02              tmSCRIPT var=2 (both)
       00 0b 01              slot[0] END, SIZE(SUB), LINE (sub)
       12 83 69 00           i
       00 01                 END sub, LINE (super)
       02 88 32 00           2
       00 00 00 00           END markers
```

## Integral with no limits: ∫ a² dx
```
LaTeX: \int a^{2}dx
Bytes: 03 01 01 03 0a 0a 01
       03 15 00              tmSINT var=0 (no limits)
       00 01                 slot[0] END, LINE (integrand)
       12 83 61 00           a
       03 0f 00              tmSCRIPT var=0 (super)
       00 0b 11 01           slot[0] END, SIZE(SUB), null LINE, LINE
       02 88 32 00           2
       00 00 00              END markers for super+integrand
       11 11 0d              null LINE, null LINE, SIZE(SYM)
       02 86 2b 22           ∫ display (U+222B)
       00 0a                 END, SIZE(FULL)
       12 83 64 00           d
       12 83 78 00           x
       00 00                 END markers
```

## Fence: (∇×u)
```
LaTeX: \left( \nabla \times u \right)
Bytes: 03 01 01 03 0a 0a 01
       03 01 00              tmPAREN var=0
       00 01                 slot[0] END, LINE (content)
       02 86 d1 00           ∇ (nabla, symbol)
       02 86 b4 00           × (times, symbol)
       12 83 75 00           u (variable)
       00                    END content LINE
       02 96 28 00           ( display
       02 96 29 00           ) display
       00 00                 END markers
```

## NGSolve Eddy Current (141 bytes, inline_parens)
```
LaTeX: \int \nu (\nabla \times A) \cdot (\nabla \times N)d\Omega
       + j\omega \sigma \int A \cdot Nd\Omega = 0

NOTE: Uses inline_parens (char_function '(' ')') instead of tmpl_fence.
      tmpl_fence inside integral content LINE crashes EQNEDT32.

Bytes: 03 01 01 03 0a 0a 01
       03 15 00              tmSINT var=0
       00 01                 slot[0] END, content LINE start
       02 86 6e 00           ν (function font — inline_parens)
       02 82 28 00           ( (function font)
       02 86 d1 00           ∇
       02 86 b4 00           ×
       12 83 41 00           A
       02 82 29 00           ) (function font)
       02 86 c5 22           · (cdot)
       02 82 28 00           (
       02 86 d1 00           ∇
       02 86 b4 00           ×
       12 83 4e 00           N
       02 82 29 00           )
       12 83 64 00           d (trailing INSIDE content LINE)
       02 85 57 00           Ω
       00                    content LINE END
       0b 11 11 0d           SIZE(SUB), null, null, SIZE(SYM)
       02 86 2b 22           ∫ display
       00                    display area END
       0a                    SIZE(FULL) — between integrals
       02 86 2b 00           +
       12 83 6a 00           j
       02 86 77 00           ω
       02 86 73 00           σ
       03 15 00 00 01        tmSINT, slot[0] END, content LINE
       12 83 41 00           A
       02 86 c5 22           ·
       12 83 4e 00           N
       12 83 64 00           d
       02 85 57 00           Ω
       00                    content LINE END
       0b 11 11 0d           SIZE(SUB), null, null, SIZE(SYM)
       02 86 2b 22           ∫ display
       00 0a                 display END, SIZE(FULL) (more content follows)
       02 86 3d 00           =
       02 88 30 00           0
       00 00                 LINE END, TOP END
```

## NGSolve Eigenvalue (120 bytes, inline_parens)
```
LaTeX: \int (\nabla \times u) \cdot (\nabla \times v)d\Omega
       = \lambda \int u \cdot vd\Omega

NOTE: inline_parens + SIZE_FULL only between integrals.

Bytes: 03 01 01 03 0a 0a 01
       03 15 00 00 01        tmSINT, slot[0] END, content LINE
       02 82 28 00           ( (inline_parens)
       02 86 d1 00           ∇
       02 86 b4 00           ×
       12 83 75 00           u
       02 82 29 00           )
       02 86 c5 22           ·
       02 82 28 00           (
       02 86 d1 00           ∇
       02 86 b4 00           ×
       12 83 76 00           v
       02 82 29 00           )
       12 83 64 00           d (trailing INSIDE content LINE)
       02 85 57 00           Ω
       00                    content LINE END
       0b 11 11 0d           SIZE(SUB), null, null, SIZE(SYM)
       02 86 2b 22           ∫ display
       00                    display END
       0a                    SIZE(FULL) — between integrals
       02 86 3d 00           =
       02 86 6c 00           λ
       03 15 00 00 01        tmSINT, slot[0] END, content LINE
       12 83 75 00           u
       02 86 c5 22           ·
       12 83 76 00           v
       12 83 64 00           d
       02 85 57 00           Ω
       00                    content LINE END
       0b 11 11 0d           SIZE(SUB), null, null, SIZE(SYM)
       02 86 2b 22           ∫ display
       00                    display END (NO SIZE_FULL after last!)
       00 00                 LINE END, TOP END
```

## Summation: Σ_{i=1}^{n} a_i
```
LaTeX: \sum _{i = 1}^{n}a_{i}
Bytes: 03 01 01 03 0a 0a 01
       02 86 e5 00           Σ (char, symbol font 0xE5)
       03 0f 02              tmSCRIPT var=2 (both)
       00 0b 01              slot[0] END, SIZE(SUB), LINE (sub)
       12 83 69 00           i
       02 86 3d 00           =
       02 88 31 00           1
       00 01                 END sub, LINE (super)
       12 83 6e 00           n
       00 00                 END super+script
       12 83 61 00           a
       03 0f 01              tmSCRIPT var=1 (subscript only)
       00 0b 01              slot[0] END, SIZE(SUB), LINE
       12 83 69 00           i
       00                    END sub
       11 00 00 00           null LINE, END markers
```

## Overbrace: overbrace{abc}^{a}
```
LaTeX: \overbrace{abc}^{a}
Bytes: 03 1b 00              tmUHBRACE var=0
       00 01                 slot[0] END, LINE (content)
       12 83 61 00           a
       12 83 62 00           b
       12 83 63 00           c
       00                    END content
       0b 01                 SIZE(SUB), LINE (label)
       12 83 61 00           a (label)
       00 0a                 END label, SIZE(FULL)
       02 96 37 fe           overbrace display (U+FE37)
```

## Exterior Calculus: F = E dx∧dt + B dy∧dz (Faraday 2-form)
```
LaTeX: F = Edx\wedge dt + Bdy\wedge dz
Bytes: 03 01 01 03 0a        header
       0a 01                 SIZE_FULL, LINE
       12 83 46 00           F
       02 86 3d 00           =
       12 83 45 00           E
       12 83 64 00           d
       12 83 78 00           x
       02 86 d9 00           ∧ (wedge, symbol 0xD9)
       12 83 64 00           d
       12 83 74 00           t
       02 86 2b 00           +
       12 83 42 00           B
       12 83 64 00           d
       12 83 79 00           y
       02 86 d9 00           ∧ (wedge)
       12 83 64 00           d
       12 83 7a 00           z
       00 00                 LINE END, TOP END
```

## Exterior Calculus: dF = 0 (Maxwell compact)
```
LaTeX: dF = 0
Bytes: 03 01 01 03 0a 0a 01
       12 83 64 00           d
       12 83 46 00           F
       02 86 3d 00           =
       02 88 30 00           0
       00 00
```

## Exterior Calculus: *d*F = J (Maxwell Hodge form)
```
LaTeX: *d*F = J
Bytes: 03 01 01 03 0a 0a 01
       02 82 2a 00           * (Hodge star, function font)
       12 83 64 00           d
       02 82 2a 00           * (Hodge star)
       12 83 46 00           F
       02 86 3d 00           =
       12 83 4a 00           J
       00 00
```

## Helmholtz Weak Form (141 bytes)
```
LaTeX: \int \nabla u \cdot \nabla vd\Omega - k^{2}\int uvd\Omega = \int fvd\Omega
NOTE: 3 integrals, SIZE_FULL between each, k² coefficient before 2nd integral.
```

## Time-Harmonic Maxwell (202 bytes)
```
LaTeX: \int \dfrac{1}{\mu}(\nabla\times E)\cdot(\nabla\times F)d\Omega
       - \omega^{2}\varepsilon \int E\cdot Fd\Omega = j\omega \int J\cdot Fd\Omega
NOTE: Fraction 1/μ inside integral, inline_parens for (∇×E) and (∇×F).
      3 integrals with SIZE_FULL between them.
```

## Closed Integral: ∫ dω = ∮ ω (Generalized Stokes theorem)
```
LaTeX: \int d\omega  = \oint \omega
Bytes: ...(header)...
       03 15 00 00           tmSINT var=0 (∫)
       01 12 83 64 00        LINE: d
       02 86 77 00           ω (symbol 0x77)
       00                    END content
       0b 11 11 0d 02 86 2b 22 00  display data
       0a                    SIZE_FULL (between integrals)
       02 86 3d 00           =
       03 15 03 00           tmSINT var=3 (∮)  ← variation=3 gives ∮
       01 02 86 77 00        LINE: ω
       00                    END content
       0b 11 11 0d 02 86 2b 22 00  display data
       00 00                 LINE END, TOP END
```

## EM Basics: J = σE (Ohm's law)
```
LaTeX: J = \sigma E
Bytes: 03 01 01 03 0a 0a 01
       12 83 4a 00           J
       02 86 3d 00           =
       12 83 c3 03           σ (Greek lc, U+03C3)
       12 83 45 00           E
       00 00
```

## EM Basics: F = q(E + v × B) (Lorentz force)
```
LaTeX: F = q(E + v \times B)
Bytes: 03 01 01 03 0a 0a 01
       12 83 46 00           F
       02 86 3d 00           =
       12 83 71 00           q
       02 82 28 00           ( (inline_parens)
       12 83 45 00           E
       02 86 2b 00           +
       12 83 76 00           v
       02 86 d7 00           × (times)
       12 83 42 00           B
       02 82 29 00           )
       00 00
```

## EM Basics: S = E × H (Poynting vector)
```
LaTeX: S = E \times H
Bytes: 03 01 01 03 0a 0a 01
       12 83 53 00  S    02 86 3d 00  =
       12 83 45 00  E    02 86 d7 00  ×    12 83 48 00  H
       00 00
```

## EM Basics: ∇·J + ∂ρ/∂t = 0 (continuity equation)
```
LaTeX: \nabla  \cdot J + \dfrac{\partial \rho }{\partial t} = 0
Bytes: 03 01 01 03 0a 0a 01
       02 86 07 22           ∇ (U+2207)
       02 86 c5 22           · (cdot, U+22C5)
       12 83 4a 00           J
       02 86 2b 00           +
       03 0e 00 00 01        tmFRACT, slot[0] END, LINE (numer)
       02 86 02 22           ∂ (U+2202)
       12 83 c1 03           ρ (U+03C1)
       00 01                 END numer, LINE (denom)
       02 86 02 22           ∂
       12 83 74 00           t
       00 00                 END denom+frac
       02 86 3d 00           =
       02 88 30 00           0
       00 00
```

## EM Basics: W = ½∫B·HdΩ (magnetic energy)
```
LaTeX: W = \dfrac{1}{2}\int B \cdot Hd\Omega
Bytes: 03 01 01 03 0a 0a 01
       12 83 57 00  W    02 86 3d 00  =
       03 0e 00 00 01 02 88 31 00 00 01 02 88 32 00 00 00  frac 1/2
       03 15 00 00 01        tmSINT, content LINE
       12 83 42 00  B    02 86 c5 22  ·    12 83 48 00  H
       12 83 64 00  d    02 83 a9 03  Ω
       00 11 11 0d 02 86 2b 22 00  display data
       00 00
```

## EM Basics: ν = 1/(μ₀μᵣ) (reluctivity)
```
LaTeX: \nu  = \dfrac{1}{\mu _{0}\mu _{r}}
Bytes: 03 01 01 03 0a 0a 01
       12 83 bd 03  ν    02 86 3d 00  =
       03 0e 00 00 01 02 88 31 00  frac numer: 1
       00 01                       denom:
       12 83 bc 03                 μ
       03 0f 01 00 01 02 88 30 00 00 11 00  subscript: 0
       12 83 bc 03                 μ
       03 0f 01 00 01 12 83 72 00 00 11 00  subscript: r
       00 00 00 00
```

## Gao Iron Loss: b = B_max sin ωt (eq.1)
```
LaTeX: b = B_{\max}\sin\omega t
NOTE: TF_FUNCTION chars (typeface 0x82) grouped into LaTeX functions.
Bytes: 03 01 01 03 0a 0a 01
       12 83 62 00           b
       02 86 3d 00           =
       12 83 42 00           B
       03 0f 01 00 01        tmSCRIPT sub (B_{max})
       02 82 6d 00 02 82 61 00 02 82 78 00  max (function)
       00 11 00              END
       02 82 73 00 02 82 69 00 02 82 6e 00  sin (function)
       12 83 c9 03           ω (U+03C9)
       12 83 74 00           t
       00 00
```

## Gao Iron Loss: h = (a₁+a₃b²+⋯)db/dt + (c₁+c₃b²+⋯)b (eq.4)
```
LaTeX: h = (a_{1} + a_{3}b^{2} + a_{5}b^{4} + \cdots )\dfrac{db}{dt}
       + (c_{1} + c_{3}b^{2} + c_{5}b^{4} + \cdots )b
NOTE: \cdots encoded as THREE consecutive \cdot (U+22C5) chars.
      eq2tex post-processing merges triple \cdot into \cdots.
      274 bytes total.
```

## Gao Iron Loss: ∮HdB = Σ B_{imax} iπ H_{imax} sin(φᵢ-αᵢ) (eq.8)
```
LaTeX: \oint HdB= \sum B_{i\max}i\pi H_{i\max}\sin(\phi _{i} - \alpha _{i})
NOTE: ∮ = tmSINT var=3. Σ = char_symbol(0x2211).
      164 bytes total.
```

## Gao Iron Loss: W_iron = f·Σ.../ρ (eq.9)
```
LaTeX: W_{\operatorname{iron}} = \dfrac{f\sum B_{i\max}i\pi H_{i\max}
       \sin(\phi _{i} - \alpha _{i})}{\rho }
NOTE: W subscript function chars 'iron' → \operatorname{iron}.
      182 bytes total.
```

## Gao Iron Loss: W_iron basic calculation (eq.12)
```
LaTeX: W_{\operatorname{iron}} = \dfrac{\dfrac{1}{2}a_{1,50Hz}\omega^{2}
       B_{1\max}^{2} + 2a_{1,50Hz}\omega^{2}B_{2\max}^{2} + \cdots}{\rho}
NOTE: Nested fraction inside outer fraction numerator.
      279 bytes total.
```
"""

# ================================================================
# 7. MTEF Builder Recipes
# ================================================================

MTEF_BUILDER = r"""
# MTEF Builder Recipes

Python functions for constructing valid MTEF binary from components.

## Header
```python
def mtef_header():
    return bytes([0x03, 0x01, 0x01, 0x03, 0x0a])
```

## Characters
```python
def char_variable(code):
    # Italic variable. code = ord('a')..ord('z'), ord('A')..ord('Z')
    return bytes([0x12, 0x83, code & 0xFF, (code >> 8) & 0xFF])

def char_number(code):
    # Digit. code = ord('0')..ord('9')
    return bytes([0x02, 0x88, code & 0xFF, (code >> 8) & 0xFF])

def char_symbol(code):
    # Math symbol. code = ASCII or Unicode (2-byte LE).
    return bytes([0x02, 0x86, code & 0xFF, (code >> 8) & 0xFF])

def char_greek_lc(code):
    # Lowercase Greek. code from Symbol font position.
    return bytes([0x02, 0x84, code & 0xFF, (code >> 8) & 0xFF])

def char_greek_uc(code):
    # Uppercase Greek. code from Symbol font position.
    return bytes([0x02, 0x85, code & 0xFF, (code >> 8) & 0xFF])

def char_text(code):
    # Roman text character.
    return bytes([0x02, 0x81, code & 0xFF, (code >> 8) & 0xFF])

def char_function(code):
    # Function font character (non-italic parentheses etc.).
    return bytes([0x02, 0x82, code & 0xFF, (code >> 8) & 0xFF])

def char_display(code):
    # Display character (fence/bigop glyphs, typeface=22).
    return bytes([0x02, 0x96, code & 0xFF, (code >> 8) & 0xFF])
```

## Common Symbols
```python
SYM_PLUS     = char_symbol(0x2b)       # +
SYM_MINUS    = char_symbol(0x2d)       # -
SYM_EQUALS   = char_symbol(0x3d)       # =
SYM_TIMES    = char_symbol(0xb4)       # ×
SYM_CDOT     = char_symbol(0x22c5)     # · (U+22C5)
SYM_NABLA    = char_symbol(0xd1)       # ∇
SYM_PARTIAL  = char_symbol(0xb6)       # ∂
SYM_OMEGA_SYM = char_symbol(0x77)      # ω (in symbol font)
SYM_SIGMA_SYM = char_symbol(0x73)      # σ
SYM_NU_SYM   = char_symbol(0x6e)       # ν
SYM_LAMBDA_SYM = char_symbol(0x6c)     # λ
SYM_WEDGE    = char_symbol(0xd9)       # ∧ (wedge product)
SYM_RHO_SYM  = char_symbol(0x72)      # ρ
SYM_EPSILON_SYM = char_symbol(0x65)    # ε
SYM_ALPHA_SYM = char_symbol(0x61)     # α
SYM_OMEGA_LC = char_symbol(0x77)       # ω (lowercase)
OMEGA_UC     = char_greek_uc(0x57)     # Ω (uppercase Greek)
GAMMA_UC     = char_greek_uc(0x47)     # Γ (uppercase Greek)
INTEGRAL_DISP = char_display(0x222b)   # ∫ display glyph
```

## Structural Helpers
```python
END = b'\x00'
LINE = b'\x01'
NULL_LINE = b'\x11'
SIZE_FULL = b'\x0a'
SIZE_SUB = b'\x0b'
SIZE_SYM = b'\x0d'

def tmpl_frac(numerator, denominator):
    # \\dfrac{num}{den}
    return (b'\x03\x0e\x00'      # TMPL tmFRACT var=0
            + END + LINE          # slot[0] END, LINE (num)
            + numerator
            + END + LINE          # END num, LINE (den)
            + denominator
            + END + END)          # END den, END tmpl

def tmpl_sup(content):
    # Superscript: ^{content}
    return (b'\x03\x0f\x00'      # TMPL tmSCRIPT var=0
            + END                 # slot[0] empty
            + SIZE_SUB + NULL_LINE + LINE
            + content
            + END + END)

def tmpl_sub(content):
    # Subscript: _{content}
    return (b'\x03\x0f\x01'      # TMPL tmSCRIPT var=1
            + END                 # slot[0] empty
            + SIZE_SUB + LINE
            + content
            + END
            + NULL_LINE + END)

def tmpl_subsup(sub_content, sup_content):
    # _{sub}^{sup}
    return (b'\x03\x0f\x02'      # TMPL tmSCRIPT var=2
            + END                 # slot[0] empty
            + SIZE_SUB + LINE
            + sub_content
            + END + LINE
            + sup_content
            + END + END)

def tmpl_fence_paren(content):
    # \\left( content \\right)
    return (b'\x03\x01\x00'      # TMPL tmPAREN var=0
            + END + LINE         # slot[0] END, content LINE
            + content
            + END                # END content
            + char_display(0x28) # ( display
            + char_display(0x29))# ) display

def inline_parens(content):
    # Parentheses using FUNCTION font chars instead of tmpl_fence.
    # EQNEDT32 crashes when tmpl_fence is inside an integral's content LINE.
    return char_function(ord('(')) + content + char_function(ord(')'))

def tmpl_integral_nolimits(integrand, trailing=b''):
    # \\int integrand [trailing, e.g. dΩ]
    # IMPORTANT: trailing goes INSIDE the content LINE (EQNEDT32 native format).
    # SIZE_SUB precedes the display data area.
    # Does NOT append SIZE_FULL — caller must add SIZE_FULL between integrals.
    return (b'\x03\x15\x00'      # TMPL tmSINT var=0
            + END + LINE         # slot[0] END, content LINE start
            + integrand
            + trailing           # trailing (dΩ etc.) inside content LINE
            + END                # content LINE end
            + SIZE_SUB           # precedes display data area
            + NULL_LINE + NULL_LINE + SIZE_SYM
            + char_symbol(0x222b)  # ∫ display
            + END)               # display area end (NO SIZE_FULL)

def tmpl_oint_nolimits(integrand, trailing=b''):
    # \\oint integrand [trailing]
    # Same as tmpl_integral_nolimits but variation=3 for ∮ (closed integral).
    return (b'\x03\x15\x03'      # TMPL tmSINT var=3 → ∮
            + END + LINE
            + integrand
            + trailing
            + END
            + SIZE_SUB
            + NULL_LINE + NULL_LINE + SIZE_SYM
            + char_symbol(0x222b)
            + END)

def tmpl_overbrace(content, label):
    # \\overbrace{content}^{label}
    return (b'\x03\x1b\x00'      # TMPL tmUHBRACE var=0
            + END + LINE         # slot[0] END, content LINE
            + content
            + END                # END content
            + SIZE_SUB + LINE    # label
            + label
            + END + SIZE_FULL    # END label
            + char_display(0xfe37))  # overbrace glyph

def build_equation(*parts):
    # Build complete MTEF: header + SIZE_FULL + LINE + parts + LINE_END + TOP_END.
    # For multi-integral equations, add SIZE_FULL between integrals in parts.
    return mtef_header() + SIZE_FULL + LINE + b''.join(parts) + END + END
```

## Complete Example: Building ∫(∇×u)·(∇×v)dΩ = λ∫u·vdΩ

```python
# Use inline_parens (NOT tmpl_fence_paren) for parentheses inside integrals.
# tmpl_fence inside integral's content LINE crashes EQNEDT32.
nabla_cross_u = (char_symbol(0xd1)       # ∇
                + char_symbol(0xb4)       # ×
                + char_variable(ord('u')))

nabla_cross_v = (char_symbol(0xd1)       # ∇
                + char_symbol(0xb4)       # ×
                + char_variable(ord('v')))

paren_ncu = inline_parens(nabla_cross_u)  # (∇×u) — uses char_function
paren_ncv = inline_parens(nabla_cross_v)  # (∇×v) — uses char_function

integrand1 = paren_ncu + char_symbol(0x22c5) + paren_ncv  # (∇×u)·(∇×v)

d_omega = char_variable(ord('d')) + char_greek_uc(0x57)    # dΩ

int1 = tmpl_integral_nolimits(integrand1, d_omega)

integrand2 = (char_variable(ord('u'))
             + char_symbol(0x22c5)
             + char_variable(ord('v')))

int2 = tmpl_integral_nolimits(integrand2, d_omega)

eq = build_equation(
    int1,                           # ∫(∇×u)·(∇×v)dΩ
    SIZE_FULL,                      # restore size between integrals
    char_symbol(0x3d),              # =
    char_symbol(0x6c),              # λ
    int2                            # ∫u·vdΩ
)
# Result: 120 bytes, roundtrip-verified ✓
```

## TF_FUNCTION Grouping (typeface 0x82)

Consecutive CHAR records with typeface 0x82 (FUNCTION) are grouped by eq2tex
into LaTeX function commands:

```python
# Building \sin, \cos, \max, \lim, etc.
# Use char_function for each letter:
sin_chars = char_function(ord('s')) + char_function(ord('i')) + char_function(ord('n'))
# Bytes: 02 82 73 00  02 82 69 00  02 82 6e 00
# eq2tex groups these into: \sin

# Known function names: sin, cos, tan, cot, sec, csc,
#   sinh, cosh, tanh, coth, sech, csch,
#   log, ln, exp, lim, max, min, sup, inf, det, dim, ker, deg, arg, Re, Im

# Unknown sequences become \operatorname{...}:
iron_chars = (char_function(ord('i')) + char_function(ord('r'))
             + char_function(ord('o')) + char_function(ord('n')))
# eq2tex produces: \operatorname{iron}

# Parentheses in FUNCTION font are NOT grouped — they remain literal:
char_function(ord('('))  → standalone ( character
```

## Triple-Cdot Recipe (\cdots)

EQNEDT32 has no visible glyph for U+22EF (⋯) or Symbol font 0xBC.
To display ellipsis, use three consecutive U+22C5 (⋅) characters:

```python
# Three cdot chars → visible ⋅⋅⋅ in EQNEDT32
cdots = char_symbol(0x22c5) + char_symbol(0x22c5) + char_symbol(0x22c5)
# Bytes: 02 86 c5 22  02 86 c5 22  02 86 c5 22

# eq2tex post-processing merges " \cdot  \cdot  \cdot " → "\cdots "
# So the LaTeX output is clean: a_{1} + a_{3}b^{2} + \cdots
```

### Key Rules for Multi-Integral Equations

1. **SIZE_FULL between integrals**: Add `SIZE_FULL` after each integral's display
   data END, EXCEPT the last integral. The last integral should NOT have SIZE_FULL
   after it — just let `build_equation` add the final END markers.

2. **Parentheses inside integrals**: Use `inline_parens()` (char_function font),
   NOT `tmpl_fence_paren()`. Fence templates with display chars (typeface 0x96)
   inside an integral's content LINE crash EQNEDT32 during paste.

3. **Trailing content inside content LINE**: `dΩ`, `dx`, etc. go INSIDE the
   integral's content LINE, before the content LINE END.
"""

# ================================================================
# 8. Known Limitations
# ================================================================

MTEF_LIMITATIONS = """
# Known EQNEDT32 Limitations

## Templates that crash EQNEDT32

When pasted via "DS Equation" clipboard format:
- **tmSUM (29)** / **tmPROD (31)** templates crash EQNEDT32.
  Workaround: use char_symbol(0xE5) for Σ, char_symbol(0xD5) for Π
  combined with tmSCRIPT for sub/superscript limits.
- **tmROOT (13)** crashes are unresolved — avoid for now.
- **tmpl_fence inside integral content LINE** crashes EQNEDT32 during paste.
  Any fence template (tmPAREN, tmBRACK, etc.) with display chars (typeface 0x96)
  placed inside an integral's content LINE causes a crash. Workaround: use
  `inline_parens()` which uses char_function font parentheses instead of
  fence templates. Produces `(...)` instead of `\\left(...)\\right)`.

## Multi-integral SIZE_FULL rule

When an equation has multiple integrals, SIZE_FULL (0x0a) must appear between
integrals to restore the font size after each integral's display data area.
However, SIZE_FULL must NOT appear after the LAST integral — only between them.
Incorrect placement causes "elements not available" error dialog.

## Content accumulation

If Select All + Paste fails to replace existing content, equations
accumulate until "This equation is the maximum size allowed" dialog.
Recovery: restart EQNEDT32 (taskkill + relaunch).

## OLE clipboard async

Copy uses PostMessageW (async). Must wait 2-3 seconds for OLE to
render clipboard data before reading.

## Foreground window hook

CF_UNICODETEXT (LaTeX) is only placed on clipboard when the foreground
window is NOT an Office application. The WinEventHook in eq2tex_hook.dll
monitors foreground changes.

## Character encoding variants

Same mathematical symbol can be encoded multiple ways:
- ∇: `02 86 d1 00` (Symbol 0xD1) or `02 86 07 22` (Unicode U+2207)
- Ω: `02 85 57 00` (UC_GREEK 'W') or `02 85 a9 03` (Unicode U+03A9)
- ·: `02 86 c5 00` (Symbol 0xC5) or `02 86 c5 22` (Unicode U+22C5)
- λ: `02 86 6c 00` (Symbol 'l') or `02 84 bb 03` (Unicode U+03BB)

All variants are accepted by EQNEDT32. The Symbol font positions
are more compact; Unicode codes are more explicit.
"""

# ================================================================
# API
# ================================================================

def get_mtef_documentation(topic: str = "all") -> str:
    """Return MTEF format documentation by topic."""
    topics = {
        "header": MTEF_HEADER,
        "records": MTEF_RECORD_TAGS,
        "chars": MTEF_CHAR_RECORDS,
        "templates": MTEF_TEMPLATES,
        "patterns": MTEF_EQNEDT32_PATTERNS,
        "examples": MTEF_EXAMPLES,
        "builder": MTEF_BUILDER,
        "limitations": MTEF_LIMITATIONS,
    }

    topic = topic.lower().strip()
    if topic == "all":
        return "\n\n".join(topics.values())
    elif topic in topics:
        return topics[topic]
    else:
        return (
            f"Unknown topic: '{topic}'. "
            f"Available: all, {', '.join(topics.keys())}"
        )
