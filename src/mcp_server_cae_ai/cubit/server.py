"""
Cubit Mesh Export MCP Server

Provides tools for:
- Export function documentation (Gmsh, VTK, Nastran, MEG, Netgen, Exodus)
- Netgen/NGSolve high-order curving workflows (SetGeomInfo, name-based)
- Cubit scripting patterns and best practices
- Cubit Python API reference (600+ functions, entity classes)
- Linting Python scripts for Cubit export convention violations

Usage:
    python server.py              # Start MCP server (stdio transport)
    python server.py --selftest   # Run self-test on examples/
"""

import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Import knowledge bases and rules (relative imports for pip package)
from .rules import ALL_RULES
from .export_knowledge import get_export_documentation
from .netgen_workflow_knowledge import get_netgen_documentation
from .cubit_scripting_knowledge import get_cubit_documentation
from .cubit_forum_tips import get_forum_tips
from .cubit_api_reference import get_api_reference

# Create MCP server
mcp = FastMCP("cubit-export")

# Project root (current working directory for pip-installed package)
PROJECT_ROOT = Path.cwd()


# ============================================================
# Lint helpers
# ============================================================

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


# ============================================================
# Netgen code examples
# ============================================================

EXAMPLES = {}

EXAMPLES['cylinder'] = '''# Cylinder with SetGeomInfo (Netgen high-order curving)
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import Mesh, Integrate, CF, BND
import cubit
import cubit_mesh_export

R, H, ORDER = 0.5, 2.0, 3

cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f"create cylinder height {H} radius {R}")

# STEP export/reimport (seam alignment)
step_file = "cylinder.step"
cubit.cmd(f'export step "{step_file}" overwrite')
cubit.cmd("reset")
cubit.cmd(f'import step "{step_file}" heal')

# Mesh
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.15")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

# Export to Netgen with geometry
geo = OCCGeometry(step_file)
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)

# SetGeomInfo
cubit_mesh_export.set_cylinder_geominfo(
    ngmesh, radius=R, height=H, center=(0, 0, 0), axis='z')

# Curve and verify
mesh = Mesh(ngmesh)
mesh.Curve(ORDER)

expected_vol = math.pi * R**2 * H
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol-expected_vol)/expected_vol*100:.4f}%")
'''

EXAMPLES['sphere'] = '''# Sphere with SetGeomInfo
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

R, ORDER = 0.5, 3

cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f"create sphere radius {R}")
cubit.cmd('export step "sphere.step" overwrite')
cubit.cmd("reset")
cubit.cmd('import step "sphere.step" heal')

cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.1")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

geo = OCCGeometry("sphere.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)
cubit_mesh_export.set_sphere_geominfo(ngmesh, radius=R, center=(0, 0, 0))

mesh = Mesh(ngmesh)
mesh.Curve(ORDER)

expected_vol = 4/3 * math.pi * R**3
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol-expected_vol)/expected_vol*100:.4f}%")
'''

EXAMPLES['torus'] = '''# Torus with SetGeomInfo
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

R_MAJOR, R_MINOR, ORDER = 1.0, 0.3, 3

cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f"create torus major {R_MAJOR} minor {R_MINOR}")
cubit.cmd('export step "torus.step" overwrite')
cubit.cmd("reset")
cubit.cmd('import step "torus.step" heal')

cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.08")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

geo = OCCGeometry("torus.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)
cubit_mesh_export.set_torus_geominfo(
    ngmesh, major_radius=R_MAJOR, minor_radius=R_MINOR,
    center=(0, 0, 0), axis='z')

mesh = Mesh(ngmesh)
mesh.Curve(ORDER)

expected_vol = 2 * math.pi**2 * R_MAJOR * R_MINOR**2
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol-expected_vol)/expected_vol*100:.4f}%")
'''

EXAMPLES['cone'] = '''# Cone with SetGeomInfo
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

R_BASE, H, ORDER = 0.5, 2.0, 3

cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f"create cone height {H} radius {R_BASE} top 0")
cubit.cmd('export step "cone.step" overwrite')
cubit.cmd("reset")
cubit.cmd('import step "cone.step" heal')

cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.1")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

geo = OCCGeometry("cone.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)
cubit_mesh_export.set_cone_geominfo(
    ngmesh, base_radius=R_BASE, height=H, center=(0, 0, 0), axis='z')

mesh = Mesh(ngmesh)
mesh.Curve(ORDER)

expected_vol = 1/3 * math.pi * R_BASE**2 * H
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol-expected_vol)/expected_vol*100:.4f}%")
'''

