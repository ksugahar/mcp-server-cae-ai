"""
Radia Project MCP Server

Provides tools for:
- Linting Python scripts against Radia + NGSolve conventions (27 rules)
- Radia BEM library usage documentation
- GmshBuilder mesh generation API documentation (719 methods, 15 topics incl. CFD techniques)
- NGSolve FEM usage documentation (12 topics incl. EM formulations, adaptive)
- Induction heating workflow (EM -> Joule heat -> transient thermal, 7 topics)
- Kelvin transformation reference for open boundary FEM
- ngsolve-sparsesolv (ICCG) solver documentation
- md2html converter documentation (MathJax, reference links, styled HTML)

Usage:
    mcp-server-radia              # Start MCP server (stdio transport)
    mcp-server-radia --selftest   # Run self-test on examples/
"""

import os
import sys
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Import rules and knowledge bases
from .rules import ALL_RULES
from .sparsesolv_knowledge import get_sparsesolv_documentation
from .kelvin_knowledge import get_kelvin_documentation
from .radia_knowledge import get_radia_documentation
from .ngsolve_knowledge import get_ngsolve_documentation
from .induction_heating_knowledge import get_induction_heating_documentation
from .md2html_knowledge import get_md2html_documentation
from .gmsh_builder_knowledge import get_gmsh_builder_documentation

# Create MCP server
mcp = FastMCP("radia-lint")

# Resolve relative paths against current working directory
PROJECT_ROOT = Path.cwd()


