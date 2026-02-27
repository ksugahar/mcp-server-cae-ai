"""
Radia Project MCP Server

Provides tools for:
- Linting Python scripts against Radia + NGSolve conventions (21 rules)
- Radia BEM library usage documentation
- NGSolve FEM usage documentation (12 topics incl. EM formulations, adaptive)
- Kelvin transformation reference for open boundary FEM
- ngsolve-sparsesolv (ICCG) solver documentation

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
from .sparsesolv_knowledge import (
    SPARSESOLV_OVERVIEW, SPARSESOLV_API, SPARSESOLV_EXAMPLES,
    SPARSESOLV_ABMC, SPARSESOLV_BEST_PRACTICES,
    SPARSESOLV_BUILD, get_full_documentation as get_sparsesolv_docs,
)
from .kelvin_knowledge import get_kelvin_documentation
from .radia_knowledge import get_radia_documentation
from .ngsolve_knowledge import get_ngsolve_documentation

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
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MODERATE': 2, 'LOW': 3, 'ERROR': -1}
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
    - Missing rad.FldUnits() initialization (MODERATE)
    - PEEC n_seg too low for circular coil coupling (MODERATE)
    - Classical EFIE 1/kappa^2 low-frequency breakdown (MODERATE)
    - PEEC P/(jw) low-frequency breakdown (HIGH)
    - Docstrings hardcoding "in mm" (MODERATE)
    - Outdated build/Release path imports (LOW)

    NGSolve checks:
    - BEM on HDivSurface without .Trace() (CRITICAL)
    - HCurl magnetostatics without nograds=True (HIGH)
    - BDDC preconditioner registered after assembly (MODERATE)
    - Overwriting x/y/z coordinate variables (MODERATE)
    - Direct .vec assignment without .data (MODERATE)
    - 2D OCC geometry without dim=2 (MODERATE)
    - CG on A-Omega saddle-point system (MODERATE)
    - Kelvin domain without bonus_intorder (MODERATE)
    - VectorH1 for electromagnetic fields (MODERATE)
    - PINVIT/LOBPCG without gradient projection (MODERATE)

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
    summary_by_severity = {'CRITICAL': 0, 'HIGH': 0, 'MODERATE': 0, 'LOW': 0}

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
        f"{summary_by_severity['LOW']} LOW",
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
            'rule': 'missing-fldunits',
            'severity': 'MODERATE',
            'description': (
                "Example scripts should call rad.FldUnits('m') at initialization "
                "for consistency with NGSolve and project convention."
            ),
            'fix': "Add rad.FldUnits('m') after import radia as rad.",
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
    ]

    lines = ["Radia + NGSolve Lint Rules", "=" * 50, ""]
    for r in rules_info:
        lines.append(f"[{r['severity']}] {r['rule']}")
        lines.append(f"  {r['description']}")
        lines.append(f"  Fix: {r['fix']}")
        lines.append("")

    return '\n'.join(lines)


@mcp.tool()
def sparsesolv_usage(topic: str = "all") -> str:
    """
    Get ngsolve-sparsesolv usage documentation.

    ngsolve-sparsesolv is a standalone pybind11 add-on module for NGSolve
    that provides IC, SGS, and BDDC preconditioners with ICCG, SGSMRTR,
    and CG solvers. Supports auto-shift IC, complex systems, ABMC parallel
    triangular solves, and BDDC domain decomposition.

    Repository: https://github.com/ksugahar/ngsolve-sparsesolv

    Args:
        topic: Documentation topic to retrieve. Options:
            "all"            - Complete documentation
            "overview"       - Library overview, add-on positioning, features
            "api"            - Python API reference (solvers, preconditioners, BDDC)
            "examples"       - Usage examples (Poisson, curl-curl, complex, BDDC, etc.)
            "abmc"           - ABMC ordering: parallel triangular solve optimization
            "best_practices" - Preconditioner selection, complex systems, tips
            "build"          - Build and installation instructions
    """
    topic = topic.lower().strip()
    if topic == "all":
        return get_sparsesolv_docs()
    elif topic == "overview":
        return SPARSESOLV_OVERVIEW
    elif topic == "api":
        return SPARSESOLV_API
    elif topic == "examples":
        return SPARSESOLV_EXAMPLES
    elif topic == "abmc":
        return SPARSESOLV_ABMC
    elif topic in ("best_practices", "best-practices", "bestpractices", "tips"):
        return SPARSESOLV_BEST_PRACTICES
    elif topic == "build":
        return SPARSESOLV_BUILD
    else:
        return (
            f"Unknown topic: '{topic}'. "
            "Available topics: all, overview, api, examples, abmc, best_practices, build"
        )


@mcp.tool()
def sparsesolv_code_example(problem_type: str = "poisson") -> str:
    """
    Get a ready-to-use ngsolve-sparsesolv code example.

    Args:
        problem_type: Type of problem. Options:
            "poisson"     - 2D Poisson with ICCG
            "curlcurl"    - 3D curl-curl with auto-shift IC (electromagnetic)
            "eddy"        - Complex eddy current problem
            "precond"     - Using IC/SGS preconditioners with NGSolve CGSolver
            "divergence"  - Divergence detection example
            "bddc"        - BDDC preconditioner with CG
    """
    problem_type = problem_type.lower().strip()

    if problem_type == "poisson":
        return '''# 2D Poisson Problem with ICCG
from ngsolve import *
from sparsesolv_ngsolve import SparseSolvSolver

mesh = Mesh(unit_square.GenerateMesh(maxh=0.1))
fes = H1(mesh, order=2, dirichlet="bottom|right|top|left")
u, v = fes.TnT()

a = BilinearForm(fes)
a += grad(u) * grad(v) * dx
a.Assemble()

f = LinearForm(fes)
f += 2 * pi * pi * sin(pi * x) * sin(pi * y) * v * dx
f.Assemble()

# Solve with ICCG
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-10, maxiter=2000)

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec

result = solver.last_result
print(f"Converged: {result.converged}, Iterations: {result.iterations}")
print(f"Final residual: {result.final_residual:.2e}")
'''

    elif problem_type == "curlcurl":
        return '''# 3D Curl-Curl (Electromagnetic) with Auto-Shift ICCG
from ngsolve import *
from netgen.occ import Box, Pnt
from sparsesolv_ngsolve import SparseSolvSolver

box = Box(Pnt(0, 0, 0), Pnt(1, 1, 1))
for face in box.faces:
    face.name = "outer"
mesh = Mesh(box.GenerateMesh(maxh=0.4))

fes = HCurl(mesh, order=1, dirichlet="outer", nograds=True)
u, v = fes.TnT()

a = BilinearForm(fes)
a += curl(u) * curl(v) * dx
a.Assemble()

f = LinearForm(fes)
f += CF((0, 0, 1)) * v * dx
f.Assemble()

# ICCG with auto-shift for semi-definite curl-curl system
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-8, maxiter=2000, shift=1.0)
solver.auto_shift = True         # Critical for semi-definite systems
solver.diagonal_scaling = True   # Improve conditioning

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec

result = solver.last_result
print(f"Converged: {result.converged}, Iterations: {result.iterations}")
'''

    elif problem_type == "eddy":
        return '''# Complex Eddy Current Problem
from ngsolve import *
from netgen.occ import Box, Pnt, OCCGeometry
from sparsesolv_ngsolve import SparseSolvSolver

box = Box(Pnt(0, 0, 0), Pnt(1, 1, 1))
for face in box.faces:
    face.name = "outer"
mesh = Mesh(OCCGeometry(box).GenerateMesh(maxh=0.3))

# Complex-valued HCurl space for eddy currents
fes = HCurl(mesh, order=1, complex=True, dirichlet="outer", nograds=True)
u, v = fes.TnT()

# Complex-symmetric: curl-curl + j*omega*sigma*mass
a = BilinearForm(fes)
a += InnerProduct(curl(u), curl(v)) * dx
a += 1j * InnerProduct(u, v) * dx
a.Assemble()

f = LinearForm(fes)
f += InnerProduct(CF((1, 0, 0)), v) * dx
f.Assemble()

# Factory auto-dispatches to complex solver
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-8, maxiter=5000,
                           save_best_result=True)

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec

result = solver.last_result
print(f"Converged: {result.converged}, Iterations: {result.iterations}")
'''

    elif problem_type == "precond":
        return '''# Using IC/SGS Preconditioners with NGSolve CGSolver
from ngsolve import *
from ngsolve.krylovspace import CGSolver
from sparsesolv_ngsolve import ICPreconditioner, SGSPreconditioner

mesh = Mesh(unit_square.GenerateMesh(maxh=0.05))
fes = H1(mesh, order=2, dirichlet="bottom|right|top|left")
u, v = fes.TnT()

a = BilinearForm(fes)
a += grad(u) * grad(v) * dx
a.Assemble()

f = LinearForm(fes)
f += 1 * v * dx
f.Assemble()

gfu = GridFunction(fes)

# Option 1: IC preconditioner
pre_ic = ICPreconditioner(a.mat, freedofs=fes.FreeDofs(), shift=1.05)
pre_ic.Update()
inv = CGSolver(a.mat, pre_ic, printrates=True, tol=1e-10, maxiter=2000)
gfu.vec.data = inv * f.vec
print(f"IC+CG done")

# Option 2: SGS preconditioner
pre_sgs = SGSPreconditioner(a.mat, freedofs=fes.FreeDofs())
pre_sgs.Update()
inv = CGSolver(a.mat, pre_sgs, printrates=False, tol=1e-10)
gfu.vec.data = inv * f.vec
print(f"SGS+CG done")
'''

    elif problem_type == "divergence":
        return '''# Divergence Detection and Early Termination
from ngsolve import *
from sparsesolv_ngsolve import SparseSolvSolver

mesh = Mesh(unit_square.GenerateMesh(maxh=0.1))
fes = H1(mesh, order=2, dirichlet="bottom|right|top|left")
u, v = fes.TnT()

a = BilinearForm(fes)
a += grad(u) * grad(v) * dx
a.Assemble()

f = LinearForm(fes)
f += 1 * v * dx
f.Assemble()

solver = SparseSolvSolver(a.mat, method="CG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-12, maxiter=5000)
solver.divergence_check = True
solver.divergence_threshold = 10.0   # residual > best * 10 = stagnation
solver.divergence_count = 20         # stop after 20 bad iterations

gfu = GridFunction(fes)
result = solver.Solve(f.vec, gfu.vec)
print(f"Converged: {result.converged}")
print(f"Iterations: {result.iterations} (max: 5000)")
print(f"Final residual: {result.final_residual:.2e}")
'''

    elif problem_type == "bddc":
        return '''# BDDC Preconditioner with CG (mesh-independent convergence)
from ngsolve import *
from ngsolve.krylovspace import CGSolver
from sparsesolv_ngsolve import BDDCPreconditioner

mesh = Mesh(unit_square.GenerateMesh(maxh=0.05))
fes = H1(mesh, order=2, dirichlet="bottom|right|top|left")
u, v = fes.TnT()

a = BilinearForm(fes)
a += grad(u) * grad(v) * dx
a.Assemble()

f = LinearForm(fes)
f += 1 * v * dx
f.Assemble()

# BDDC requires BilinearForm + FESpace (not just the matrix)
pre = BDDCPreconditioner(a, fes, coarse_inverse="sparsecholesky")
pre.Update()

print(f"Wirebasket DOFs: {pre.num_wirebasket_dofs}")
print(f"Interface DOFs: {pre.num_interface_dofs}")

# Typically converges in ~2 iterations (mesh-independent!)
inv = CGSolver(a.mat, pre, tol=1e-10, maxiter=100, printrates=True)

gfu = GridFunction(fes)
gfu.vec.data = inv * f.vec
'''

    else:
        return (
            f"Unknown problem type: '{problem_type}'. "
            "Available: poisson, curlcurl, eddy, precond, divergence, bddc"
        )


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
            "all"              - Complete documentation
            "overview"         - Library overview and workflow
            "geometry"         - Geometry creation (ObjHexahedron, ObjRecMag, etc.)
            "materials"        - Material definition (MatLin, MatSatIsoFrm, etc.)
            "solving"          - Solver usage (rad.Solve, method selection)
            "fields"           - Field computation (rad.Fld, FldLst, FldInt)
            "mesh_import"      - NGSolve/GMSH/Cubit mesh import
            "best_practices"   - Common patterns and pitfalls
            "peec"             - PEEC conductor analysis (FastHenry, topology, SIBC)
            "ngbem_peec"           - PEEC with ngbem: Loop-Star, shield BEM+SIBC, stabilized EFIE
            "efie_preconditioner" - Calderon preconditioner for EFIE (Andriulli/Schoeberl)
            "fem_verification"    - NGSolve FEM verification results and parameters
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
            "pitfalls"         - Common mistakes and how to avoid them (35 items)
            "linalg"           - Vector/matrix operations, NumPy interop
            "formulations"     - EM formulations: A, Omega, A-Phi, T-Omega, Kelvin (EMPY)
            "adaptive"         - Adaptive mesh refinement with ZZ error estimator (EMPY)
    """
    return get_ngsolve_documentation(topic)


def _selftest():
    """Run lint on the project's examples/ and src/radia/ directories."""
    print("=" * 70)
    print("Radia Lint Self-Test")
    print("=" * 70)
    print()

    result = lint_radia_directory("examples", include_src=True)
    print(result)


def main():
    """Entry point for mcp-server-radia console script."""
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        _selftest()
    else:
        mcp.run(transport="stdio")


if __name__ == '__main__':
    main()