EXAMPLES['hex_cylinder'] = '''# Hex-meshed Cylinder with SetGeomInfo
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

R, H = 0.5, 2.0

cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f"create cylinder height {H} radius {R}")
cubit.cmd('export step "hex_cyl.step" overwrite')
cubit.cmd("reset")
cubit.cmd('import step "hex_cyl.step" heal')

# Hex meshing requires webcut for cylinder
cubit.cmd("webcut volume all with plane xplane")
cubit.cmd("webcut volume all with plane yplane")
cubit.cmd("merge all")
cubit.cmd("volume all scheme auto")
cubit.cmd("volume all size 0.15")
cubit.cmd("mesh volume all")

cubit.cmd("block 1 add hex all")
cubit.cmd("block 2 add quad all")

geo = OCCGeometry("hex_cyl.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)
cubit_mesh_export.set_cylinder_geominfo(
    ngmesh, radius=R, height=H, center=(0, 0, 0), axis='z')

mesh = Mesh(ngmesh)
mesh.Curve(3)

expected_vol = math.pi * R**2 * H
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol-expected_vol)/expected_vol*100:.4f}%")
'''

EXAMPLES['complex_named'] = '''# Complex Geometry with Name-based Face Mapping
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry, Box, Cylinder, gp_Ax2, gp_Dir, gp_Pnt
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

BRICK_SIZE, R_HOLE, ORDER = 2.0, 0.3, 3

# Step 1: Create geometry in OCC (NOT Cubit)
brick = Box(gp_Pnt(-1, -1, -1), gp_Pnt(1, 1, 1))
cyl = Cylinder(gp_Ax2(gp_Pnt(0, 0, -2), gp_Dir(0, 0, 1)), R_HOLE, 4)
shape = brick - cyl

# Step 2: Name OCC faces (critical!)
cubit_mesh_export.name_occ_faces(shape)

# Step 3: Export STEP from OCC
shape.WriteStep("complex.step")
geo = OCCGeometry("complex.step")

# Step 4: Import into Cubit and mesh
cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd('import step "complex.step" noheal')
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.15")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

# Step 5: Export with name-based mapping
ngmesh = cubit_mesh_export.export_netgen_with_names(cubit, geo)

# Step 6: SetGeomInfo for cylindrical hole
cubit_mesh_export.set_cylinder_geominfo(
    ngmesh, radius=R_HOLE, height=BRICK_SIZE, center=(0, 0, 0), axis='z')

# Step 7: Curve and verify
mesh = Mesh(ngmesh)
mesh.Curve(ORDER)

expected_vol = BRICK_SIZE**3 - math.pi * R_HOLE**2 * BRICK_SIZE
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol-expected_vol)/expected_vol*100:.4f}%")
'''

EXAMPLES['gmsh_2nd_order'] = '''# Gmsh 2nd Order Alternative (Simplest Workflow)
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.read_gmsh import ReadGmsh
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

R = 1.0

cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f"create sphere radius {R}")
cubit.cmd("volume 1 scheme tetmesh")
cubit.cmd("volume 1 size 0.2")
cubit.cmd("mesh volume 1")

# Register blocks with 2nd order elements
cubit.cmd("block 1 add tet all in volume 1")
cubit.cmd("block 1 element type tetra10")
cubit.cmd("block 2 add tri all")
cubit.cmd("block 2 element type tri6")

# Export to Gmsh v2.2
cubit_mesh_export.export_gmsh_v2(cubit, "sphere_2nd.msh")

# Read into NGSolve (no geometry reference needed!)
mesh = Mesh(ReadGmsh("sphere_2nd.msh"))

expected_vol = 4/3 * math.pi * R**3
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol-expected_vol)/expected_vol*100:.4f}%")
'''

EXAMPLES['poisson_sphere'] = '''# Complete FEM Example: Poisson on Sphere
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import *
import cubit
import cubit_mesh_export

R, ORDER = 1.0, 3

# --- Mesh generation ---
cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f"create sphere radius {R}")
cubit.cmd('export step "sphere.step" overwrite')
cubit.cmd("reset")
cubit.cmd('import step "sphere.step" heal')
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.2")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd('block 1 name "domain"')
cubit.cmd("block 2 add tri all")
cubit.cmd('block 2 name "boundary"')

# --- Netgen export with curving ---
geo = OCCGeometry("sphere.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)
cubit_mesh_export.set_sphere_geominfo(ngmesh, radius=R)

mesh = Mesh(ngmesh)
mesh.Curve(ORDER)

# --- Solve Poisson equation ---
fes = H1(mesh, order=ORDER, dirichlet="boundary")
u, v = fes.TnT()

a = BilinearForm(fes)
a += grad(u) * grad(v) * dx
a.Assemble()

f = LinearForm(fes)
f += 1 * v * dx
f.Assemble()

gfu = GridFunction(fes)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs()) * f.vec

print(f"DOFs: {fes.ndof}")
print(f"Integral of solution: {Integrate(gfu, mesh):.6f}")
'''