def _lint_file(filepath: str) -> list[dict]:
    """Run all lint rules on a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except (OSError, IOError) as e:
        return [{'line': 0, 'severity': 'ERROR', 'rule': 'read-error',
                 'message': f'Cannot read file: {e}'}]

    findings = []
    for rule_fn in ALL_RULES:
        findings.extend(rule_fn(filepath, lines))

    # Sort by severity, then line number
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MODERATE': 2, 'LOW': 3, 'INFO': 4, 'ERROR': -1}
    findings.sort(key=lambda f: (severity_order.get(f['severity'], 9), f['line']))
    return findings


def _format_findings(filepath: str, findings: list[dict]) -> str:
    """Format findings for display."""
    if not findings:
        return f"[OK] {filepath}: No issues found."

    lines = [f"[{len(findings)} issue(s)] {filepath}:"]
    for f in findings:
        lines.append(
            f"  L{f['line']:>4d} [{f['severity']}] {f['rule']}: {f['message']}"
        )
    return '\n'.join(lines)


@mcp.tool()
def lint_radia_script(filepath: str) -> str:
    """
    Lint a single Python script for Radia and NGSolve convention violations.

    Radia checks:
    - ObjBckg called with list instead of callable (CRITICAL)
    - Bessel jv used instead of iv for circular SIBC (CRITICAL)
    - Missing rad.UtiDelAll() cleanup (HIGH)
    - Hardcoded absolute paths in sys.path (HIGH)
    - EFIE V_LL term with wrong (minus) sign (HIGH)
    - Removed rad.FldUnits() call present (HIGH)
    - PEEC n_seg too low for circular coil coupling (MODERATE)
    - Classical EFIE 1/kappa^2 low-frequency breakdown (MODERATE)
    - PEEC P/(jw) low-frequency breakdown (HIGH)
    - Docstrings hardcoding "in mm" (MODERATE)
    - Outdated build/Release path imports (LOW)

    NGSolve checks:
    - BEM on HDivSurface without .Trace() (CRITICAL)
    - HCurl magnetostatics without nograds=True (HIGH)
    - Eddy current FE space missing complex=True (HIGH)
    - BDDC preconditioner registered after assembly (MODERATE)
    - Overwriting x/y/z coordinate variables (MODERATE)
    - Direct .vec assignment without .data (MODERATE)
    - 2D OCC geometry without dim=2 (MODERATE)
    - CG on A-Omega saddle-point system (MODERATE)
    - Kelvin domain without bonus_intorder (MODERATE)
    - VectorH1 for electromagnetic fields (MODERATE)
    - PINVIT/LOBPCG without gradient projection (MODERATE)
    - Joule heat missing Conj() for complex fields (MODERATE)

    Args:
        filepath: Absolute or relative path to the Python file to check.
    """
    # Resolve relative paths against project root
    p = Path(filepath)
    if not p.is_absolute():
        p = PROJECT_ROOT / p

    if not p.exists():
        return f"Error: File not found: {p}"
    if not p.suffix == '.py':
        return f"Error: Not a Python file: {p}"

    findings = _lint_file(str(p))
    return _format_findings(str(p), findings)


@mcp.tool()
def lint_radia_directory(directory: str = "examples", include_src: bool = False) -> str:
    """
    Lint all Python scripts in a directory for Radia convention violations.

    Recursively scans .py files and reports findings grouped by file.

    Args:
        directory: Directory path relative to project root (default: "examples").
        include_src: Also scan src/radia/ for docstring issues (default: false).
    """
    dirs_to_scan = []

    # Main directory
    d = Path(directory)
    if not d.is_absolute():
        d = PROJECT_ROOT / d
    if d.exists():
        dirs_to_scan.append(d)
    else:
        return f"Error: Directory not found: {d}"

    # Optionally include src/radia
    if include_src:
        src_dir = PROJECT_ROOT / "src" / "radia"
        if src_dir.exists():
            dirs_to_scan.append(src_dir)

    # Collect all .py files
    py_files = []
    for scan_dir in dirs_to_scan:
        py_files.extend(sorted(scan_dir.rglob("*.py")))

    if not py_files:
        return f"No Python files found in {directory}."

    # Lint all files
    total_findings = 0
    file_results = []
    summary_by_severity = {'CRITICAL': 0, 'HIGH': 0, 'MODERATE': 0, 'LOW': 0, 'INFO': 0}

    for py_file in py_files:
        findings = _lint_file(str(py_file))
        if findings:
            total_findings += len(findings)
            rel_path = py_file.relative_to(PROJECT_ROOT) if py_file.is_relative_to(PROJECT_ROOT) else py_file
            file_results.append(_format_findings(str(rel_path), findings))
            for f in findings:
                sev = f['severity']
                if sev in summary_by_severity:
                    summary_by_severity[sev] += 1

    # Build output
    output_parts = [
        f"Radia Lint Report: {len(py_files)} files scanned, {total_findings} issues found.",
        "",
        f"Summary: {summary_by_severity['CRITICAL']} CRITICAL, "
        f"{summary_by_severity['HIGH']} HIGH, "
        f"{summary_by_severity['MODERATE']} MODERATE, "
        f"{summary_by_severity['LOW']} LOW, "
        f"{summary_by_severity['INFO']} INFO",
        "",
    ]

    if file_results:
        output_parts.append("=" * 70)
        output_parts.extend(file_results)
    else:
        output_parts.append("All files passed!")

    return '\n'.join(output_parts)


@mcp.tool()
def get_radia_lint_rules() -> str:
    """
    List all available Radia lint rules with descriptions.

    Returns a summary of each rule, its severity, and what it checks for.
    """
    rules_info = [
        {
            'rule': 'objbckg-needs-callable',
            'severity': 'CRITICAL',
            'description': (
                'rad.ObjBckg() must receive a callable (lambda or function), '
                'not a list/array. The legacy ObjBckg([Bx,By,Bz]) form is not supported.'
            ),
            'fix': 'rad.ObjBckg([0,0,B]) -> rad.ObjBckg(lambda p: [0,0,B])',
        },
        {
            'rule': 'missing-utidelall',
            'severity': 'HIGH',
            'description': (
                'Example scripts that import radia should call rad.UtiDelAll() '
                'before exiting to free C++ objects.'
            ),
            'fix': 'Add rad.UtiDelAll() at the end of main().',
        },
        {
            'rule': 'hardcoded-absolute-path',
            'severity': 'HIGH',
            'description': (
                'sys.path.insert() or path variables should not use hardcoded '
                'absolute Windows paths (e.g. S:\\Radia\\...).'
            ),
            'fix': 'Use os.path.join(os.path.dirname(__file__), "relative/path").',
        },
        {
            'rule': 'removed-fldunits',
            'severity': 'HIGH',
            'description': (
                "rad.FldUnits() has been removed. Radia always uses meters. "
                "Delete all FldUnits() calls."
            ),
            'fix': "Delete the rad.FldUnits() call entirely.",
        },
        {
            'rule': 'removed-fldbatch',
            'severity': 'HIGH',
            'description': (
                "FldBatch/FldA/FldPhi are removed. Use unified rad.Fld() "
                "with batch points shape (N,3)."
            ),
            'fix': (
                "Replace rad.FldBatch(obj, pts) with "
                "np.asarray(rad.Fld(obj, 'b', pts)). "
                "Replace rad.FldA(obj, pts) with rad.Fld(obj, 'a', pts). "
                "Replace rad.FldPhi(obj, pts) with rad.Fld(obj, 'phi', pts)."
            ),
        },
        {
            'rule': 'removed-solver-api',
            'severity': 'HIGH',
            'description': (
                "Old solver parameter APIs (SetHACApKParams, SetBiCGSTABTol, "
                "SetRelaxParam, SetNewtonMethod, etc.) are removed."
            ),
            'fix': (
                "Use rad.SolverConfig(**kwargs) to set parameters and "
                "rad.GetSolverConfig() to query them. Example: "
                "rad.SolverConfig(hacapk_eps=1e-4, hacapk_leaf=10, hacapk_eta=2.0)"
            ),
        },
        {
            'rule': 'docstring-hardcoded-mm',
            'severity': 'MODERATE',
            'description': (
                'Public API docstrings in src/radia/ should not hardcode "in mm" '
                'when the class supports a units parameter.'
            ),
            'fix': 'Change "point in mm" to "point (in constructor length units)".',
        },
        {
            'rule': 'build-release-path',
            'severity': 'LOW',
            'description': (
                'Importing from build/Release may use outdated binaries. '
                'Prefer src/radia which has the latest copies.'
            ),
            'fix': 'Change to: os.path.join(os.path.dirname(__file__), "../../src/radia").',
        },
        {
            'rule': 'bessel-jv-not-iv',
            'severity': 'CRITICAL',
            'description': (
                'Circular wire SIBC must use modified Bessel functions iv (I0, I1), '
                'NOT regular jv (J0, J1). jv gives correct R_ac/R_dc but wrong sign '
                'on internal inductance Im(Z).'
            ),
            'fix': 'from scipy.special import jv -> from scipy.special import iv',
        },
        {
            'rule': 'peec-low-nseg',
            'severity': 'MODERATE',
            'description': (
                'Circular coil PEEC with n_seg < 32 may give poor coupling accuracy. '
                'n_seg=16 gives ~26% Delta_L error vs FEM; n_seg=64 gives ~9%.'
            ),
            'fix': 'Increase n_seg to 64 or higher for accurate core/shield coupling.',
        },
        {
            'rule': 'efie-v-minus-sign',
            'severity': 'HIGH',
            'description': (
                'EFIE system (Zs*M_LL + jw*mu_0*V_LL)*I = -jw*b must use '
                'POSITIVE sign on V_LL term. A minus sign violates Lenz\'s law: '
                'A_scat would reinforce A_inc instead of opposing it.'
            ),
            'fix': 'Change minus to plus: Zs*M_LL + jw*mu_0*V_LL (not minus).',
        },
        {
            'rule': 'classical-efie-breakdown',
            'severity': 'MODERATE',
            'description': (
                'Classical EFIE using V1 - (1/kappa^2)*V2 has O(kappa^{-2}) '
                'condition number blow-up at low frequency. Use Weggler\'s '
                'stabilized formulation with kappa^2 * V_kappa instead.'
            ),
            'fix': 'Use stabilized EFIE: [A_k, Q_k; Q_k^T, kappa^2*V_k].',
        },
        # NGSolve rules
        {
            'rule': 'hcurl-missing-nograds',
            'severity': 'HIGH',
            'description': (
                'HCurl space for magnetostatics should use nograds=True to '
                'remove gradient null space. Without it, the curl-curl system '
                'is singular.'
            ),
            'fix': 'Add nograds=True: HCurl(mesh, order=2, nograds=True)',
        },
        {
            'rule': 'ngsolve-precond-after-assemble',
            'severity': 'MODERATE',
            'description': (
                'BDDC Preconditioner must be registered BEFORE .Assemble() '
                'to access element matrices. Registration after assembly '
                'means the preconditioner cannot see the element structure.'
            ),
            'fix': 'Move Preconditioner(a, "bddc") BEFORE a.Assemble().',
        },
        {
            'rule': 'ngsolve-missing-trace-bem',
            'severity': 'CRITICAL',
            'description': (
                'BEM operators (LaplaceSL/HelmholtzSL) on HDivSurface require '
                '.Trace() on trial/test functions. Without it, boundary-edge '
                'DOFs get corrupted, causing wildly wrong results.'
            ),
            'fix': 'Use j_trial.Trace()*ds(...) instead of j_trial*ds(...).',
        },
        {
            'rule': 'ngsolve-overwrite-xyz',
            'severity': 'MODERATE',
            'description': (
                'Loop variable x/y/z overwrites NGSolve coordinate '
                'CoefficientFunction. After the loop, the variable is a '
                'scalar, not a coordinate.'
            ),
            'fix': 'Use different loop variable: "for xi in ..." instead of "for x in ...".',
        },
        {
            'rule': 'ngsolve-vec-assign',
            'severity': 'MODERATE',
            'description': (
                'Direct .vec = assignment creates symbolic expression, '
                'not evaluated result. Must use .vec.data = to evaluate.'
            ),
            'fix': 'Use gfu.vec.data = ... instead of gfu.vec = ...',
        },
        {
            'rule': 'ngsolve-dim2-occ',
            'severity': 'MODERATE',
            'description': (
                '2D OCC geometry (Rectangle, Face) requires dim=2 parameter '
                'in OCCGeometry(). Without it, a 3D surface mesh is generated.'
            ),
            'fix': 'Add dim=2: OCCGeometry(shape, dim=2)',
        },
        # EMPY-sourced rules
        {
            'rule': 'ngsolve-cg-on-saddle-point',
            'severity': 'MODERATE',
            'description': (
                'CG solver on A-Omega mixed formulation (saddle-point system). '
                'The system is indefinite, CG may diverge. Use MinRes/GMRes.'
            ),
            'fix': 'Replace solvers.CG() with solvers.GMRes() or MinRes().',
        },
        {
            'rule': 'ngsolve-kelvin-missing-bonus-intorder',
            'severity': 'MODERATE',
            'description': (
                'Kelvin domain integration without bonus_intorder. The varying '
                'Jacobian requires higher quadrature for accurate results.'
            ),
            'fix': 'Add bonus_intorder=4: dx("Kelvin", bonus_intorder=4)',
        },
        # Docs-sourced rules
        {
            'rule': 'ngsolve-vectorh1-for-em',
            'severity': 'MODERATE',
            'description': (
                'VectorH1 used in electromagnetic context. VectorH1 enforces full '
                'C^0 continuity on ALL components, which is wrong for EM fields. '
                'Use HCurl (tangential) or HDiv (normal continuity).'
            ),
            'fix': 'Replace VectorH1 with HCurl (for E, A) or HDiv (for B, J).',
        },
        {
            'rule': 'ngsolve-pinvit-no-projection',
            'severity': 'MODERATE',
            'description': (
                'PINVIT/LOBPCG eigenvalue solver on HCurl without gradient '
                'projection. Curl-curl null space produces spurious zero eigenvalues.'
            ),
            'fix': 'Build gradient projection via fes.CreateGradient() and apply to preconditioner.',
        },
        # Induction heating rules
        {
            'rule': 'eddy-current-missing-complex',
            'severity': 'HIGH',
            'description': (
                'HCurl/H1 space in eddy current context without complex=True. '
                'Frequency-domain analysis requires complex-valued FE spaces.'
            ),
            'fix': 'Add complex=True: HCurl(mesh, order=2, complex=True)',
        },
        {
            'rule': 'joule-heat-missing-conj',
            'severity': 'MODERATE',
            'description': (
                'Joule heat computed as InnerProduct(E, E) instead of '
                'InnerProduct(E, Conj(E)). Complex E*E != |E|^2.'
            ),
            'fix': 'Use: 0.5 * sigma * InnerProduct(E, Conj(E)).real',
        },
        # GmshBuilder rules
        {
            'rule': 'gmsh-builder-no-context-manager',
            'severity': 'HIGH',
            'description': (
                'GmshBuilder must be used as a context manager (with statement) '
                'to ensure GMSH is properly initialized and finalized.'
            ),
            'fix': 'Use: with GmshBuilder() as gb: ...',
        },
        {
            'rule': 'gmsh-builder-old-cubit-import',
            'severity': 'HIGH',
            'description': (
                'cubit_mesh / CubitMesh has been renamed to gmsh_builder / GmshBuilder.'
            ),
            'fix': 'Use: from radia.gmsh_builder import GmshBuilder',
        },
        {
            'rule': 'gmsh-builder-no-mesh-size',
            'severity': 'MODERATE',
            'description': (
                'generate() called without set_mesh_size() or set_divisions(). '
                'GMSH uses default sizing which may produce poor quality mesh.'
            ),
            'fix': 'Add gb.set_mesh_size(0.005) before gb.generate().',
        },
        {
            'rule': 'gmsh-builder-missing-fragment',
            'severity': 'MODERATE',
            'description': (
                'Multiple geometries exported to Radia without fragment(). '
                'Volumes must share interfaces via fragment() for correct BEM assembly.'
            ),
            'fix': 'Use gb.fragment(vol_ids) before meshing multi-body assemblies.',
        },
    ]

    lines = ["Radia + NGSolve Lint Rules", "=" * 50, ""]
    for r in rules_info:
        lines.append(f"[{r['severity']}] {r['rule']}")
        lines.append(f"  {r['description']}")
        lines.append(f"  Fix: {r['fix']}")
        lines.append("")

    return '\n'.join(lines)


@mcp.tool()
def sparsesolv(topic: str = "all") -> str:
    """
    Get ngsolve-sparsesolv documentation and code examples.

    ngsolve-sparsesolv is a standalone pybind11 add-on module for NGSolve
    that provides IC, SGS, and BDDC preconditioners with ICCG, SGSMRTR,
    and CG solvers. Supports auto-shift IC, complex systems, ABMC parallel
    triangular solves, and BDDC domain decomposition.

    Repository: https://github.com/ksugahar/ngsolve-sparsesolv

    Args:
        topic: Documentation topic or code example. Options:
            "all"              - Complete documentation
            "overview"         - Library overview, add-on positioning, features
            "api"              - Python API reference (solvers, preconditioners, BDDC)
            "examples"         - Usage examples (Poisson, curl-curl, complex, BDDC, etc.)
            "abmc"             - ABMC ordering: parallel triangular solve optimization
            "best_practices"   - Preconditioner selection, complex systems, tips
            "build"            - Build and installation instructions
            "example_poisson"  - Ready-to-run: 2D Poisson with ICCG
            "example_curlcurl" - Ready-to-run: 3D curl-curl with auto-shift IC
            "example_eddy"     - Ready-to-run: Complex eddy current problem
            "example_precond"  - Ready-to-run: IC/SGS with NGSolve CGSolver
            "example_divergence" - Ready-to-run: Divergence detection
            "example_bddc"     - Ready-to-run: BDDC preconditioner with CG
    """
    return get_sparsesolv_documentation(topic)


@mcp.tool()
def kelvin_transformation(topic: str = "all") -> str:
    """
    Get Kelvin transformation documentation for open boundary FEM problems.

    The Kelvin transformation maps an unbounded exterior domain to a bounded
    computational domain, enabling FEM solutions without artificial truncation.
    Used with NGSolve for magnetostatic and electromagnetic problems.

    Args:
        topic: Documentation topic. Options:
            "all"            - Complete documentation
            "overview"       - Mathematical foundation and key principles
            "h_formulation"  - H-field perturbation potential formulation
            "a_formulation"  - Vector potential formulation (coils)
            "3d"             - 3D sphere/solid examples
            "adaptive"       - Adaptive mesh refinement with Kelvin
            "identify"       - Periodic boundary Identify() best practices
            "tips"           - Common mistakes and performance tips
    """
    return get_kelvin_documentation(topic)


@mcp.tool()
def radia_usage(topic: str = "all") -> str:
    """
    Get Radia BEM library usage documentation.

    Radia is a boundary element method library for magnetostatic field
    computation. This tool provides API reference, usage patterns, and
    best practices for the Radia Python interface.

    Args:
        topic: Documentation topic. Options:
            "all"                 - Complete documentation
            "overview"            - Library overview and workflow
            "geometry"            - Geometry creation (ObjHexahedron, ObjRecMag, etc.)
            "materials"           - Material definition (MatLin, MatSatIsoFrm, etc.)
            "solving"             - Solver usage (rad.Solve, method selection)
            "parallelization"     - NGSolve TaskManager parallelization
            "fields"              - Field computation (rad.Fld, FldLst, FldInt)
            "mesh_import"         - NGSolve/GMSH/Cubit mesh import
            "best_practices"      - Common patterns and pitfalls
            "peec"                - PEEC conductor analysis (FastHenry, topology, SIBC)
            "ngbem_peec"          - PEEC with ngbem: Loop-Star, shield BEM+SIBC, stabilized EFIE
            "efie_preconditioner" - Calderon preconditioner for EFIE (Andriulli/Schoeberl)
            "fem_verification"    - NGSolve FEM verification results and parameters
            "scalar_potential"    - Phi-reduced scalar potential (Radia source + NGSolve FEM)
            "play_models"         - 6 canonical usage patterns (PM, PM+iron, bkg field, etc.)
            "hysteresis"          - B-input Play model, energy-based hysteresis (MatEnergyHysteresis)
            "build_and_release"   - Build, CI/CD, wheel build, PyPI publish workflow
    """
    return get_radia_documentation(topic)


@mcp.tool()
def ngsolve_usage(topic: str = "all") -> str:
    """
    Get NGSolve finite element library usage documentation.

    NGSolve is a high-performance FEM library used alongside Radia for
    electromagnetic simulation. This tool provides API patterns, best
    practices, and common pitfalls gathered from official tutorials,
    documentation, and community forums.

    Sources:
      - https://docu.ngsolve.org/latest/i-tutorials/
      - https://forum.ngsolve.org/

    Args:
        topic: Documentation topic. Options:
            "all"              - Complete documentation
            "overview"         - Installation, workflow, direct solvers
            "spaces"           - FE spaces (H1, HCurl, HDiv, HDivSurface, SurfaceL2)
            "maxwell"          - Maxwell/magnetostatics (A-formulation, BDDC, materials)
            "solvers"          - Direct & iterative solver selection guide
            "preconditioners"  - BDDC, multigrid, Jacobi, AMG configuration
            "bem"              - Boundary element method (ngbem, LaplaceSL, FEM-BEM coupling)
            "mesh"             - Mesh generation (OCC geometry, STEP import, surface mesh)
            "nonlinear"        - Newton's method for nonlinear problems
            "pitfalls"         - Common mistakes and how to avoid them (40 items)
            "linalg"           - Vector/matrix operations, NumPy interop
            "formulations"     - EM formulations: A, Omega, A-Phi, T-Omega, Kelvin (EMPY)
            "adaptive"         - Adaptive mesh refinement with ZZ error estimator (EMPY)
    """
    return get_ngsolve_documentation(topic)


@mcp.tool()
def induction_heating(topic: str = "all") -> str:
    """
    Get induction heating simulation documentation for NGSolve.

    Complete workflow for electromagnetic induction heating analysis:
    EM eddy current solve (A-Phi) -> Joule heat computation -> transient
    thermal analysis, including Gmsh mesh loading, rotating workpiece,
    VTK output, and post-processing patterns.

    Based on production simulations for industrial induction heating
    (8 kHz, 7000 A, iron/steel workpiece with copper coil).

    Args:
        topic: Documentation topic. Options:
            "all"           - Complete documentation
            "overview"      - Physics overview, parameters, skin depth
            "gmsh_mesh"     - ReadGmsh loading, physical groups, boundary layers
            "eddy_current"  - A-Phi formulation (production code with Gmsh mesh)
            "thermal"       - Transient heat equation (theta-scheme, material props)
            "rotating"      - Rotating workpiece (mesh.SetDeformation)
            "postprocess"   - VTK output, point/line evaluation, CSV/MAT export
            "pitfalls"      - Common mistakes in induction heating simulation
    """
    return get_induction_heating_documentation(topic)


@mcp.tool()
def md2html_usage(topic: str = "all") -> str:
    """
    Get md2html converter documentation.

    md2html.py is a Markdown-to-HTML converter with MathJax support,
    reference link handling, and styled output. Installed at:
    C:/Program Files/Python312/Scripts/md2html.py

    Key features:
    - MathJax LaTeX math ($...$, $$...$$, ```math blocks)
    - Math protection: shields LaTeX from markdown processing
    - ||...|| norm notation auto-converted to \\Vert in math
    - [N] reference links with anchor scrolling to numbered references
    - UTF-8 with cp932 fallback (Japanese Windows)
    - Styled HTML output (dark code blocks, blue tables, responsive)

    Args:
        topic: Documentation topic. Options:
            "all"            - Complete documentation
            "usage"          - Command-line usage and features list
            "implementation" - Architecture, functions, template, CSS details
            "tips"           - LaTeX math patterns, troubleshooting
    """
    return get_md2html_documentation(topic)


@mcp.tool()
def gmsh_builder_usage(topic: str = "all") -> str:
    """
    Get GmshBuilder mesh generation API documentation.

    GmshBuilder is a high-level wrapper around GMSH's OCC (OpenCASCADE)
    kernel, providing ~719 methods for geometry creation, boolean ops,
    mesh control, mesh generation, quality evaluation, and export.
    Part of the Radia project: from radia.gmsh_builder import GmshBuilder

    Args:
        topic: Documentation topic. Options:
            "all"              - Complete documentation
            "overview"         - Library overview, modules, quick start
            "geometry"         - Geometry creation (80 methods: box, cylinder, sphere, etc.)
            "boolean"          - Boolean operations (29 methods: fuse, cut, webcut, etc.)
            "transforms"       - Transforms (26 methods: translate, rotate, mirror, array)
            "mesh_control"     - Mesh control (75 methods: size, fields, transfinite, etc.)
            "generation"       - Mesh generation (48 methods: generate, refine, optimize)
            "quality"          - Mesh quality (27 methods: Jacobian, aspect ratio, etc.)
            "mesh_access"      - Mesh access (75 methods: nodes, elements, Jacobian, basis)
            "physical_groups"  - Physical groups (59 methods: blocks, sidesets, materials)
            "export"           - Export (29 methods: msh, step, vtk, Radia, NGSolve)
            "entity_wrappers"  - Entity queries (55 methods: volume/surface/curve/vertex)
            "advanced"         - Advanced features (110 methods: analysis, groups, views, options)
            "recipes"          - Practical recipes (C-magnet hex, coil, multi-material)
            "best_practices"   - Best practices and common pitfalls
            "cfd_techniques"   - CFD meshing techniques (BL, airfoil, wake, terrain, field composition)
    """
    return get_gmsh_builder_documentation(topic)


# ============================================================
# MCP Prompts
# ============================================================

@mcp.prompt()
def new_radia_example(description: str) -> str:
    """Create a new Radia example script following all project conventions."""
    return (
        f"Create a new Radia example script: {description}\n\n"
        "Follow these conventions:\n"
        "1. Call rad.UtiDelAll() at the end\n"
        "3. Use snake_case naming with demo_ prefix\n"
        "4. Use relative path imports: sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/radia'))\n"
        "5. Export VTK output with same basename as script\n"
        "6. Magnetization in A/m (not Tesla): M = Br / mu_0\n"
        "7. No hardcoded absolute paths\n"
        "8. No Unicode symbols in print statements (use ASCII: ^2, ->, <=)\n"
        "9. Place output files next to the script\n"
        "10. Use rad.ObjBckg(lambda p: [Bx, By, Bz]) for background field (callable, not list)\n"
    )


@mcp.prompt()
def lint_project() -> str:
    """Lint all Python scripts in the Radia project for convention violations."""
    return (
        "Run the lint_radia_directory tool on 'examples' with include_src=True.\n"
        "Report:\n"
        "1. Total files scanned and issues found\n"
        "2. CRITICAL issues (must fix immediately)\n"
        "3. HIGH issues (should fix)\n"
        "4. Summary of patterns (recurring issues across files)\n"
        "5. Suggested fixes for the most common issues\n"
    )


@mcp.prompt()
def ngsolve_radia_workflow(geometry: str) -> str:
    """Set up NGSolve mesh -> Radia open boundary evaluation workflow."""
    return (
        f"Set up an NGSolve -> Radia open boundary field evaluation workflow for: {geometry}\n\n"
        "## Workflow A: NGSolve FEM -> Radia Open Boundary\n"
        "1. Create/import geometry in NGSolve (OCC or GMSH)\n"
        "2. Set up FEM solve (H1/HCurl/HDiv as appropriate)\n"
        "3. Solve for magnetization M per element\n"
        "4. Convert mesh to Radia objects: netgen_mesh_to_radia(mesh, material=...)\n"
        "5. Evaluate field at external points: rad.Fld() (single or batch), rad.FldVTS()\n\n"
        "## Workflow B: Radia Source -> NGSolve FEM (Phi-Reduced)\n"
        "Use when Radia computes H_s (source field from magnets or coils) and\n"
        "NGSolve handles the iron/material response via scalar potential.\n\n"
        "1. Build source in Radia (permanent magnet or coil via equivalent magnetization)\n"
        "2. Create NGSolve mesh with labeled iron regions\n"
        "3. Use ScalarPotentialSolver:\n"
        "   ```python\n"
        "   from radia.scalar_potential_solver import ScalarPotentialSolver\n"
        "   solver = ScalarPotentialSolver(mesh, iron_domains='iron', mu_r=1000)\n"
        "   solver.set_source_from_radia(radia_obj, resolution=31)\n"
        "   solver.solve()  # 'single' for mu_r<5000, 'two' for higher\n"
        "   B = solver.get_B()  # CoefficientFunction\n"
        "   ```\n"
        "4. For coils: model winding as ObjRecMag with M_z = NI/h (A/m)\n\n"
        "Key rules:\n"
        "- Radia always uses meters (no FldUnits call needed)\n"
        "- Use proper Radia objects (ObjHexahedron/ObjTetrahedron), NOT dipole approximation\n"
        "- No Solve() needed if M is already known from NGSolve\n"
        "- For HDiv: use order=2 for best accuracy\n"
        "- Coil equivalent magnetization: M = NI/h along coil axis\n"
    )


