"""
EQNEDT32 / MTEF MCP Server

Provides tools for:
- MTEF binary format documentation (8 topics)
- MTEF hex → annotated breakdown
- LaTeX → MTEF builder recipes

Usage:
    mcp-server-eqnedt32             # Start MCP server (stdio transport)
"""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .mtef_knowledge import get_mtef_documentation

mcp = FastMCP("eqnedt32-mtef")


@mcp.tool()
def mtef_documentation(topic: str = "all") -> str:
    """
    Get MTEF binary format documentation.

    Topics:
    - header: MTEF stream header (5-byte format)
    - records: Record tag byte format and types
    - chars: CHAR record encoding, typefaces, character codes
    - templates: Template selectors, variations, slot counts
    - patterns: EQNEDT32-specific encoding patterns
    - examples: Verified MTEF<->LaTeX examples with hex dumps
    - builder: Python MTEF builder recipes and helper functions
    - limitations: Known EQNEDT32 crashes and workarounds
    - all: Everything
    """
    return get_mtef_documentation(topic)


@mcp.tool()
def annotate_mtef_hex(hex_string: str) -> str:
    """
    Annotate an MTEF hex dump with record-by-record breakdown.

    Input: space-separated hex bytes (e.g. "03 01 01 03 0a 12 83 61 00")
    Output: annotated breakdown showing record types, fonts, characters.
    """
    try:
        data = bytes.fromhex(hex_string.replace(' ', ''))
    except ValueError as e:
        return f"Invalid hex: {e}"

    lines = []
    i = 0

    # Font names
    FONTS = {
        0x81: "TEXT", 0x82: "FUNCTION", 0x83: "VARIABLE",
        0x84: "LC_GREEK", 0x85: "UC_GREEK", 0x86: "SYMBOL",
        0x87: "VECTOR", 0x88: "NUMBER", 0x96: "DISPLAY",
    }

    # Template names
    TMPLS = {
        0: "tmANGLE", 1: "tmPAREN", 2: "tmBRACE", 3: "tmBRACK",
        4: "tmBAR", 5: "tmDBAR", 6: "tmFLOOR", 7: "tmCEIL",
        13: "tmROOT", 14: "tmFRACT", 15: "tmSCRIPT",
        16: "tmUBAR", 17: "tmOBAR",
        21: "tmSINT", 22: "tmDINT", 23: "tmTINT",
        24: "tmSSINT", 25: "tmDSINT", 26: "tmTSINT",
        27: "tmUHBRACE", 28: "tmLHBRACE",
        29: "tmSUM", 30: "tmISUM", 31: "tmPROD",
        39: "tmLIM", 41: "tmSLFRACT", 44: "tmLSCRIPT",
        45: "tmDIRAC", 48: "tmOARC",
    }

    # Well-known symbol codes
    SYMBOLS = {
        0x2b: '+', 0x2d: '-', 0x3d: '=', 0xb4: 'times',
        0xd1: 'nabla', 0xb6: 'partial', 0x6e: 'nu', 0x73: 'sigma',
        0x77: 'omega', 0x6c: 'lambda', 0xe5: 'Sigma(char)',
        0xc5: 'cdot', 0x07: 'nabla(alt)',
        0x22c5: 'cdot', 0x222b: 'integral', 0x2295: 'oplus',
        0x2229: 'cap', 0x222a: 'cup', 0x2207: 'nabla(U)',
    }

    def hexb(start, count):
        return ' '.join(f'{data[start+j]:02x}' for j in range(count))

    # Header
    if len(data) >= 5 and data[0] <= 5:
        lines.append(f"  {hexb(0,5)}  HEADER ver={data[0]} "
                      f"plat={data[1]} prod={data[2]} "
                      f"pv={data[3]} sv={data[4]}")
        i = 5

    while i < len(data):
        tag = data[i]
        rec_type = tag & 0x0f
        options = (tag >> 4) & 0x0f

        if rec_type == 0:  # END
            lines.append(f"  {hexb(i,1)}           END")
            i += 1
        elif rec_type == 1:  # LINE
            if options & 0x01:
                lines.append(f"  {hexb(i,1)}           null LINE")
            else:
                lines.append(f"  {hexb(i,1)}           LINE")
            i += 1
        elif rec_type == 2:  # CHAR
            if i + 3 < len(data):
                tf = data[i+1]
                code = data[i+2] | (data[i+3] << 8)
                font_name = FONTS.get(tf, f"tf={tf}")
                # Try to identify the character
                char_str = ""
                if tf == 0x83:  # VARIABLE
                    char_str = chr(code) if 0x20 <= code < 0x7f else f"U+{code:04X}"
                elif tf == 0x88:  # NUMBER
                    char_str = chr(code) if 0x30 <= code <= 0x39 else f"U+{code:04X}"
                elif tf == 0x86:  # SYMBOL
                    char_str = SYMBOLS.get(code, f"0x{code:04X}")
                elif tf == 0x84:  # LC_GREEK
                    char_str = f"greek_lc(0x{code:04X})"
                elif tf == 0x85:  # UC_GREEK
                    if code == 0x57:
                        char_str = "Ω"
                    else:
                        char_str = f"greek_uc(0x{code:04X})"
                elif tf == 0x81:  # TEXT
                    char_str = chr(code) if 0x20 <= code < 0x7f else f"U+{code:04X}"
                elif tf == 0x82:  # FUNCTION
                    char_str = chr(code) if 0x20 <= code < 0x7f else f"U+{code:04X}"
                elif tf == 0x96:  # DISPLAY
                    char_str = f"display(0x{code:04X})"
                else:
                    char_str = f"code=0x{code:04X}"
                opt_str = " [TEXT]" if options & 0x01 else ""
                lines.append(f"  {hexb(i,4)}      CHAR {font_name} "
                              f"'{char_str}'{opt_str}")
                i += 4
            else:
                lines.append(f"  {hexb(i,1)}           CHAR (truncated)")
                i += 1
        elif rec_type == 3:  # TMPL
            if i + 2 < len(data):
                sel = data[i+1]
                var = data[i+2]
                tmpl_name = TMPLS.get(sel, f"sel={sel}")
                lines.append(f"  {hexb(i,3)}        TMPL {tmpl_name} var={var}")
                i += 3
            else:
                lines.append(f"  {hexb(i,1)}           TMPL (truncated)")
                i += 1
        elif rec_type == 4:  # PILE
            lines.append(f"  {hexb(i,1)}           PILE")
            i += 1
        elif rec_type == 5:  # MATRIX
            lines.append(f"  {hexb(i,1)}           MATRIX")
            i += 1
        elif rec_type == 6:  # EMBELL
            if i + 1 < len(data):
                emb = data[i+1]
                lines.append(f"  {hexb(i,2)}        EMBELL type={emb}")
                i += 2
            else:
                i += 1
        elif rec_type in (10, 11, 12, 13, 14):  # SIZE markers
            names = {10: "FULL", 11: "SUB", 12: "SUB2", 13: "SYM", 14: "SUBSYM"}
            lines.append(f"  {hexb(i,1)}           SIZE({names[rec_type]})")
            i += 1
        else:
            lines.append(f"  {hexb(i,1)}           unknown(type={rec_type})")
            i += 1

    return '\n'.join(lines)


def main():
    """Run MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