# ============================================================
# Tools
# ============================================================

@mcp.tool()
def cubit_export_docs(format: str = "all") -> str:
	"""
	Get documentation for cubit_mesh_export export functions.

	Provides API reference, parameter tables, supported element types,
	and usage examples for each mesh export format.

	Args:
	    format: Export format to document. Options:
	        "all"            - Function overview + format comparison
	        "overview"       - Function overview table
	        "gmsh_v2"        - Gmsh v2.2 format (export_Gmsh_ver2)
	        "gmsh_v4"        - Gmsh v4.1 format (export_Gmsh_ver4)
	        "netgen"         - Netgen mesh (export_NetgenMesh)
	        "vtk"            - VTK Legacy format (export_vtk)
	        "vtu"            - VTK XML format (export_vtu)
	        "nastran"        - Nastran BDF format (export_Nastran)
	        "meg"            - MEG ELF/MAGIC format (export_meg)
	        "exodus"         - Exodus II format (export_exodus)
	        "comparison"     - Format comparison and decision matrix
	        "decision_guide" - Interactive decision tree for format selection
	"""
	return get_export_documentation(format)


@mcp.tool()
def netgen_workflow_guide(workflow: str = "overview") -> str:
	"""
	Get step-by-step Netgen/NGSolve workflow documentation.

	The Netgen high-order curving workflow is complex, involving Cubit meshing,
	OCC geometry, STEP exchange, and SetGeomInfo UV parameters. This tool
	provides detailed guidance for each workflow variant.

	Args:
	    workflow: Workflow to document. Options:
	        "overview"          - Decision tree: which workflow to use
	        "simple_cylinder"   - Cylinder: STEP reimport + SetGeomInfo
	        "simple_sphere"     - Sphere workflow
	        "simple_torus"      - Torus workflow
	        "simple_cone"       - Cone workflow
	        "complex_named"     - Complex geometry: OCC + name_occ_faces
	        "multi_surface"     - Multiple curved surface types in one shape
	        "freeform"          - Handling unsupported surface types (BSpline, etc.)
	        "accuracy"          - Accuracy guide: order selection and verification
	        "gmsh_2nd_order"    - Alternative: Gmsh 2nd order (simplest)
	        "setgeominfo_api"   - SetGeomInfo function reference
	        "seam_problem"      - ACIS/OCC seam line problem and solutions
	        "troubleshooting"   - Common errors and fixes
	        "tolerance_tuning"  - How to tune tol parameter for SetGeomInfo
	        "uv_math"           - UV computation mathematics (atan2, etc.)
	"""
	return get_netgen_documentation(workflow)


@mcp.tool()
def netgen_code_example(shape: str = "cylinder") -> str:
	"""
	Get a ready-to-run Netgen export code example.

	Returns a complete Python script for exporting Cubit mesh to Netgen
	with high-order curving. Each example follows the recommended workflow.

	Args:
	    shape: Geometry shape for the example. Options:
	        "cylinder"       - Cylinder with SetGeomInfo
	        "sphere"         - Sphere with SetGeomInfo
	        "torus"          - Torus with SetGeomInfo
	        "cone"           - Cone with SetGeomInfo
	        "hex_cylinder"   - Hex-meshed cylinder
	        "complex_named"  - Boolean geometry with name-based workflow
	        "gmsh_2nd_order" - Gmsh 2nd order alternative (simplest)
	        "poisson_sphere" - Complete FEM: Poisson equation on sphere
	"""
	shape = shape.lower().strip()
	if shape in EXAMPLES:
		return EXAMPLES[shape]
	else:
		return (
			f"Unknown shape: '{shape}'. "
			f"Available: {', '.join(EXAMPLES.keys())}"
		)


@mcp.tool()
def cubit_scripting_guide(topic: str = "all") -> str:
	"""
	Get Cubit Python scripting documentation for mesh generation.

	Covers block registration, element order control, mesh schemes,
	STEP exchange, initialization, 2D meshing, troubleshooting, and common pitfalls.

	Args:
	    topic: Documentation topic. Options:
	        "all"                - Complete scripting guide
	        "overview"           - Why Cubit, element types, workflow
	        "blocks"             - Block registration (mesh elements vs geometry)
	        "blocks_only_policy" - Why blocks only (no nodesets/sidesets)
	        "element_order"      - 1st/2nd order, connectivity APIs
	        "mesh_schemes"       - tetmesh, map, sweep, trimesh
	        "step_exchange"      - STEP import/export, heal vs noheal
	        "initialization"     - Cubit Python init boilerplate
	        "mixed_elements"     - Mixed element types and warnings
	        "common_mistakes"    - Frequent Cubit API pitfalls
	        "hex_workflow"       - Hexahedral mesh generation
	        "tet_workflow"       - Tetrahedral mesh generation
	        "2d_mesh"            - 2D surface meshing and export
	        "troubleshooting"    - Common problems and debugging
	        "design_philosophy"  - Why module reads Python API, not built-in export
	        "aprepro_journal"    - Running scripts from Cubit via play command
	"""
	return get_cubit_documentation(topic)