@mcp.prompt()
def coil_scalar_potential(description: str) -> str:
    """Set up coil + iron core with phi-reduced scalar potential method."""
    return (
        f"Set up a coil + iron core simulation using phi-reduced scalar potential: {description}\n\n"
        "## Physics\n"
        "The phi-reduced method (Simkin-Trowbridge 1979) splits H into:\n"
        "  H = H_s - grad(phi)\n"
        "where H_s is the source field (coil) computed by Radia, and phi is\n"
        "the correction potential from NGSolve FEM that accounts for iron.\n\n"
        "## Coil Modeling in Radia\n"
        "A solenoid with N turns, current I, height h is modeled as\n"
        "uniformly magnetized blocks with M_z = N*I/h (A/m).\n"
        "For a hollow rectangular coil, decompose into 4 wall blocks:\n"
        "```python\n"
        "M_z = N * I / h  # Equivalent magnetization\n"
        "left  = rad.ObjRecMag([-(a_in+a_out)/2, 0, 0], [a_out-a_in, outer, h], [0,0,M_z])\n"
        "right = rad.ObjRecMag([ (a_in+a_out)/2, 0, 0], [a_out-a_in, outer, h], [0,0,M_z])\n"
        "front = rad.ObjRecMag([0, (a_in+a_out)/2, 0], [bore, a_out-a_in, h], [0,0,M_z])\n"
        "back  = rad.ObjRecMag([0,-(a_in+a_out)/2, 0], [bore, a_out-a_in, h], [0,0,M_z])\n"
        "coil = rad.ObjCnt([left, right, front, back])\n"
        "```\n\n"
        "## Solver Selection\n"
        "- mu_r < 5000: use solve(method='single') -- single reduced potential\n"
        "- mu_r >= 5000: use solve(method='two') -- two-potential (Simkin-Trowbridge)\n\n"
        "## Example: examples/ngsolve_integration/demo_coil_scalar_potential.py\n"
        "## Reference: Simkin & Trowbridge, IJNME, vol.14, pp.423-440, 1979\n"
    )


