"""
Lint rules for GMSH mesh generation Python scripts.

Each rule function receives (filepath, lines) and returns a list of findings.
A finding is a dict with keys: line, severity, rule, message.
"""

import re
from typing import List, Dict


def check_missing_gmsh_initialize(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: Script imports gmsh but does not call gmsh.initialize()."""
    findings = []
    has_import = any(
        re.search(r'^\s*import\s+gmsh\b', line)
        for line in lines
    )
    if not has_import:
        return findings

    has_init = any('gmsh.initialize' in line for line in lines)
    if not has_init:
        findings.append({
            'line': 1,
            'severity': 'CRITICAL',
            'rule': 'missing-gmsh-initialize',
            'message': (
                'Script imports gmsh but does not call gmsh.initialize(). '
                'Add gmsh.initialize() before any GMSH API calls.'
            ),
        })
    return findings


def check_missing_gmsh_finalize(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: Script calls gmsh.initialize() but no gmsh.finalize()."""
    findings = []
    has_init = any('gmsh.initialize' in line for line in lines)
    if not has_init:
        return findings

    has_finalize = any('gmsh.finalize' in line for line in lines)
    if not has_finalize:
        # Find the last line for reporting
        last_line = len(lines)
        findings.append({
            'line': last_line,
            'severity': 'HIGH',
            'rule': 'missing-gmsh-finalize',
            'message': (
                'gmsh.initialize() called but no gmsh.finalize() found. '
                'Add gmsh.finalize() at end of script to release resources.'
            ),
        })
    return findings


def check_missing_synchronize(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: Meshing or physical group ops without prior synchronize()."""
    findings = []
    # Operations that require synchronize() to have been called
    needs_sync_pattern = re.compile(
        r'gmsh\.model\.(?:mesh\.generate|addPhysicalGroup|setPhysicalName)\s*\('
    )
    sync_pattern = re.compile(
        r'gmsh\.model\.(?:geo|occ)\.synchronize\s*\('
    )
    # Also accept gmsh.model.mesh.generate after gmsh.open/gmsh.merge (no sync needed)
    file_load_pattern = re.compile(
        r'gmsh\.(?:open|merge)\s*\('
    )

    has_geo_or_occ = any(
        re.search(r'gmsh\.model\.(?:geo|occ)\.', line)
        for line in lines
        if not line.strip().startswith('#')
    )
    if not has_geo_or_occ:
        return findings

    has_sync = any(
        sync_pattern.search(line)
        for line in lines
        if not line.strip().startswith('#')
    )
    has_needs_sync = any(
        needs_sync_pattern.search(line)
        for line in lines
        if not line.strip().startswith('#')
    )

    if has_needs_sync and not has_sync:
        # Find the first line that needs sync
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if needs_sync_pattern.search(stripped):
                findings.append({
                    'line': i,
                    'severity': 'CRITICAL',
                    'rule': 'missing-synchronize',
                    'message': (
                        'geo/occ operations found but no synchronize() call. '
                        'Add gmsh.model.geo.synchronize() or '
                        'gmsh.model.occ.synchronize() before meshing or '
                        'physical group assignment.'
                    ),
                })
                break
    return findings


def check_wrong_generate_dimension(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: generate(2) for volume mesh or generate(3) for surface-only."""
    findings = []
    generate_pattern = re.compile(r'gmsh\.model\.mesh\.generate\s*\(\s*(\d)\s*\)')

    # Check for volume geometry creation (suggests 3D mesh needed)
    has_volume = any(
        re.search(r'gmsh\.model\.(?:geo|occ)\.(?:addVolume|addBox|addSphere|addCylinder|addCone|addTorus|addWedge|extrude)\s*\(', line)
        for line in lines
        if not line.strip().startswith('#')
    )

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        match = generate_pattern.search(stripped)
        if match:
            dim = int(match.group(1))
            if dim == 2 and has_volume:
                findings.append({
                    'line': i,
                    'severity': 'HIGH',
                    'rule': 'wrong-generate-dimension',
                    'message': (
                        'generate(2) called but volume geometry detected. '
                        'Use gmsh.model.mesh.generate(3) for volume meshes. '
                        'Use generate(2) only for surface-only (PEEC/BEM) meshes.'
                    ),
                })
    return findings


def check_missing_physical_groups(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: Mesh generated and written but no addPhysicalGroup()."""
    findings = []
    has_generate = any(
        'mesh.generate' in line
        for line in lines
        if not line.strip().startswith('#')
    )
    has_write = any(
        re.search(r'gmsh\.write\s*\(', line)
        for line in lines
        if not line.strip().startswith('#')
    )
    has_physical = any(
        'addPhysicalGroup' in line
        for line in lines
        if not line.strip().startswith('#')
    )

    if has_generate and has_write and not has_physical:
        write_line = 1
        for i, line in enumerate(lines, 1):
            if re.search(r'gmsh\.write\s*\(', line):
                write_line = i
                break
        findings.append({
            'line': write_line,
            'severity': 'HIGH',
            'rule': 'missing-physical-groups',
            'message': (
                'Mesh generated and written but no addPhysicalGroup() found. '
                'Physical groups are required for NGSolve/Radia material '
                'assignment. Add: gmsh.model.addPhysicalGroup(3, [vol_tag])'
            ),
        })
    return findings


def check_mixing_geo_and_occ(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: Both gmsh.model.geo.* and gmsh.model.occ.* in same script."""
    findings = []
    geo_pattern = re.compile(r'gmsh\.model\.geo\.(?:add|extrude|revolve|synchronize)')
    occ_pattern = re.compile(r'gmsh\.model\.occ\.(?:add|fuse|cut|intersect|fragment|import|translate|rotate|dilate|mirror|copy|extrude|revolve|synchronize)')

    geo_line = None
    occ_line = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if geo_pattern.search(stripped) and geo_line is None:
            geo_line = i
        if occ_pattern.search(stripped) and occ_line is None:
            occ_line = i

    if geo_line is not None and occ_line is not None:
        later_line = max(geo_line, occ_line)
        findings.append({
            'line': later_line,
            'severity': 'CRITICAL',
            'rule': 'mixing-geo-and-occ',
            'message': (
                'Both gmsh.model.geo.* and gmsh.model.occ.* APIs used in '
                'the same script. GMSH requires using a single CAD kernel. '
                'Use geo (built-in) OR occ (OpenCASCADE), not both.'
            ),
        })
    return findings


def check_hardcoded_absolute_path(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Hardcoded absolute paths in sys.path or path assignments."""
    findings = []
    patterns = [
        re.compile(r'sys\.path\.(?:insert|append)\s*\(\s*(?:\d+\s*,\s*)?r?["\'][A-Za-z]:\\'),
        re.compile(r'sys\.path\.(?:insert|append)\s*\(\s*(?:\d+\s*,\s*)?r?["\'][A-Za-z]:/'),
    ]
    # Allow known tool paths (common in examples)
    allow_patterns = [
        re.compile(r'Coreform Cubit', re.IGNORECASE),
        re.compile(r'NGSolve', re.IGNORECASE),
    ]

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for pattern in patterns:
            if pattern.search(stripped):
                if any(ap.search(stripped) for ap in allow_patterns):
                    continue
                findings.append({
                    'line': i,
                    'severity': 'MODERATE',
                    'rule': 'hardcoded-absolute-path',
                    'message': (
                        'Hardcoded absolute path detected. '
                        'Use os.path.dirname(__file__) for relative paths.'
                    ),
                })
                break
    return findings


def check_msh_v4_for_readgmsh(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Using v4 format when ReadGmsh is called (v2.2 recommended)."""
    findings = []
    has_readgmsh = any('ReadGmsh' in line for line in lines)
    if not has_readgmsh:
        return findings

    v4_pattern = re.compile(r'MshFileVersion.*4')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if v4_pattern.search(stripped):
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'msh-v4-for-readgmsh',
                'message': (
                    'MshFileVersion set to 4 but ReadGmsh is used. '
                    'ReadGmsh works best with v2.2 format. '
                    'Use: gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)'
                ),
            })
    return findings


def check_generate_before_synchronize(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: mesh.generate() called before synchronize()."""
    findings = []
    generate_pattern = re.compile(r'gmsh\.model\.mesh\.generate\s*\(')
    sync_pattern = re.compile(r'gmsh\.model\.(?:geo|occ)\.synchronize\s*\(')

    # Only check if geo/occ operations exist (no sync needed for gmsh.open)
    has_geo_or_occ = any(
        re.search(r'gmsh\.model\.(?:geo|occ)\.(?:add|fuse|cut|intersect|fragment|import|extrude|revolve)', line)
        for line in lines
        if not line.strip().startswith('#')
    )
    if not has_geo_or_occ:
        return findings

    generate_line = None
    first_sync_line = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if generate_pattern.search(stripped) and generate_line is None:
            generate_line = i
        if sync_pattern.search(stripped) and first_sync_line is None:
            first_sync_line = i

    if generate_line is not None and first_sync_line is not None:
        if generate_line < first_sync_line:
            findings.append({
                'line': generate_line,
                'severity': 'CRITICAL',
                'rule': 'generate-before-synchronize',
                'message': (
                    'mesh.generate() called at line {} before synchronize() '
                    'at line {}. Call synchronize() first to finalize geometry.'
                ).format(generate_line, first_sync_line),
            })
    return findings


def check_unit_conversion_in_coords(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Multiplication by 1000 or 0.001 in coordinate definitions."""
    findings = []
    # Detect common unit conversion patterns near GMSH geometry calls
    conv_pattern = re.compile(
        r'(?:\*\s*(?:1000|0\.001|1e-3|1e3))|(?:(?:1000|0\.001|1e-3|1e3)\s*\*)'
    )
    gmsh_coord_pattern = re.compile(
        r'gmsh\.model\.(?:geo|occ)\.(?:add(?:Point|Box|Sphere|Cylinder|Cone|Torus|Wedge))\s*\('
    )

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if gmsh_coord_pattern.search(stripped) and conv_pattern.search(stripped):
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'unit-conversion-in-coords',
                'message': (
                    'Unit conversion factor (1000 or 0.001) in geometry '
                    'coordinates. Radia uses meters -- define coordinates '
                    'directly in meters without conversion.'
                ),
            })
    return findings


def check_missing_model_add(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: No gmsh.model.add() call before geometry creation."""
    findings = []
    has_import = any(
        re.search(r'^\s*import\s+gmsh\b', line)
        for line in lines
    )
    if not has_import:
        return findings

    has_model_add = any(
        re.search(r'gmsh\.model\.add\s*\(', line)
        for line in lines
        if not line.strip().startswith('#')
    )
    has_geo_or_occ = any(
        re.search(r'gmsh\.model\.(?:geo|occ)\.add', line)
        for line in lines
        if not line.strip().startswith('#')
    )

    if has_geo_or_occ and not has_model_add:
        findings.append({
            'line': 1,
            'severity': 'MODERATE',
            'rule': 'missing-model-add',
            'message': (
                'Geometry created but no gmsh.model.add() call found. '
                'Add gmsh.model.add("model_name") after gmsh.initialize() '
                'to create a named model.'
            ),
        })
    return findings


def check_setorder_before_generate(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: mesh.setOrder() called before mesh.generate()."""
    findings = []
    setorder_pattern = re.compile(r'gmsh\.model\.mesh\.setOrder\s*\(')
    generate_pattern = re.compile(r'gmsh\.model\.mesh\.generate\s*\(')

    setorder_line = None
    generate_line = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if setorder_pattern.search(stripped) and setorder_line is None:
            setorder_line = i
        if generate_pattern.search(stripped) and generate_line is None:
            generate_line = i

    if setorder_line is not None and generate_line is not None:
        if setorder_line < generate_line:
            findings.append({
                'line': setorder_line,
                'severity': 'HIGH',
                'rule': 'setorder-before-generate',
                'message': (
                    'mesh.setOrder() called at line {} before mesh.generate() '
                    'at line {}. Generate the mesh first, then elevate order.'
                ).format(setorder_line, generate_line),
            })
    return findings


def check_write_without_generate(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: gmsh.write() called but no mesh.generate() found."""
    findings = []
    has_write = False
    write_line = None
    has_generate = False

    # Only check scripts that import gmsh
    has_import = any(
        re.search(r'^\s*import\s+gmsh\b', line)
        for line in lines
    )
    if not has_import:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.search(r'gmsh\.write\s*\(', stripped):
            has_write = True
            if write_line is None:
                write_line = i
        if re.search(r'gmsh\.model\.mesh\.generate\s*\(', stripped):
            has_generate = True

    # Also check for gmsh.open() which loads an existing mesh (no generate needed)
    has_open = any(
        re.search(r'gmsh\.open\s*\(', line)
        for line in lines
        if not line.strip().startswith('#')
    )

    if has_write and not has_generate and not has_open:
        findings.append({
            'line': write_line,
            'severity': 'CRITICAL',
            'rule': 'write-without-generate',
            'message': (
                'gmsh.write() called but no gmsh.model.mesh.generate() found. '
                'Generate the mesh before writing: '
                'gmsh.model.mesh.generate(3) for volume, generate(2) for surface.'
            ),
        })
    return findings


def check_gmsh_unicode_print(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Unicode mathematical symbols in print statements."""
    findings = []
    unicode_chars = re.compile(
        r'[\u00b2\u00b3\u00b9\u2070-\u209f\u2190-\u21ff\u2200-\u22ff'
        r'\u2300-\u23ff\u2500-\u257f\u03b1-\u03c9\u0394\u03a3\u03a9'
        r'\u00b0\u00b5\u2264\u2265\u2260]'
    )
    print_pattern = re.compile(r'\bprint\s*\(')

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if print_pattern.search(stripped) and unicode_chars.search(stripped):
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'gmsh-unicode-print',
                'message': (
                    'Unicode mathematical symbol in print statement. '
                    'Windows console (cp932) cannot display these. '
                    'Use ASCII: ^2 not superscript-2, -> not arrow, <= not <=.'
                ),
            })
    return findings


# All rules in execution order
ALL_RULES = [
    check_missing_gmsh_initialize,
    check_missing_gmsh_finalize,
    check_missing_synchronize,
    check_wrong_generate_dimension,
    check_missing_physical_groups,
    check_mixing_geo_and_occ,
    check_hardcoded_absolute_path,
    check_msh_v4_for_readgmsh,
    check_generate_before_synchronize,
    check_unit_conversion_in_coords,
    check_missing_model_add,
    check_setorder_before_generate,
    check_write_without_generate,
    check_gmsh_unicode_print,
]