@mcp.tool()
def cubit_forum_tips(topic: str = "all") -> str:
	"""
	Get practical Cubit meshing tips sourced from the Coreform forum.

	Real-world solutions to common meshing problems, collected from
	forum.coreform.com discussions with high view counts.

	Args:
	    topic: Tip category. Options:
	        "all"                  - All tips
	        "mesh_quality"         - Smoothing, Jacobian fixes, quality diagnostics
	        "biased_graded"        - Curve bias, circle scheme, auto factor, refinement
	        "hex_decomposition"    - Webcut patterns, torus meshing, embedded spheres
	        "sweep_tips"           - Transform translate, copy mesh, interval matching
	        "parallel_meshing"     - HPC tetmesher, multiprocessing pattern
	        "python_api"           - Entity names, connectivity, batch mode, STL engine
	        "export_tips"          - Abaqus parts, Exodus sizing, LS-DYNA
	        "geometry_healing"     - STEP/STL import, heal, stitch, bounding voids
	        "sculpt_workflow"      - Sculpt setup, command-line, capture, HEX27
	        "boundary_layer"       - BL setup, reversal nodes fix, composite surface
	        "python_performance"   - Performance settings, batch queries, entity tracking
	        "quality_diagnostics"  - Quality extraction, bad element selection, normals
	        "solver_workflows"     - FEniCS, VTK, CalculiX, OpenFOAM integration
	        "advanced_meshing"     - Void, crack, dome, hemisphere, topography, THex
	"""
	return get_forum_tips(topic)


@mcp.tool()
def cubit_api_reference(topic: str = "all") -> str:
	"""
	Get the Cubit Python API reference (cubit.* functions and entity classes).

	Organized reference of 600+ CubitInterface namespace functions and
	entity class methods from the official Coreform Cubit 2025.8 docs.

	Args:
	    topic: API category. Options:
	        "all"                  - All API categories
	        "core"                 - cmd, parse_cubit_list, init, naming, APREPRO
	        "geometry_queries"     - center_point, bounding_box, normals, topology
	        "mesh_access"          - connectivity, nodal_coordinates, element access
	        "blocks_sets"          - block/nodeset/sideset/group functions
	        "mesh_settings"        - scheme, size, intervals, quality, tetmesh
	        "entity_classes"       - Volume, Surface, Curve, Vertex class methods
	        "graphics_selection"   - Graphics control, selection, journaling
	        "advanced"             - Merge detection, geometry analysis, Sculpt
	"""
	return get_api_reference(topic)


@mcp.tool()
def lint_cubit_script(filepath: str) -> str:
	"""
	Lint a Python script for Cubit mesh export convention violations.

	Checks for (16 rules):
	- Missing block registration before export (CRITICAL)
	- Missing mesh command before export (CRITICAL)
	- Geometry block with 2nd order conversion (HIGH)
	- Missing cubit.init() (HIGH)
	- get_connectivity instead of get_expanded_connectivity for 2nd order (HIGH)
	- Element type set before adding to block (HIGH)
	- SetGeomInfo without geometry reference (HIGH)
	- nodeset/sideset usage with blocks-only export formats (HIGH)
	- export_netgen_with_names without name_occ_faces (HIGH)
	- Missing STEP reimport for curved surfaces (MODERATE)
	- Name-based workflow with 'heal' instead of 'noheal' (MODERATE)
	- Hardcoded absolute paths (MODERATE)
	- Missing boundary element block for Netgen (MODERATE)
	- Wrong file extension for export format (MODERATE)
	- mesh.Curve() without SetGeomInfo (MODERATE)
	- Blocks registered without names (LOW)

	Args:
	    filepath: Absolute or relative path to the Python file to check.
	"""
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
def lint_cubit_directory(directory: str = "examples") -> str:
	"""
	Lint all Python scripts in a directory for Cubit export convention violations.

	Recursively scans .py files and reports findings grouped by file.

	Args:
	    directory: Directory path relative to project root (default: "examples").
	"""
	d = Path(directory)
	if not d.is_absolute():
		d = PROJECT_ROOT / d

	if not d.exists():
		return f"Error: Directory not found: {d}"

	# Collect all .py files
	py_files = sorted(d.rglob("*.py"))

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
		f"Cubit Export Lint Report: {len(py_files)} files scanned, {total_findings} issues found.",
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


# ============================================================
# New tools: script generation and mesh quality
# ============================================================

SCRIPT_TEMPLATES = {}