# ============================================================
# MCP Resources
# ============================================================

@mcp.resource("radia://units")
def radia_units_reference() -> str:
    """Radia unit system quick reference."""
    return (
        "# Radia Unit System\n\n"
        "| Quantity | Unit | Notes |\n"
        "|----------|------|-------|\n"
        "| Length | meters | Always meters, no config needed |\n"
        "| B field | Tesla | |\n"
        "| H field | A/m | |\n"
        "| M (magnetization) | A/m | M = Br / mu_0 (e.g., Br=1.2T -> M=954930 A/m) |\n"
        "| A (vector potential) | T*m | |\n"
        "| mu_0 | 4*pi*1e-7 T*m/A | |\n"
        "| mu_0/(4*pi) | 1e-7 T*m/A | Used in Green's function |\n\n"
        "**CRITICAL**: M is in A/m, NOT Tesla. Do NOT confuse with J (magnetic polarization, Tesla): J = mu_0 * M.\n"
    )


@mcp.resource("radia://api-quick")
def radia_api_quick_reference() -> str:
    """Radia API quick reference card."""
    return (
        "# Radia API Quick Reference\n\n"
        "## Geometry\n"
        "- `rad.ObjRecMag(center, dimensions, magnetization)` - Rectangular magnet\n"
        "- `rad.ObjHexahedron(vertices_8, magnetization)` - Arbitrary hexahedron\n"
        "- `rad.ObjTetrahedron(vertices_4, magnetization)` - Tetrahedron\n"
        "- `rad.ObjWedge(vertices_6, magnetization)` - Wedge\n"
        "- `rad.ObjCnt([obj1, obj2, ...])` - Container\n"
        "- `rad.ObjBckg(callable)` - Background field (MUST be callable)\n\n"
        "## Materials\n"
        "- `rad.MatLin(mu_r)` - Linear isotropic (single arg)\n"
        "- `rad.MatSatIsoTab([[H, B], ...])` - Nonlinear B-H curve\n"
        "- `rad.MatApl(obj, mat)` - Apply material to object\n\n"
        "## Solving\n"
        "- `rad.Solve(obj, precision, max_iter, method)` - method: 0=LU, 1=BiCGSTAB, 2=HACApK\n"
        "- `rad.SolverConfig(hacapk_eps=1e-4, hacapk_leaf=10, ...)` - Solver parameters\n"
        "- `rad.GetSolverConfig()` - Query current solver settings\n\n"
        "## Fields\n"
        "- `rad.Fld(obj, 'b'|'h'|'a'|'phi'|'m', point)` - Single point, shape (3,)\n"
        "- `rad.Fld(obj, 'b'|'h'|'a'|'phi', points)` - Batch, shape (N,3)\n"
        "- `rad.FldVTS(obj, filename, ...)` - VTK structured grid export\n\n"
        "## Cleanup\n"
        "- `rad.UtiDelAll()` - Delete all objects (MUST call at end)\n"
    )


