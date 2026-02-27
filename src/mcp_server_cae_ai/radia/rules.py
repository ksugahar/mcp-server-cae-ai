"""
Lint rules for Radia Python scripts.

Each rule function receives (filepath, lines) and returns a list of findings.
A finding is a dict with keys: line, severity, rule, message.
"""

import re
import os
from typing import List, Dict


def check_objbckg_no_lambda(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: rad.ObjBckg() must receive a callable, not a list."""
    findings = []
    pattern = re.compile(r'rad\.ObjBckg\s*\(\s*\[')
    for i, line in enumerate(lines, 1):
        if pattern.search(line):
            findings.append({
                'line': i,
                'severity': 'CRITICAL',
                'rule': 'objbckg-needs-callable',
                'message': (
                    'rad.ObjBckg() requires a callable (lambda or function), '
                    'not a list. Use: rad.ObjBckg(lambda p: [Bx, By, Bz])'
                ),
            })
    return findings


def check_missing_utidelall(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: Scripts should call rad.UtiDelAll() for cleanup."""
    findings = []
    # Only check files that import radia
    has_radia = any('import radia' in line or 'import rad' in line for line in lines)
    if not has_radia:
        return findings

    # Skip __init__.py and module files (they shouldn't call UtiDelAll)
    basename = os.path.basename(filepath)
    if basename.startswith('__') or basename in ('radia.py',):
        return findings

    # Only check example scripts (files with if __name__ == '__main__')
    has_main = any("__name__" in line and "__main__" in line for line in lines)
    if not has_main:
        return findings

    has_utidelall = any('UtiDelAll' in line for line in lines)
    if not has_utidelall:
        findings.append({
            'line': len(lines),
            'severity': 'HIGH',
            'rule': 'missing-utidelall',
            'message': (
                'Script imports radia but does not call rad.UtiDelAll(). '
                'Add cleanup before script exit.'
            ),
        })
    return findings


def check_hardcoded_absolute_paths(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: No hardcoded absolute paths in sys.path or path assignments."""
    findings = []
    # Patterns for hardcoded Windows absolute paths used as imports/paths
    patterns = [
        re.compile(r'sys\.path\.insert\s*\(\s*\d+\s*,\s*r?["\'][A-Za-z]:\\'),
        re.compile(r'(?:repo_root|work_dir|base_dir)\s*=\s*r?["\'][A-Za-z]:\\'),
    ]
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for pattern in patterns:
            if pattern.search(stripped):
                findings.append({
                    'line': i,
                    'severity': 'HIGH',
                    'rule': 'hardcoded-absolute-path',
                    'message': (
                        'Hardcoded absolute path detected. '
                        'Use os.path.dirname(__file__) for relative paths.'
                    ),
                })
                break
    return findings


def check_missing_fldunits(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Example scripts should set rad.FldUnits('m')."""
    findings = []
    has_radia = any('import radia' in line or 'import rad' in line for line in lines)
    if not has_radia:
        return findings

    # Only check example scripts
    if 'examples' not in filepath.replace('\\', '/'):
        return findings

    has_fldunits = any('FldUnits' in line for line in lines)
    if not has_fldunits:
        findings.append({
            'line': 1,
            'severity': 'MODERATE',
            'rule': 'missing-fldunits',
            'message': (
                "Example script should call rad.FldUnits('m') at initialization. "
                "See Unit System Policy in CLAUDE.md."
            ),
        })
    return findings


def check_docstring_hardcoded_mm(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Public API docstrings should not hardcode 'in mm'."""
    findings = []
    # Only check src/radia modules
    if 'src/radia' not in filepath.replace('\\', '/') and 'src\\radia' not in filepath:
        return findings

    # Look for "in mm" in docstrings (inside triple-quoted strings)
    in_docstring = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if '"""' in stripped:
            count = stripped.count('"""')
            if count == 1:
                in_docstring = not in_docstring
            # If count == 2, it's an inline docstring - stays outside
        if in_docstring and re.search(r'\bpoint.*\bin mm\b', stripped):
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'docstring-hardcoded-mm',
                'message': (
                    'Docstring hardcodes "in mm". '
                    'Use "in constructor length units" for unit-agnostic API.'
                ),
            })
    return findings


def check_build_release_path(filepath: str, lines: List[str]) -> List[Dict]:
    """LOW: build/Release path import may be outdated."""
    findings = []
    pattern = re.compile(r"sys\.path\.insert.*['\"].*build/Release['\"]")
    for i, line in enumerate(lines, 1):
        if pattern.search(line):
            findings.append({
                'line': i,
                'severity': 'LOW',
                'rule': 'build-release-path',
                'message': (
                    'Import from build/Release may be outdated. '
                    'Prefer src/radia which has the latest binaries.'
                ),
            })
    return findings


def check_bessel_jv_for_sibc(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: Circular wire SIBC must use iv (modified Bessel), not jv."""
    findings = []
    # Check if file uses SIBC/impedance AND imports jv (not iv)
    has_sibc_context = any(
        kw in line.lower()
        for line in lines
        for kw in ['sibc', 'bessel', 'skin_depth', 'impedance_circular',
                    'bessel_impedance']
    )
    if not has_sibc_context:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Check for import of jv from scipy.special in SIBC context
        if re.search(r'from\s+scipy\.special\s+import\s+.*\bjv\b', stripped):
            # Check it's not also importing iv
            if not re.search(r'\biv\b', stripped):
                findings.append({
                    'line': i,
                    'severity': 'CRITICAL',
                    'rule': 'bessel-jv-not-iv',
                    'message': (
                        'Circular wire SIBC requires modified Bessel functions '
                        'iv (I0, I1), NOT regular jv (J0, J1). '
                        'jv gives wrong sign on internal inductance. '
                        'Use: from scipy.special import iv'
                    ),
                })
    return findings


def check_peec_low_nseg(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: PEEC circular coil should use n_seg >= 32 for coupling accuracy."""
    findings = []
    # Only check files that look like PEEC scripts
    has_peec_context = any(
        kw in line
        for line in lines
        for kw in ['FastHenryParser', 'PEECBuilder', 'peec', 'n_seg']
    )
    if not has_peec_context:
        return findings

    # Look for n_seg=<small number> patterns
    pattern = re.compile(r'\bn_seg\s*=\s*(\d+)')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        match = pattern.search(stripped)
        if match:
            n_seg = int(match.group(1))
            if n_seg < 32:
                findings.append({
                    'line': i,
                    'severity': 'MODERATE',
                    'rule': 'peec-low-nseg',
                    'message': (
                        f'n_seg={n_seg} may be too coarse for circular coil '
                        f'coupling accuracy. n_seg=16 gives ~26% Delta_L error; '
                        f'use n_seg>=64 for <10% error with magnetic cores.'
                    ),
                })
    return findings


def check_efie_v_minus_sign(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: EFIE V term must have positive sign (Lenz's law)."""
    findings = []
    # Only check files with EFIE/BEM/shield context
    has_efie_context = any(
        kw in line.lower()
        for line in lines
        for kw in ['shieldbemsibc', 'efie', 'v_ll', 'maxwell_slp',
                    'maxwellsinglelayer']
    )
    if not has_efie_context:
        return findings

    # Look for minus sign before V_LL or mu_0 * V in EFIE system assembly
    # Patterns that indicate wrong sign:
    #   - Zs * M_LL - jw * mu_0 * V_LL  (minus before jw*mu_0*V)
    #   - M_LL - ...V_LL
    patterns = [
        re.compile(r'[-]\s*(?:1j|1\.?j)\s*\*\s*(?:omega|w)\s*\*\s*(?:mu_0|MU_0|mu0)\s*\*\s*(?:V_LL|V_loop|self\._V_LL)'),
        re.compile(r'[-]\s*(?:mu_0|MU_0|mu0)\s*\*\s*(?:omega|w)\s*\*\s*(?:V_LL|V_loop|self\._V_LL)'),
    ]
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for pattern in patterns:
            if pattern.search(stripped):
                findings.append({
                    'line': i,
                    'severity': 'HIGH',
                    'rule': 'efie-v-minus-sign',
                    'message': (
                        'EFIE V_LL term has MINUS sign. The correct EFIE is: '
                        '(Zs*M_LL + jw*mu_0*V_LL)*I = -jw*b. '
                        'A minus sign on V violates Lenz\'s law '
                        '(A_scat would reinforce A_inc instead of opposing it).'
                    ),
                })
                break
    return findings


def check_classical_efie_breakdown(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Classical EFIE 1/kappa^2 causes low-frequency breakdown."""
    findings = []
    # Only check files using ngbem/HelmholtzSL
    has_helmholtz = any(
        kw in line
        for line in lines
        for kw in ['HelmholtzSL', 'HelmholtzSingleLayer']
    )
    if not has_helmholtz:
        return findings

    # Look for 1/kappa**2 or (1/kappa^2) patterns
    patterns = [
        re.compile(r'1\s*/\s*(?:kappa|kap)\s*\*\*\s*2'),
        re.compile(r'1\.0\s*/\s*\(?(?:kappa|kap)\s*\*\*\s*2'),
        re.compile(r'1\.0\s*/\s*\(?(?:kappa|kap)\s*\*\s*(?:kappa|kap)'),
    ]
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for pattern in patterns:
            if pattern.search(stripped):
                findings.append({
                    'line': i,
                    'severity': 'MODERATE',
                    'rule': 'classical-efie-breakdown',
                    'message': (
                        'Classical EFIE with 1/kappa^2 scaling causes O(kappa^{-2}) '
                        'condition number blow-up at low frequency. '
                        'Use stabilized formulation: kappa^2 * V_kappa '
                        '(multiply V by kappa^2 instead of dividing). '
                        'Ref: Weggler stabilized EFIE.'
                    ),
                })
                break
    return findings


def check_peec_p_over_jw(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: PEEC Loop-Star P/(jw) causes low-frequency breakdown."""
    findings = []
    # Only check files with PEEC/Loop-Star context
    has_peec_ls = any(
        kw in line
        for line in lines
        for kw in ['loop_star', 'Loop-Star', 'LoopStar', 'Z_SS', 'P_matrix',
                    'NGBEMPEECSolver', 'ngbem_peec']
    )
    if not has_peec_ls:
        return findings

    # Detect P/(jw) or P/(1j*omega) patterns in actual code (not comments/docstrings)
    patterns = [
        re.compile(r'(?:self\.)?P\s*/\s*\(?\s*(?:1j|1\.?j)\s*\*\s*(?:omega|w)'),
        re.compile(r'(?:self\.)?P\s*/\s*\(?\s*(?:omega|w)\s*\*\s*(?:1j|1\.?j)'),
        re.compile(r'Z_SS\s*=\s*.*(?:self\.)?P\s*/'),
    ]
    in_docstring = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Track docstring state
        if '"""' in stripped:
            count = stripped.count('"""')
            if count == 1:
                in_docstring = not in_docstring
            continue
        if in_docstring or stripped.startswith('#'):
            continue
        for pattern in patterns:
            if pattern.search(stripped):
                findings.append({
                    'line': i,
                    'severity': 'HIGH',
                    'rule': 'peec-p-over-jw',
                    'message': (
                        'PEEC Loop-Star P/(jw) causes low-frequency breakdown '
                        '(40-340% error). Use reformulated Schur complement: '
                        'precompute P^{-1}@M_LS, multiply by jw at runtime. '
                        'Or use stabilized mode with Weggler\'s k^2*V_0 block. '
                        'See NGBEMPEECSolver mode="full" or mode="stabilized".'
                    ),
                })
                break
    return findings


# --- NGSolve-specific rules ---

def check_hcurl_missing_nograds(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: Magnetostatic HCurl spaces should use nograds=True."""
    findings = []
    has_magnetostatic = any(
        kw in line.lower()
        for line in lines
        for kw in ['magnetostatic', 'curl(u)*curl(v)', 'curl-curl',
                    'vector potential', 'magnet']
    )
    if not has_magnetostatic:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # HCurl(...) without nograds or with nograds=False, and NOT complex
        if re.search(r'HCurl\s*\(', stripped):
            has_nograds = 'nograds=True' in stripped or 'nograds = True' in stripped
            is_complex = 'complex=True' in stripped or 'complex = True' in stripped
            if not has_nograds and not is_complex:
                findings.append({
                    'line': i,
                    'severity': 'HIGH',
                    'rule': 'hcurl-missing-nograds',
                    'message': (
                        'HCurl space for magnetostatics should use nograds=True '
                        'to remove gradient null space. Without it, the curl-curl '
                        'system is singular. Add nograds=True parameter.'
                    ),
                })
    return findings


def check_ngsolve_precond_after_assemble(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: BDDC preconditioner must be registered before assembly."""
    findings = []
    has_bddc = any('Preconditioner' in line and 'bddc' in line for line in lines)
    if not has_bddc:
        return findings

    # Find .Assemble() and Preconditioner("bddc") line numbers
    assemble_lines = []
    precond_lines = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if '.Assemble()' in stripped:
            assemble_lines.append(i)
        if re.search(r'Preconditioner\s*\(.*bddc', stripped):
            precond_lines.append(i)

    # Check if any Preconditioner appears after its bilinear form's Assemble
    for p_line in precond_lines:
        for a_line in assemble_lines:
            if a_line < p_line:
                findings.append({
                    'line': p_line,
                    'severity': 'MODERATE',
                    'rule': 'ngsolve-precond-after-assemble',
                    'message': (
                        'BDDC Preconditioner registered AFTER .Assemble() '
                        '(line {}). It must be registered BEFORE assembly '
                        'to access element matrices. Move Preconditioner() '
                        'before .Assemble().'.format(a_line)
                    ),
                })
                break
    return findings


def check_ngsolve_missing_trace_bem(filepath: str, lines: List[str]) -> List[Dict]:
    """CRITICAL: BEM on HDivSurface requires .Trace() on trial/test functions."""
    findings = []
    has_bem_hdiv = any(
        'HDivSurface' in line and ('LaplaceSL' in ''.join(lines) or
                                    'HelmholtzSL' in ''.join(lines))
        for line in lines
    )
    if not has_bem_hdiv:
        return findings

    # Look for LaplaceSL/HelmholtzSL usage without .Trace()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Check for BEM operator with trial/test but without .Trace()
        if re.search(r'(?:LaplaceSL|HelmholtzSL)\s*\(', stripped):
            # Check if .Trace() appears in the same line
            if '.Trace()' not in stripped:
                # Could be multi-line, check surrounding context
                context = ' '.join(lines[max(0,i-2):min(len(lines),i+2)])
                if '.Trace()' not in context:
                    findings.append({
                        'line': i,
                        'severity': 'CRITICAL',
                        'rule': 'ngsolve-missing-trace-bem',
                        'message': (
                            'BEM operator (LaplaceSL/HelmholtzSL) on HDivSurface '
                            'requires .Trace() on trial/test functions. Without '
                            '.Trace(), boundary-edge DOFs get corrupted diagonal '
                            'entries, causing wildly wrong results. '
                            'Use: j_trial.Trace() * ds(...)'
                        ),
                    })
    return findings


def check_ngsolve_overwrite_xyz(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Overwriting x/y/z coordinate variables in loops."""
    findings = []
    has_ngsolve = any(
        kw in line
        for line in lines
        for kw in ['from ngsolve', 'import ngsolve', 'from ngsolve import']
    )
    if not has_ngsolve:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Check for 'for x in' or 'for y in' or 'for z in' patterns
        match = re.match(r'for\s+(x|y|z)\s+in\s+', stripped)
        if match:
            var = match.group(1)
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'ngsolve-overwrite-xyz',
                'message': (
                    f'Loop variable "{var}" overwrites NGSolve coordinate '
                    f'CoefficientFunction. After this loop, {var} will be a '
                    f'scalar, not a coordinate. Use a different variable name '
                    f'(e.g., "{var}i" or "{var}_val").'
                ),
            })
    return findings


def check_ngsolve_vec_assign(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: NGSolve vector assignment must use .data attribute."""
    findings = []
    has_ngsolve = any(
        kw in line
        for line in lines
        for kw in ['from ngsolve', 'import ngsolve', 'GridFunction']
    )
    if not has_ngsolve:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Pattern: gfu.vec = ... (without .data)
        if re.search(r'\.vec\s*=\s*(?!.*\.data)', stripped):
            # Exclude .vec.data = and .vec[:] =
            if '.vec.data' not in stripped and '.vec[' not in stripped:
                # Exclude definitions like gfu.vec = gfu.vec.CreateVector()
                if 'CreateVector' not in stripped:
                    findings.append({
                        'line': i,
                        'severity': 'MODERATE',
                        'rule': 'ngsolve-vec-assign',
                        'message': (
                            'Direct assignment to .vec creates a symbolic '
                            'expression, not an evaluated result. '
                            'Use .vec.data = ... to evaluate and store, or '
                            '.vec[:] = ... for slice assignment.'
                        ),
                    })
    return findings


def check_ngsolve_dim2_occ(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: 2D OCC geometry requires dim=2 parameter."""
    findings = []
    has_2d_geom = any(
        kw in line
        for line in lines
        for kw in ['Rectangle', 'Circle', 'Face()', 'WorkPlane']
    )
    if not has_2d_geom:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.search(r'OCCGeometry\s*\(', stripped) and 'dim=' not in stripped:
            # Check if Face() or 2D shapes are used nearby
            context = ' '.join(lines[max(0,i-5):i])
            if any(kw in context for kw in ['Rectangle', '.Face()', 'WorkPlane',
                                              'Circle']):
                findings.append({
                    'line': i,
                    'severity': 'MODERATE',
                    'rule': 'ngsolve-dim2-occ',
                    'message': (
                        'OCCGeometry with 2D shapes (Rectangle, Face) requires '
                        'dim=2 parameter. Without it, a 3D surface mesh is '
                        'generated instead of a 2D mesh. '
                        'Use: OCCGeometry(shape, dim=2)'
                    ),
                })
    return findings


def check_ngsolve_cg_on_saddle_point(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: CG used on A-Omega saddle-point system (should use GMRes/MinRes)."""
    findings = []
    # Detect A-Omega or saddle-point indicators
    has_saddle = False
    for line in lines:
        stripped = line.strip()
        if any(kw in stripped for kw in [
            'curl(N).Trace() * normal',
            'curl(A).Trace() * normal',
            'A_ReducedOmega',
            'fesA * fesOmega',
        ]):
            has_saddle = True
            break

    if not has_saddle:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # CG on indefinite system
        if re.search(r'solvers\.CG\s*\(', stripped) or \
           re.search(r'CGSolver\s*\(', stripped):
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'ngsolve-cg-on-saddle-point',
                'message': (
                    'CG solver used on a saddle-point system (A-Omega mixed '
                    'formulation). The system is INDEFINITE, so CG may diverge. '
                    'Use MinRes, GMRes, or a direct solver instead.'
                ),
            })
    return findings


def check_ngsolve_vectorh1_for_em(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: VectorH1 is wrong for electromagnetic fields (use HCurl/HDiv)."""
    findings = []
    has_em_context = any(
        kw in line.lower()
        for line in lines
        for kw in ['magnetostatic', 'maxwell', 'curl(u)', 'curl(v)',
                    'vector potential', 'electric field', 'magnetic',
                    'hcurl', 'hdiv', 'b-field', 'e-field']
    )
    if not has_em_context:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.search(r'VectorH1\s*\(', stripped):
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'ngsolve-vectorh1-for-em',
                'message': (
                    'VectorH1 used in electromagnetic context. VectorH1 enforces '
                    'full C^0 continuity on ALL components, which is wrong for EM '
                    'fields. Use HCurl (tangential continuity for E, A) or '
                    'HDiv (normal continuity for B, J).'
                ),
            })
    return findings


def check_ngsolve_pinvit_no_projection(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: PINVIT/LOBPCG eigenvalue solver without gradient projection."""
    findings = []
    has_pinvit = any(
        kw in line
        for line in lines
        for kw in ['solvers.PINVIT', 'PINVIT(', 'solvers.LOBPCG', 'LOBPCG(']
    )
    if not has_pinvit:
        return findings

    # Check if gradient projection is present
    has_projection = any(
        kw in line
        for line in lines
        for kw in ['CreateGradient', 'gradmat', 'grad_projection', 'proj @']
    )

    # Check if HCurl context
    has_hcurl = any('HCurl' in line for line in lines)

    if has_hcurl and not has_projection:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.search(r'(?:PINVIT|LOBPCG)\s*\(', stripped):
                findings.append({
                    'line': i,
                    'severity': 'MODERATE',
                    'rule': 'ngsolve-pinvit-no-projection',
                    'message': (
                        'PINVIT/LOBPCG eigenvalue solver on HCurl space without '
                        'gradient projection. The curl-curl null space (gradient '
                        'fields) produces spurious zero eigenvalues. Use '
                        'fes.CreateGradient() to build projection matrix.'
                    ),
                })
    return findings


def check_eddy_current_missing_complex(filepath: str, lines: List[str]) -> List[Dict]:
    """HIGH: Eddy current HCurl/H1 spaces must use complex=True."""
    findings = []
    has_eddy_context = any(
        kw in line.lower()
        for line in lines
        for kw in ['eddy', 'induction_heating', 'joule', 'freq', '2j *',
                    'a + grad(phi)', 'a+grad(phi)']
    )
    if not has_eddy_context:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # HCurl or H1 in eddy current context without complex=True
        if re.search(r'(?:HCurl|H1)\s*\(', stripped):
            has_complex = 'complex=True' in stripped or 'complex = True' in stripped
            # Skip H1 for thermal (no complex needed for temperature)
            is_thermal = any(
                kw in stripped.lower()
                for kw in ['temperature', 'thermal', 'heat']
            )
            if not has_complex and not is_thermal:
                # Check if this is a definedon for thermal (checking context)
                context = ' '.join(lines[max(0,i-3):i+2])
                is_thermal_ctx = any(
                    kw in context.lower()
                    for kw in ['temperature', 'thermal', 'heat equation',
                                'rho_c', 'kappa', 'convection']
                )
                if not is_thermal_ctx:
                    findings.append({
                        'line': i,
                        'severity': 'HIGH',
                        'rule': 'eddy-current-missing-complex',
                        'message': (
                            'FE space in eddy current context without complex=True. '
                            'Frequency-domain eddy current analysis requires complex-'
                            'valued spaces. Add complex=True parameter.'
                        ),
                    })
    return findings


def check_joule_heat_missing_conj(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Joule heat Q must use Conj(E), not E*E."""
    findings = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Look for Q = ... sigma * InnerProduct(E, E) without Conj
        if re.search(r'InnerProduct\s*\(\s*E\s*,\s*E\s*\)', stripped):
            if 'Conj' not in stripped:
                findings.append({
                    'line': i,
                    'severity': 'MODERATE',
                    'rule': 'joule-heat-missing-conj',
                    'message': (
                        'Joule heat uses InnerProduct(E, E) instead of '
                        'InnerProduct(E, Conj(E)). For complex fields, '
                        'E*E gives a complex number, not real power. '
                        'Use: 0.5 * sigma * InnerProduct(E, Conj(E)).real'
                    ),
                })
    return findings


def check_ngsolve_kelvin_missing_bonus_intorder(filepath: str, lines: List[str]) -> List[Dict]:
    """MODERATE: Kelvin transform bilinear form without bonus_intorder."""
    findings = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        # Detect Kelvin-domain integration without bonus_intorder
        if re.search(r'dx\s*\(\s*["\']Kelvin["\']', stripped) and \
           'bonus_intorder' not in stripped:
            findings.append({
                'line': i,
                'severity': 'MODERATE',
                'rule': 'ngsolve-kelvin-missing-bonus-intorder',
                'message': (
                    'Integration over Kelvin domain without bonus_intorder. '
                    'The spatially-varying Kelvin Jacobian requires higher '
                    'quadrature for accuracy. '
                    'Use: dx("Kelvin", bonus_intorder=4)'
                ),
            })
    return findings


# All rules in execution order
ALL_RULES = [
    # Radia rules
    check_objbckg_no_lambda,
    check_missing_utidelall,
    check_hardcoded_absolute_paths,
    check_missing_fldunits,
    check_docstring_hardcoded_mm,
    check_build_release_path,
    check_bessel_jv_for_sibc,
    check_peec_low_nseg,
    check_efie_v_minus_sign,
    check_classical_efie_breakdown,
    check_peec_p_over_jw,
    # NGSolve rules
    check_hcurl_missing_nograds,
    check_ngsolve_precond_after_assemble,
    check_ngsolve_missing_trace_bem,
    check_ngsolve_overwrite_xyz,
    check_ngsolve_vec_assign,
    check_ngsolve_dim2_occ,
    # NGSolve rules (EMPY-sourced)
    check_ngsolve_cg_on_saddle_point,
    check_ngsolve_kelvin_missing_bonus_intorder,
    # NGSolve rules (docs-sourced)
    check_ngsolve_vectorh1_for_em,
    check_ngsolve_pinvit_no_projection,
    # NGSolve rules (induction heating)
    check_eddy_current_missing_complex,
    check_joule_heat_missing_conj,
]