SCRIPT_TEMPLATES['tet_netgen'] = '''# Cubit -> Netgen: Tet mesh with high-order curving
# Replace GEOMETRY, PARAMETERS, and SETGEOMINFO sections for your shape
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import Mesh, Integrate, CF, BND
import cubit
import cubit_mesh_export

# === PARAMETERS ===
MESH_SIZE = 0.15
CURVE_ORDER = 3

# === GEOMETRY ===
cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
# TODO: Create your geometry here
# cubit.cmd("create cylinder height 2 radius 0.5")

# === STEP EXCHANGE (required for curved surfaces) ===
step_file = "geometry.step"
cubit.cmd(f'export step "{step_file}" overwrite')
cubit.cmd("reset")
cubit.cmd(f'import step "{step_file}" heal')

# === MESH ===
cubit.cmd("volume all scheme tetmesh")
cubit.cmd(f"volume all size {MESH_SIZE}")
cubit.cmd("mesh volume all")

# === BLOCKS ===
cubit.cmd("block 1 add tet all")
cubit.cmd('block 1 name "domain"')
cubit.cmd("block 2 add tri all")
cubit.cmd('block 2 name "boundary"')

# === EXPORT TO NETGEN ===
geo = OCCGeometry(step_file)
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)

# === SETGEOMINFO (one call per curved surface type) ===
# TODO: Add SetGeomInfo calls for your surfaces
# cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=0.5, height=2.0)

# === CURVE AND VERIFY ===
mesh = Mesh(ngmesh)
mesh.Curve(CURVE_ORDER)

vol = Integrate(CF(1), mesh)
area = Integrate(CF(1), mesh, VOL_or_BND=BND)
print(f"Volume: {vol:.6f}, Surface area: {area:.6f}")
'''

SCRIPT_TEMPLATES['tet_netgen_named'] = '''# Cubit -> Netgen: Complex geometry with name-based workflow
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry, Box, Cylinder, Sphere, gp_Pnt, gp_Ax2, gp_Dir
from ngsolve import Mesh, Integrate, CF, BND
import cubit
import cubit_mesh_export

MESH_SIZE = 0.15
CURVE_ORDER = 3

# === OCC GEOMETRY (create in OCC, not Cubit) ===
# TODO: Build your geometry using OCC Boolean operations
# brick = Box(gp_Pnt(-1,-1,-1), gp_Pnt(1,1,1))
# hole = Cylinder(gp_Ax2(gp_Pnt(0,0,-2), gp_Dir(0,0,1)), 0.3, 4)
# shape = brick - hole

# === NAME AND EXPORT ===
cubit_mesh_export.name_occ_faces(shape)
step_file = "geometry.step"
shape.WriteStep(step_file)
geo = OCCGeometry(step_file)

# === CUBIT IMPORT AND MESH ===
cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
cubit.cmd(f'import step "{step_file}" noheal')  # noheal preserves names!
cubit.cmd("volume all scheme tetmesh")
cubit.cmd(f"volume all size {MESH_SIZE}")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

# === EXPORT WITH NAME MAPPING ===
ngmesh = cubit_mesh_export.export_netgen_with_names(cubit, geo)

# === SETGEOMINFO ===
# TODO: Add SetGeomInfo calls for curved surfaces
# cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=0.3, height=2.0)

# === CURVE AND VERIFY ===
mesh = Mesh(ngmesh)
mesh.Curve(CURVE_ORDER)

vol = Integrate(CF(1), mesh)
print(f"Volume: {vol:.6f}")
'''

SCRIPT_TEMPLATES['tet_gmsh'] = '''# Cubit -> Gmsh 2nd order (simplest workflow)
import sys, os
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.read_gmsh import ReadGmsh
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

MESH_SIZE = 0.15

# === GEOMETRY AND MESH ===
cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
# TODO: Create your geometry
# cubit.cmd("create sphere radius 1")
cubit.cmd("volume all scheme tetmesh")
cubit.cmd(f"volume all size {MESH_SIZE}")
cubit.cmd("mesh volume all")

# === BLOCKS (2nd order) ===
cubit.cmd("block 1 add tet all")
cubit.cmd("block 1 element type tetra10")
cubit.cmd("block 2 add tri all")
cubit.cmd("block 2 element type tri6")

# === EXPORT ===
cubit_mesh_export.export_gmsh_v2(cubit, "mesh.msh")

# === IMPORT TO NGSOLVE ===
mesh = Mesh(ReadGmsh("mesh.msh"))
vol = Integrate(CF(1), mesh)
print(f"Volume: {vol:.6f}")
'''