@mcp.resource("radia://materials")
def radia_materials_reference() -> str:
    """Radia material specification quick reference."""
    return (
        "# Radia Material Specification\n\n"
        "## Permanent Magnets (fixed M, no Solve needed)\n"
        "```python\n"
        "# Specify M directly in A/m\n"
        "pm = rad.ObjHexahedron(vertices, [0, 0, 954930])  # Br=1.2T -> M=954930\n"
        "B = rad.Fld(pm, 'b', [0, 0, 0.1])  # No Solve() needed\n"
        "```\n\n"
        "## Linear Soft Iron\n"
        "```python\n"
        "mat = rad.MatLin(1000)  # mu_r = 1000\n"
        "rad.MatApl(iron_obj, mat)\n"
        "```\n\n"
        "## Nonlinear Soft Iron (B-H curve)\n"
        "```python\n"
        "BH = [[0, 0], [100, 0.1], [1000, 1.2], [50000, 2.0]]  # [H(A/m), B(T)]\n"
        "mat = rad.MatSatIsoTab(BH)\n"
        "rad.MatApl(iron_obj, mat)\n"
        "```\n\n"
        "## PM + Soft Iron (requires Solve)\n"
        "```python\n"
        "assembly = rad.ObjCnt([pm, iron])\n"
        "rad.Solve(assembly, 0.0001, 1000, 0)  # 0=LU\n"
        "```\n"
    )