SCRIPT_TEMPLATES['hex_netgen'] = '''# Cubit -> Netgen: Hex mesh with high-order curving
import sys, os, math
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netgen.occ import OCCGeometry
from ngsolve import Mesh, Integrate, CF
import cubit
import cubit_mesh_export

MESH_SIZE = 0.15
CURVE_ORDER = 3

# === GEOMETRY ===
cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
# TODO: Create your geometry
# cubit.cmd("create cylinder height 2 radius 0.5")

# === STEP EXCHANGE ===
step_file = "geometry.step"
cubit.cmd(f'export step "{step_file}" overwrite')
cubit.cmd("reset")
cubit.cmd(f'import step "{step_file}" heal')

# === HEX MESH (may need webcut for non-sweepable geometries) ===
# cubit.cmd("webcut volume all with plane xplane")
# cubit.cmd("webcut volume all with plane yplane")
# cubit.cmd("merge all")
cubit.cmd("volume all scheme auto")
cubit.cmd(f"volume all size {MESH_SIZE}")
cubit.cmd("mesh volume all")

# === BLOCKS ===
cubit.cmd("block 1 add hex all")
cubit.cmd('block 1 name "domain"')
cubit.cmd("block 2 add quad all")
cubit.cmd('block 2 name "boundary"')

# === EXPORT AND CURVE ===
geo = OCCGeometry(step_file)
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)

# TODO: SetGeomInfo for curved surfaces
# cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=0.5, height=2.0)

mesh = Mesh(ngmesh)
mesh.Curve(CURVE_ORDER)

vol = Integrate(CF(1), mesh)
print(f"Volume: {vol:.6f}")
'''

SCRIPT_TEMPLATES['vtk_export'] = '''# Cubit -> VTK/VTU export for ParaView visualization
import sys, os
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cubit
import cubit_mesh_export

# === GEOMETRY AND MESH ===
cubit.init(['cubit', '-nojournal', '-batch'])
cubit.cmd("reset")
# TODO: Create your geometry
# cubit.cmd("create brick x 1 y 1 z 1")
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.1")
cubit.cmd("mesh volume all")

# === BLOCKS ===
cubit.cmd("block 1 add tet all")
cubit.cmd('block 1 name "domain"')
cubit.cmd("block 2 add tri all")
cubit.cmd('block 2 name "boundary"')

# === EXPORT (choose one) ===
# VTK Legacy (simple ASCII)
cubit_mesh_export.export_vtk(cubit, "mesh.vtk")

# VTU XML (recommended for ParaView, includes BlockID metadata)
cubit_mesh_export.export_vtu(cubit, "mesh.vtu")

# For 2nd order visualization:
# cubit.cmd("block 1 element type tetra10")
# cubit.cmd("block 2 element type tri6")
# cubit_mesh_export.export_vtk(cubit, "mesh_2nd.vtk")

print("Export complete!")
'''


MESH_QUALITY_KNOWLEDGE = """
# Mesh Quality Guide

## Quality Metrics in Cubit

```python
# Check overall mesh quality
cubit.cmd("quality volume all shape")        # Shape metric (0-1, higher=better)
cubit.cmd("quality volume all aspect ratio") # Aspect ratio (1=ideal)
cubit.cmd("quality volume all jacobian")     # Jacobian (must be >0)
cubit.cmd("quality volume all condition")    # Condition number
```

## Minimum Requirements by Application

| Application | Shape | Aspect Ratio | Jacobian |
|-------------|-------|-------------|----------|
| General FEM | > 0.2 | < 10 | > 0 |
| High-order curving | > 0.3 | < 5 | > 0 |
| Radia BEM (hex) | > 0.5 | < 3 | > 0 (convex) |
| CFD | > 0.3 | < 5 | > 0 |

## Improving Mesh Quality

### Tetrahedral Meshes
```python
# Reduce element size
cubit.cmd("volume 1 size 0.05")

# Use quality-based smoothing
cubit.cmd("volume 1 smooth scheme condition number beta 2 cpu 10")
cubit.cmd("smooth volume 1")

# Webcut for better element shapes
cubit.cmd("webcut volume 1 with plane xplane")
```

### Hexahedral Meshes
```python
# Interval control for uniformity
cubit.cmd("curve 1 interval 10")

# Auto scheme selection
cubit.cmd("volume 1 scheme auto")

# Smoothing after meshing
cubit.cmd("smooth volume 1")
```

## Element Count Guidelines

```python
# Check counts
n_tet = cubit.get_tet_count()
n_hex = cubit.get_hex_count()
n_tri = cubit.get_tri_count()
n_quad = cubit.get_quad_count()
print(f"3D: {n_tet} tet + {n_hex} hex, 2D: {n_tri} tri + {n_quad} quad")
```

| Element Count | Suitability |
|---------------|-------------|
| < 1,000 | Quick prototyping, coarse analysis |
| 1,000 - 10,000 | Standard analysis |
| 10,000 - 100,000 | Fine analysis, convergence studies |
| > 100,000 | Very fine, may need parallel solver |

## Common Quality Issues

### 1. Negative Jacobian (Invalid Elements)
- **Cause**: Collapsed or inverted elements
- **Fix**: Refine mesh, webcut complex regions, use tet instead of hex

### 2. High Aspect Ratio
- **Cause**: Non-uniform sizing, thin geometry features
- **Fix**: Local size control, bias on curves

### 3. Poor Shape Quality Near Curved Surfaces
- **Cause**: Mesh doesn't follow curvature well
- **Fix**: Smaller element size near curved surfaces
  ```python
  cubit.cmd("surface 1 size 0.02")  # Finer on specific surface
  ```

### 4. Transition Element Issues
- **Cause**: Size transition too abrupt
- **Fix**: Gradual size change
  ```python
  cubit.cmd("volume 1 sizing function type skeleton scale 1.5")
  ```
"""


@mcp.tool()
def generate_cubit_script(workflow: str = "tet_netgen") -> str:
	"""
	Generate a template Cubit Python script for common workflows.

	Returns a ready-to-customize script with TODO markers for
	geometry-specific sections. Follows all project conventions.

	Args:
	    workflow: Script template to generate. Options:
	        "tet_netgen"       - Tet mesh -> Netgen with SetGeomInfo curving
	        "tet_netgen_named" - Complex geometry with name-based workflow
	        "tet_gmsh"         - Tet mesh -> Gmsh 2nd order (simplest)
	        "hex_netgen"       - Hex mesh -> Netgen with curving
	        "vtk_export"       - Tet/hex mesh -> VTK/VTU for ParaView
	"""
	workflow = workflow.lower().strip()
	if workflow in SCRIPT_TEMPLATES:
		return SCRIPT_TEMPLATES[workflow]
	else:
		return (
			f"Unknown workflow: '{workflow}'. "
			f"Available: {', '.join(SCRIPT_TEMPLATES.keys())}"
		)


@mcp.tool()
def mesh_quality_guide(topic: str = "all") -> str:
	"""
	Get mesh quality checking and improvement documentation.

	Covers Cubit quality metrics, minimum requirements by application,
	improvement techniques, and common quality issues.

	Args:
	    topic: Documentation topic. Options:
	        "all"    - Complete mesh quality guide
	"""
	if topic.lower().strip() == "all":
		return MESH_QUALITY_KNOWLEDGE
	else:
		return MESH_QUALITY_KNOWLEDGE