@mcp.resource("radia://play-models")
def radia_play_models_reference() -> str:
    """Radia play model patterns quick reference."""
    return (
        "# Radia Play Models (Typical Usage Patterns)\n\n"
        "| Pattern | Description | Solve? | Solver |\n"
        "|---------|-------------|--------|--------|\n"
        "| A: PM only | ObjRecMag/ObjHexahedron + fixed M | No | - |\n"
        "| B: PM + Iron | PM + MatLin soft iron | Yes | LU (small) |\n"
        "| C: Iron + BkgField | ObjBckg(callable) + MatLin | Yes | LU/BiCG |\n"
        "| D: Nonlinear | MatSatIsoTab B-H curve | Yes | +RelaxParam |\n"
        "| E: Mixed mesh | Hex(6DOF) + Tet(3DOF) via mesh import | Yes | BiCG/HACApK |\n"
        "| F: Large-scale | N>2000, HACApK method=2 | Yes | HACApK |\n\n"
        "## A: PM Only (No Solve)\n"
        "```python\n"
        "rad.UtiDelAll()\n"
        "mag = rad.ObjRecMag([0,0,0], [0.02,0.02,0.01], [0,0,954930])\n"
        "B = rad.Fld(mag, 'b', [0,0,0.03])  # No Solve needed\n"
        "rad.UtiDelAll()\n"
        "```\n\n"
        "## B: PM + Soft Iron\n"
        "```python\n"
        "rad.UtiDelAll()\n"
        "pm = rad.ObjRecMag([0,0,0], [0.02,0.02,0.01], [0,0,954930])\n"
        "iron = rad.ObjRecMag([0,0,0.015], [0.03,0.03,0.01], [0,0,0])\n"
        "rad.MatApl(iron, rad.MatLin(1000))\n"
        "grp = rad.ObjCnt([pm, iron])\n"
        "rad.Solve(grp, 0.0001, 1000, 0)\n"
        "rad.UtiDelAll()\n"
        "```\n\n"
        "## C: Iron in Background Field\n"
        "```python\n"
        "import numpy as np\n"
        "MU_0 = 4 * np.pi * 1e-7\n"
        "rad.UtiDelAll()\n"
        "iron = rad.ObjRecMag([0,0,0], [0.02,0.02,0.02], [0,0,0])\n"
        "rad.MatApl(iron, rad.MatLin(1000))\n"
        "bkg = rad.ObjBckg(lambda p: [0, 0, MU_0 * 200000])  # callable!\n"
        "grp = rad.ObjCnt([iron, bkg])\n"
        "rad.Solve(grp, 0.001, 100, 0)\n"
        "rad.UtiDelAll()\n"
        "```\n\n"
        "Use `radia_usage(topic='play_models')` for all 6 patterns with details.\n"
    )


@mcp.prompt()
def radia_play_model(scenario: str) -> str:
    """Generate a Radia play model script for a given physical scenario."""
    return (
        f"Create a Radia play model script for: {scenario}\n\n"
        "## Instructions\n\n"
        "1. Call `radia_usage(topic='play_models')` to see the 6 canonical patterns\n"
        "2. Choose the best matching pattern for the scenario\n"
        "3. Generate a complete, runnable Python script following these rules:\n"
        "   - `import radia as rad` with proper sys.path\n"
        "   - All coordinates in meters\n"
        "   - M in A/m (not Tesla): M = Br / (4*pi*1e-7)\n"
        "   - `rad.UtiDelAll()` at start AND end\n"
        "   - `rad.ObjBckg(callable)` -- MUST be callable, not list\n"
        "   - No `rad.FldUnits()` call (removed)\n"
        "   - ASCII only in print statements (no Unicode)\n"
        "   - Export VTS with `rad.FldVTS()` using script basename\n\n"
        "## Solver Selection\n\n"
        "- N < 500 elements: method=0 (LU)\n"
        "- 500 < N < 2000: method=1 (BiCGSTAB)\n"
        "- N > 2000: method=2 (HACApK), with `rad.SolverConfig(hacapk_eps=1e-4, hacapk_leaf=10, hacapk_eta=2.0)`\n\n"
        "## Element Types\n\n"
        "- ObjRecMag: optimized rectangular blocks (3 DOF, MMM)\n"
        "- ObjHexahedron: arbitrary hex (6 DOF, MSC) -- better accuracy\n"
        "- ObjTetrahedron: tet (3 DOF, MMM) -- unstructured meshes\n"
        "- For complex geometry: use netgen_mesh_to_radia() or gmsh_to_radia()\n"
    )