@mcp.tool()
def get_lint_rules() -> str:
	"""
	List all available Cubit export lint rules with descriptions.

	Returns a summary of each rule including its name, severity,
	description, and fix guidance. Useful for understanding what
	the linter checks before running lint_cubit_script.
	"""
	rules_info = [
		{
			'rule': 'missing-block-registration',
			'severity': 'CRITICAL',
			'description': 'Export function called but no block registration found.',
			'trigger': 'export_vtk(cubit, "mesh.vtk") without any block add command',
			'fix': 'cubit.cmd("block 1 add tet all")',
		},
		{
			'rule': 'missing-mesh-command',
			'severity': 'CRITICAL',
			'description': 'Export function called but no mesh command found.',
			'trigger': 'export_vtk(cubit, "mesh.vtk") without mesh volume/surface command',
			'fix': 'cubit.cmd("mesh volume all")',
		},
		{
			'rule': 'geometry-block-2nd-order',
			'severity': 'HIGH',
			'description': 'Geometry block (volume/surface) used with element type conversion. Has no effect.',
			'trigger': 'block 1 add volume 1 + block 1 element type tetra10',
			'fix': 'Use mesh elements: block 1 add tet all in volume 1',
		},
		{
			'rule': 'missing-cubit-init',
			'severity': 'HIGH',
			'description': 'Script imports cubit but does not call cubit.init().',
			'trigger': 'import cubit without cubit.init()',
			'fix': "cubit.init(['cubit', '-nojournal', '-batch'])",
		},
		{
			'rule': 'wrong-connectivity-2nd-order',
			'severity': 'HIGH',
			'description': 'get_connectivity() used with 2nd order elements. Returns only corner nodes.',
			'trigger': 'block 1 element type tetra10 + get_connectivity("tet", tid)',
			'fix': 'Use get_expanded_connectivity("tet", tid)',
		},
		{
			'rule': 'element-type-before-add',
			'severity': 'HIGH',
			'description': 'Element type set before elements added to block. Type gets reset.',
			'trigger': 'block 1 element type tetra10 before block 1 add tet all',
			'fix': 'Add elements first, then set element type',
		},
		{
			'rule': 'setgeominfo-without-geometry',
			'severity': 'HIGH',
			'description': 'SetGeomInfo called but export_netgen() has no geometry parameter.',
			'trigger': 'export_netgen(cubit) + set_cylinder_geominfo(ngmesh, ...)',
			'fix': 'export_netgen(cubit, geometry=geo)',
		},
		{
			'rule': 'nodeset-sideset-usage',
			'severity': 'HIGH',
			'description': 'nodeset/sideset commands found with non-Exodus export. Blocks-only policy.',
			'trigger': 'nodeset 1 add surface 1 + export_vtk(...)',
			'fix': 'Use blocks: cubit.cmd("block 2 add tri all in surface 1")',
		},
		{
			'rule': 'missing-name-occ-faces',
			'severity': 'HIGH',
			'description': 'export_netgen_with_names() called but name_occ_faces() not found.',
			'trigger': 'export_netgen_with_names(cubit, geo) without name_occ_faces(shape)',
			'fix': 'cubit_mesh_export.name_occ_faces(shape) before STEP export',
		},
		{
			'rule': 'missing-step-reimport',
			'severity': 'MODERATE',
			'description': 'Netgen export with geometry but no STEP reimport pattern.',
			'trigger': 'export_netgen(cubit, geometry=geo) without export/reset/import STEP cycle',
			'fix': 'Export STEP -> reset -> import STEP -> mesh',
		},
		{
			'rule': 'heal-with-named-workflow',
			'severity': 'MODERATE',
			'description': 'Name-based workflow uses "heal" on STEP import, which destroys face names.',
			'trigger': 'name_occ_faces(shape) + import step "x.step" heal',
			'fix': 'Change to: import step "x.step" noheal',
		},
		{
			'rule': 'hardcoded-absolute-path',
			'severity': 'MODERATE',
			'description': 'Hardcoded absolute paths in sys.path (except Coreform Cubit/NGSolve).',
			'trigger': 'sys.path.insert(0, "S:/Projects/mymodule")',
			'fix': 'sys.path.insert(0, os.path.dirname(__file__))',
		},
		{
			'rule': 'missing-boundary-block',
			'severity': 'MODERATE',
			'description': 'Volume element block found but no surface element block for Netgen export.',
			'trigger': 'block 1 add tet all + export_netgen(...) without tri block',
			'fix': 'cubit.cmd("block 2 add tri all")',
		},
		{
			'rule': 'wrong-file-extension',
			'severity': 'MODERATE',
			'description': 'Export file extension does not match the format.',
			'trigger': 'export_vtk(cubit, "mesh.vtu") should be .vtk',
			'fix': 'Use correct extension: .vtk, .vtu, .msh, .bdf, .meg, .exo',
		},
		{
			'rule': 'curve-without-setgeominfo',
			'severity': 'MODERATE',
			'description': 'mesh.Curve() called but no set_*_geominfo() found.',
			'trigger': 'mesh.Curve(3) without set_cylinder/sphere/torus/cone_geominfo()',
			'fix': 'Call set_*_geominfo() for each curved surface before mesh.Curve()',
		},
		{
			'rule': 'missing-block-names',
			'severity': 'LOW',
			'description': 'Blocks registered without name command. Named blocks improve readability.',
			'trigger': 'block 1 add tet all without block 1 name "..."',
			'fix': 'cubit.cmd(\'block 1 name "domain"\')',
		},
	]

	lines = ["# Cubit Export Lint Rules (16 rules)", ""]
	for r in rules_info:
		lines.append(f"## [{r['severity']}] {r['rule']}")
		lines.append(f"{r['description']}")
		lines.append(f"- **Trigger**: {r['trigger']}")
		lines.append(f"- **Fix**: `{r['fix']}`")
		lines.append("")

	return '\n'.join(lines)


@mcp.tool()
def troubleshooting_guide(scenario: str = "all") -> str:
	"""
	Get debugging guidance for common Cubit mesh export problems.

	Provides diagnosis steps, root causes, and fixes for typical issues
	encountered when exporting Cubit meshes.

	Args:
	    scenario: Problem scenario. Options:
	        "all"                - Complete troubleshooting guide
	        "empty_export"       - Export produces empty file (0 elements)
	        "2nd_order"          - 2nd order elements not appearing
	        "setgeominfo"        - SetGeomInfo produces wrong results
	        "name_occ"           - name_occ_faces names not found in Cubit
	        "mesh_quality"       - Mesh quality too low
	        "module_not_found"   - Python module import errors
	        "missing_boundary"   - Missing boundary elements in export
	"""
	return get_cubit_documentation("troubleshooting")


# ============================================================
# Self-test
# ============================================================

def _selftest():
	"""Run lint on the project's examples/ directory."""
	print("=" * 70)
	print("Cubit Export Lint Self-Test")
	print("=" * 70)
	print()

	result = lint_cubit_directory("examples")
	print(result)


def main():
	"""Entry point for mcp-server-cubit command."""
	if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
		_selftest()
	else:
		mcp.run(transport="stdio")


if __name__ == '__main__':
	main()