@mcp.prompt()
def gmsh_builder_mesh(description: str) -> str:
    """Create a mesh generation script using GmshBuilder."""
    return (
        f"Create a mesh generation script using GmshBuilder: {description}\n\n"
        "## Instructions\n\n"
        "1. Call `gmsh_builder_usage(topic='recipes')` for practical examples\n"
        "2. Generate a complete, runnable Python script following these rules:\n"
        "   - `from radia.gmsh_builder import GmshBuilder`\n"
        "   - Use `with GmshBuilder(verbose=False) as gb:` context manager\n"
        "   - All coordinates in meters\n"
        "   - For hex mesh: use set_divisions() + generate('hex')\n"
        "   - For tet mesh: use set_mesh_size() + generate('tet')\n"
        "   - For multi-body: use gb.fragment(vol_ids) before meshing\n"
        "   - For Radia: use gb.to_radia(mu_r=...) or gb.to_radia_with_materials()\n"
        "   - For export: gb.export('output.msh')\n\n"
        "## Hex Meshing Recipe\n\n"
        "```python\n"
        "with GmshBuilder(verbose=False) as gb:\n"
        "    box = gb.add_box([0,0,0], [0.1, 0.02, 0.03])\n"
        "    parts = gb.webcut_plane(box, 'x', 0.03)  # split for structured mesh\n"
        "    gb.set_divisions_all(4, 3, 3)\n"
        "    gb.generate('hex')\n"
        "    radia_obj = gb.to_radia(mu_r=1000)\n"
        "```\n"
    )


def _selftest():
    """Run lint on examples/ directory, or built-in fixtures as fallback.

    When run from a project root that has examples/, lints that directory.
    Otherwise, uses built-in test fixtures to verify all rules work correctly.
    This allows --selftest to run in CI without depending on external files.
    """
    print("=" * 70)
    print("Radia Lint Self-Test")
    print("=" * 70)
    print()

    examples_dir = PROJECT_ROOT / "examples"
    if examples_dir.exists():
        result = lint_radia_directory("examples", include_src=True)
        print(result)
        return

    # Fallback: use built-in fixtures from the tests/ directory
    fixtures_dir = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures"
    if not fixtures_dir.exists():
        # Also try installed package location
        fixtures_dir = Path(__file__).parent / "fixtures"

    if fixtures_dir.exists():
        print(f"examples/ not found. Using built-in fixtures: {fixtures_dir}")
        print()
        py_files = sorted(fixtures_dir.glob("*.py"))
        total_findings = 0
        total_files = 0
        for py_file in py_files:
            findings = _lint_file(str(py_file))
            print(_format_findings(str(py_file), findings))
            print()
            total_findings += len(findings)
            total_files += 1

        print("=" * 70)
        print(f"Summary: {total_findings} finding(s) in {total_files} fixture file(s)")

        # Verify: bad files should have findings, clean file should not
        for py_file in py_files:
            findings = _lint_file(str(py_file))
            name = py_file.name
            if name.startswith("bad_") and len(findings) == 0:
                print(f"  WARNING: {name} expected findings but got none")
            if name.startswith("clean_") and len(findings) > 0:
                print(f"  FAIL: {name} should be clean but got {len(findings)} finding(s)")
                sys.exit(1)

        print("Self-test PASSED")
    else:
        print(f"SKIP: No examples/ directory and no fixtures found.")
        print("Run from the project root, or install test fixtures.")


def main():
    """Entry point for mcp-server-radia console script."""
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        _selftest()
    else:
        mcp.run(transport="stdio")


if __name__ == '__main__':
    main()
