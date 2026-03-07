"""
GMSH Mesh Generation MCP Server

Provides tools for:
- GMSH Python API documentation (geo, occ, mesh, fields, options)
- Scripting best practices and common mistakes
- End-to-end workflow guides (Radia, NGSolve, CAD import)
- Linting Python scripts for GMSH scripting violations
- Code examples and customizable templates

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
from .gmsh_api_knowledge import get_gmsh_api_reference
from .gmsh_scripting_knowledge import get_gmsh_scripting_documentation
from .gmsh_workflow_knowledge import get_gmsh_workflow_documentation

# Create MCP server
mcp = FastMCP("gmsh-lint")

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
# Code examples
# ============================================================

EXAMPLES = {}

EXAMPLES['box_geo'] = '''# Box with built-in (geo) kernel
import gmsh

gmsh.initialize()
gmsh.model.add("box_geo")

# Define points
lc = 0.01  # mesh size in meters
p1 = gmsh.model.geo.addPoint(0, 0, 0, lc)
p2 = gmsh.model.geo.addPoint(0.1, 0, 0, lc)
p3 = gmsh.model.geo.addPoint(0.1, 0.05, 0, lc)
p4 = gmsh.model.geo.addPoint(0, 0.05, 0, lc)

# Define lines
l1 = gmsh.model.geo.addLine(p1, p2)
l2 = gmsh.model.geo.addLine(p2, p3)
l3 = gmsh.model.geo.addLine(p3, p4)
l4 = gmsh.model.geo.addLine(p4, p1)

# Surface
loop = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
surf = gmsh.model.geo.addPlaneSurface([loop])

# Extrude to volume
result = gmsh.model.geo.extrude([(2, surf)], 0, 0, 0.02)

gmsh.model.geo.synchronize()

# Physical groups for NGSolve/Radia
vol_tags = [t for d, t in result if d == 3]
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "domain")

# Mesh and export
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("box_geo.msh")
gmsh.finalize()

# Import to NGSolve
from ngsolve import Mesh
mesh = Mesh("box_geo.msh")
print(f"NGSolve mesh: {mesh.ne} elements")
'''

EXAMPLES['box_occ'] = '''# Box with OpenCASCADE (occ) kernel -- simpler API
import gmsh

gmsh.initialize()
gmsh.model.add("box_occ")

# Single command creates box
box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)
gmsh.model.occ.synchronize()

# Physical group
gmsh.model.addPhysicalGroup(3, [box], 1)
gmsh.model.setPhysicalName(3, 1, "domain")

# Mesh
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.005)
gmsh.model.mesh.generate(3)
gmsh.write("box_occ.msh")
gmsh.finalize()
'''

EXAMPLES['cylinder_occ'] = '''# Cylinder with OCC kernel, mesh fields, Radia integration
import gmsh
import os, sys

gmsh.initialize()
gmsh.model.add("cylinder")

# Create cylinder: axis from (0,0,0) to (0,0,0.1), radius 0.02
cyl = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 0.1, 0.02)
gmsh.model.occ.synchronize()

# Mesh size field: refine near top surface
f1 = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(f1, "SurfacesList", [3])  # top face
gmsh.model.mesh.field.setNumber(f1, "Sampling", 100)

f2 = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(f2, "InField", f1)
gmsh.model.mesh.field.setNumber(f2, "SizeMin", 0.002)
gmsh.model.mesh.field.setNumber(f2, "SizeMax", 0.005)
gmsh.model.mesh.field.setNumber(f2, "DistMin", 0.005)
gmsh.model.mesh.field.setNumber(f2, "DistMax", 0.02)

gmsh.model.mesh.field.setAsBackgroundMesh(f2)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

gmsh.model.addPhysicalGroup(3, [cyl], 1)
gmsh.model.setPhysicalName(3, 1, "iron_core")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("cylinder.msh")
gmsh.finalize()

# Import to Radia
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/radia"))
from gmsh_mesh_import import gmsh_to_radia, get_mesh_info
import radia as rad

info = get_mesh_info("cylinder.msh")
print(f"Mesh: {info}")

rad.UtiDelAll()
core = gmsh_to_radia("cylinder.msh", mu_r=1000)
print(f"Radia object: {core}")
'''

EXAMPLES['cad_import'] = '''# STEP file import -> mesh -> export
import gmsh

gmsh.initialize()
gmsh.model.add("cad_import")

# Import STEP file
volumes = gmsh.model.occ.importShapes("model.step")
gmsh.model.occ.synchronize()

# List imported entities
for dim, tag in volumes:
    print(f"Entity: dim={dim}, tag={tag}")

# Assign physical groups
vol_tags = [t for d, t in volumes if d == 3]
for i, tag in enumerate(vol_tags, 1):
    gmsh.model.addPhysicalGroup(3, [tag], i)
    gmsh.model.setPhysicalName(3, i, f"part_{i}")

# Mesh settings
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.01)
gmsh.option.setNumber("Mesh.Optimize", 1)
gmsh.model.mesh.generate(3)
gmsh.write("cad_import.msh")
gmsh.finalize()
'''

EXAMPLES['surface_mesh'] = '''# 2D surface mesh for PEEC conductor analysis
import gmsh

gmsh.initialize()
gmsh.model.add("conductor")

# Rectangular conductor plate
rect = gmsh.model.occ.addRectangle(0, 0, 0, 0.1, 0.01)
gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(2, [rect], 1)
gmsh.model.setPhysicalName(2, 1, "conductor")

# Surface mesh only (2D)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.005)
gmsh.model.mesh.generate(2)
gmsh.write("conductor.msh")
gmsh.finalize()

# Import for PEEC
from gmsh_mesh_import import gmsh_surface_to_ngsolve
mesh = gmsh_surface_to_ngsolve("conductor.msh", label="conductor")
print(f"Surface mesh: {mesh.ne} elements")
'''

EXAMPLES['transfinite_hex'] = '''# Structured hex mesh with transfinite algorithm
import gmsh

gmsh.initialize()
gmsh.model.add("hex_box")

# OCC box
box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)
gmsh.model.occ.synchronize()

# Set transfinite on ALL curves
for dim, tag in gmsh.model.getEntities(1):
    gmsh.model.mesh.setTransfiniteCurve(tag, 11)

# Set transfinite + recombine on ALL surfaces
for dim, tag in gmsh.model.getEntities(2):
    gmsh.model.mesh.setTransfiniteSurface(tag)
    gmsh.model.mesh.setRecombine(2, tag)

# Set transfinite on volume
for dim, tag in gmsh.model.getEntities(3):
    gmsh.model.mesh.setTransfiniteVolume(tag)

# Physical group
gmsh.model.addPhysicalGroup(3, [box], 1)
gmsh.model.setPhysicalName(3, 1, "domain")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("hex_box.msh")
gmsh.finalize()

print("Hex mesh generated successfully")
'''

EXAMPLES['radia_ferrite'] = '''# GMSH -> gmsh_to_radia() -> magnetic field solve
import gmsh
import os, sys

# Create ferrite core mesh
gmsh.initialize()
gmsh.model.add("ferrite_core")

# E-core shape: three legs
leg_w, leg_h, leg_d = 0.01, 0.03, 0.01
base_w, base_h = 0.05, 0.01

# Base
base = gmsh.model.occ.addBox(-base_w/2, 0, -leg_d/2, base_w, base_h, leg_d)
# Left leg
left = gmsh.model.occ.addBox(-base_w/2, base_h, -leg_d/2, leg_w, leg_h, leg_d)
# Center leg
center = gmsh.model.occ.addBox(-leg_w/2, base_h, -leg_d/2, leg_w, leg_h, leg_d)
# Right leg
right = gmsh.model.occ.addBox(base_w/2 - leg_w, base_h, -leg_d/2, leg_w, leg_h, leg_d)

# Fuse all parts
all_parts = [(3, base), (3, left), (3, center), (3, right)]
result, _ = gmsh.model.occ.fuse([all_parts[0]], all_parts[1:])
gmsh.model.occ.synchronize()

vol_tags = [t for d, t in result if d == 3]
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "ferrite")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.003)
gmsh.model.mesh.generate(3)
gmsh.write("ferrite_core.msh")
gmsh.finalize()

# Import to Radia and solve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/radia"))
from gmsh_mesh_import import gmsh_to_radia
import radia as rad

rad.UtiDelAll()
core = gmsh_to_radia("ferrite_core.msh", mu_r=2000)

# Add permanent magnet
magnet = rad.ObjRecMag([0, 0.03, 0], [0.01, 0.02, 0.01], [0, 954930, 0])
assembly = rad.ObjCnt([core, magnet])

# Solve
result = rad.Solve(assembly, 0.0001, 1000, 0)
print(f"Solve result: {result}")

# Field at gap
B = rad.Fld(assembly, 'b', [0, 0.05, 0])
print(f"B at gap: {B} T")

rad.UtiDelAll()
'''

EXAMPLES['ngsolve_poisson'] = '''# GMSH -> NGSolve -> Poisson equation solve
import gmsh

# Create sphere mesh
gmsh.initialize()
gmsh.model.add("poisson_sphere")

sphere = gmsh.model.occ.addSphere(0, 0, 0, 1.0)
gmsh.model.occ.synchronize()

# Volume physical group
gmsh.model.addPhysicalGroup(3, [sphere], 1)
gmsh.model.setPhysicalName(3, 1, "domain")

# Boundary physical group
surfs = gmsh.model.getBoundary([(3, sphere)], oriented=False)
surf_tags = [abs(t) for _, t in surfs]
gmsh.model.addPhysicalGroup(2, surf_tags, 2)
gmsh.model.setPhysicalName(2, 2, "boundary")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.2)
gmsh.model.mesh.generate(3)
gmsh.write("poisson_sphere.msh")
gmsh.finalize()

# NGSolve FEM solve
from ngsolve import *

mesh = Mesh("poisson_sphere.msh")
print(f"Mesh: {mesh.ne} elements, {mesh.nv} vertices")

fes = H1(mesh, order=2, dirichlet="boundary")
u, v = fes.TnT()
a = BilinearForm(grad(u) * grad(v) * dx).Assemble()
f = LinearForm(1 * v * dx).Assemble()

gfu = GridFunction(fes)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs()) * f.vec
print(f"Solution max: {max(gfu.vec):.6f}")
'''


# ============================================================
# Script templates
# ============================================================

TEMPLATES = {}

TEMPLATES['volume_tet'] = '''# Template: Volume tetrahedral mesh
# TODO: Modify geometry and mesh parameters for your application

import gmsh

gmsh.initialize()
gmsh.model.add("TODO_model_name")

# TODO: Create geometry using OCC kernel
# Example: box = gmsh.model.occ.addBox(x, y, z, dx, dy, dz)
box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)

# TODO: Add boolean operations if needed
# result, map = gmsh.model.occ.cut([(3, box)], [(3, hole)])

gmsh.model.occ.synchronize()

# TODO: Define physical groups for each material region
gmsh.model.addPhysicalGroup(3, [box], 1)
gmsh.model.setPhysicalName(3, 1, "TODO_material_name")

# Mesh settings
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.005)  # TODO: Adjust
gmsh.option.setNumber("Mesh.Optimize", 1)

gmsh.model.mesh.generate(3)
gmsh.write("TODO_output.msh")

gmsh.finalize()
'''

TEMPLATES['volume_hex'] = '''# Template: Volume hexahedral mesh (transfinite)
# TODO: Modify geometry and mesh density

import gmsh

gmsh.initialize()
gmsh.model.add("TODO_hex_model")

# TODO: Create box-like geometry
box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)
gmsh.model.occ.synchronize()

# Transfinite on all curves
# TODO: Adjust number of elements per direction
n_x, n_y, n_z = 20, 10, 5  # elements in each direction
for dim, tag in gmsh.model.getEntities(1):
    gmsh.model.mesh.setTransfiniteCurve(tag, 11)  # TODO: per-curve count

# Transfinite + recombine on all surfaces
for dim, tag in gmsh.model.getEntities(2):
    gmsh.model.mesh.setTransfiniteSurface(tag)
    gmsh.model.mesh.setRecombine(2, tag)

# Transfinite on volume
for dim, tag in gmsh.model.getEntities(3):
    gmsh.model.mesh.setTransfiniteVolume(tag)

# TODO: Physical group
gmsh.model.addPhysicalGroup(3, [box], 1)
gmsh.model.setPhysicalName(3, 1, "TODO_material")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("TODO_hex_output.msh")
gmsh.finalize()
'''

TEMPLATES['surface_peec'] = '''# Template: Surface mesh for PEEC conductor analysis
# TODO: Define conductor geometry

import gmsh

gmsh.initialize()
gmsh.model.add("TODO_conductor")

# TODO: Create conductor surface geometry
# Example: rectangular plate
rect = gmsh.model.occ.addRectangle(0, 0, 0, 0.1, 0.01)

# TODO: For coil, use addDisk or construct from curves
# disk = gmsh.model.occ.addDisk(0, 0, 0, 0.05, 0.05)

gmsh.model.occ.synchronize()

# TODO: Physical group
gmsh.model.addPhysicalGroup(2, [rect], 1)
gmsh.model.setPhysicalName(2, 1, "TODO_conductor_name")

# Surface mesh only
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.005)  # TODO: Adjust
gmsh.model.mesh.generate(2)  # 2D only!
gmsh.write("TODO_conductor.msh")
gmsh.finalize()

# Import for PEEC/BEM
# from gmsh_mesh_import import gmsh_surface_to_ngsolve
# mesh = gmsh_surface_to_ngsolve("TODO_conductor.msh")
'''

TEMPLATES['cad_to_radia'] = '''# Template: STEP import -> Radia integration
# TODO: Provide STEP file path and material properties

import gmsh
import os, sys

gmsh.initialize()
gmsh.model.add("TODO_cad_model")

# TODO: Import STEP file
volumes = gmsh.model.occ.importShapes("TODO_model.step")
gmsh.model.occ.synchronize()

# TODO: Assign physical groups per material
vol_tags = [t for d, t in volumes if d == 3]
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "TODO_material")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.005)  # TODO: Adjust
gmsh.model.mesh.generate(3)
gmsh.write("TODO_cad_mesh.msh")
gmsh.finalize()

# Import to Radia
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/radia"))
from gmsh_mesh_import import gmsh_to_radia
import radia as rad

rad.UtiDelAll()
# TODO: Set material (mu_r for soft iron, magnetization for PM)
obj = gmsh_to_radia("TODO_cad_mesh.msh", mu_r=1000)
# obj = gmsh_to_radia("TODO_cad_mesh.msh", magnetization=[0, 0, 954930])
rad.UtiDelAll()
'''

TEMPLATES['cad_to_ngsolve'] = '''# Template: STEP import -> NGSolve FEM
# TODO: Provide STEP file path and define problem

import gmsh

gmsh.initialize()
gmsh.model.add("TODO_fem_model")

# TODO: Import STEP file
volumes = gmsh.model.occ.importShapes("TODO_model.step")
gmsh.model.occ.synchronize()

# TODO: Physical groups for volumes
vol_tags = [t for d, t in volumes if d == 3]
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "TODO_domain")

# TODO: Physical groups for boundaries
surfs = gmsh.model.getBoundary([(3, t) for t in vol_tags], oriented=False)
surf_tags = list(set(abs(t) for _, t in surfs))
gmsh.model.addPhysicalGroup(2, surf_tags, 2)
gmsh.model.setPhysicalName(2, 2, "TODO_boundary")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.01)  # TODO: Adjust
gmsh.model.mesh.generate(3)
gmsh.write("TODO_fem_mesh.msh")
gmsh.finalize()

# NGSolve FEM
from ngsolve import *
mesh = Mesh("TODO_fem_mesh.msh")

# TODO: Define finite element space and problem
# fes = H1(mesh, order=2, dirichlet="TODO_boundary")
# u, v = fes.TnT()
# a = BilinearForm(grad(u) * grad(v) * dx).Assemble()
# f = LinearForm(source * v * dx).Assemble()
# gfu = GridFunction(fes)
# gfu.vec.data = a.mat.Inverse(fes.FreeDofs()) * f.vec
'''


# ============================================================
# GMSH element type reference
# ============================================================

ELEMENT_TYPE_REFERENCE = """
# GMSH Element Type Codes

## 1st Order (Linear)

| Code | Type | Nodes | Radia | NGSolve |
|------|------|-------|-------|---------|
| 1 | Line2 | 2 | - | H1/HCurl edges |
| 2 | Tri3 | 3 | PEEC surface | 2D elements |
| 3 | Quad4 | 4 | PEEC surface | 2D elements |
| 4 | Tet4 | 4 | ObjTetrahedron | 3D elements |
| 5 | Hex8 | 8 | ObjHexahedron | 3D elements |
| 6 | Wedge6 | 6 | ObjWedge | 3D elements |
| 7 | Pyramid5 | 5 | - | 3D elements |

## 2nd Order (Quadratic)

| Code | Type | Nodes | Notes |
|------|------|-------|-------|
| 8 | Line3 | 3 | Mid-edge node |
| 9 | Tri6 | 6 | 3 mid-edge nodes |
| 10 | Quad9 | 9 | 4 mid-edge + 1 center |
| 11 | Tet10 | 10 | 6 mid-edge nodes |
| 12 | Hex27 | 27 | Mid-edge + mid-face + center |

## Setting Element Order

```python
gmsh.model.mesh.generate(3)     # Generate 1st order
gmsh.model.mesh.setOrder(2)     # Elevate to 2nd order
```

## Radia Support

Radia currently supports **1st order only**:
- Tet4 (code 4) -> ObjTetrahedron (MMM, 3 DOF)
- Hex8 (code 5) -> ObjHexahedron (MSC, 6 DOF)
- Wedge6 (code 6) -> ObjWedge (MSC, 5 DOF)

For PEEC surface mesh: Tri3 (code 2), Quad4 (code 3),
Tri6 (code 9), Quad8/9 (codes 10) via gmsh_surface_to_ngsolve().
"""


# ============================================================
# GMSH vs Cubit comparison
# ============================================================

COMPARISON = {
    'overview': """
# GMSH vs Cubit: Overview

| Feature | GMSH | Cubit |
|---------|------|-------|
| Cost | Free (GPL) | Commercial |
| Install | pip install gmsh | Installer + license |
| Tet mesh | Excellent | Good |
| Hex mesh | Limited (transfinite) | Excellent |
| Boolean ops | OCC kernel | ACIS kernel |
| STEP import | Yes (OCC) | Yes (ACIS) |
| Python API | Yes | Yes |
| CI/CD | Easy (no license) | License needed |

Use GMSH for: free tool, tet mesh, simple hex, CI/CD automation.
Use Cubit for: complex hex meshing, sweep, map, advanced quality control.
""",
    'hex': """
# GMSH vs Cubit: Hex Meshing

| Capability | GMSH | Cubit |
|-----------|------|-------|
| Simple box hex | Transfinite (good) | Map (excellent) |
| Swept volumes | Very limited | sweep command |
| Topology decomposition | Manual only | webcut |
| Auto hex detection | No | autoscheme |
| Mixed hex-tet | No auto transition | Yes |
| Grading | Progression/Bump | Bias on curves |
| Complex solids | Usually fails | Often succeeds |

GMSH transfinite works for: boxes, simple cylinders, layered structures.
For anything more complex, use Cubit.
""",
    'mesh_quality': """
# GMSH vs Cubit: Mesh Quality

| Metric | GMSH | Cubit |
|--------|------|-------|
| Tet quality | Good (Netgen/HXT optimizer) | Good |
| Hex quality | N/A (transfinite only) | Excellent (many schemes) |
| Smoothing | Laplace2D, Netgen | Multiple methods |
| Quality metrics | Limited API access | Full diagnostics |
| Adaptive | Background fields | Sizing functions |

GMSH mesh quality for tet is comparable to Cubit.
For hex, Cubit is significantly better due to superior algorithms.
""",
    'automation': """
# GMSH vs Cubit: Automation

| Feature | GMSH | Cubit |
|---------|------|-------|
| pip install | Yes | No |
| CI/CD | Free (no license) | Needs license server |
| Docker | Easy | Complex (license) |
| Headless | Default | -nojournal -batch |
| API stability | Good | Good |
| Multi-platform | Win/Linux/Mac | Win/Linux/Mac |

GMSH is significantly easier to automate in CI/CD pipelines
because it has no licensing requirements.
""",
}


# ============================================================
# MCP Tools
# ============================================================

@mcp.tool()
def gmsh_docs(topic: str = "all") -> str:
    """GMSH documentation: API reference, scripting guide, and workflow guides.

    Topics are organized by prefix:
    - api_*: Python API reference (geo, occ, mesh, fields, options, file_io)
    - scripting_*: Best practices (initialization, common_mistakes, integration)
    - workflow_*: End-to-end workflows (radia, ngsolve, hex, cad_import)

    Use topic="all" to see all available topics.

    Examples:
        gmsh_docs("api_occ_primitives")
        gmsh_docs("scripting_common_mistakes")
        gmsh_docs("workflow_radia_volume_mesh")
        gmsh_docs("workflow_cubit_vs_gmsh")
    """
    if topic == "all":
        overview = """# GMSH MCP Server Documentation

## API Reference (api_*)
Topics: overview, geo_points_curves, geo_surfaces_volumes, occ_primitives,
occ_booleans, occ_transforms, occ_cad_import, mesh_generation, mesh_access,
mesh_fields, physical_groups, options, file_io

## Scripting Guide (scripting_*)
Topics: overview, initialization, geo_workflow, occ_workflow,
physical_groups_guide, mesh_size_control, element_types, msh_format,
common_mistakes, ngsolve_integration, radia_integration, transfinite

## Workflow Guide (workflow_*)
Topics: overview, radia_volume_mesh, radia_peec_surface, ngsolve_import,
cad_import, hex_meshing, mesh_refinement, 2d_surface_mesh, cubit_vs_gmsh,
troubleshooting

Use: gmsh_docs("api_<topic>"), gmsh_docs("scripting_<topic>"),
     gmsh_docs("workflow_<topic>")
"""
        return overview

    topic_lower = topic.lower().strip()

    if topic_lower.startswith("api_"):
        return get_gmsh_api_reference(topic_lower[4:])
    if topic_lower.startswith("scripting_"):
        return get_gmsh_scripting_documentation(topic_lower[10:])
    if topic_lower.startswith("workflow_"):
        return get_gmsh_workflow_documentation(topic_lower[9:])

    # Try direct lookup in all knowledge bases
    result = get_gmsh_api_reference(topic_lower)
    if not result.startswith("Unknown topic"):
        return result
    result = get_gmsh_scripting_documentation(topic_lower)
    if not result.startswith("Unknown topic"):
        return result
    result = get_gmsh_workflow_documentation(topic_lower)
    if not result.startswith("Unknown topic"):
        return result

    return (
        f"Unknown topic: '{topic}'. Use gmsh_docs('all') to see available topics.\n"
        f"Prefix with api_, scripting_, or workflow_ for specific categories."
    )


@mcp.tool()
def gmsh_code_example(example: str = "box_occ") -> str:
    """Get ready-to-run GMSH Python code examples.

    Available examples:
    - box_geo: Box with built-in (geo) kernel, NGSolve import
    - box_occ: Box with OCC kernel (simplest)
    - cylinder_occ: Cylinder with mesh fields, Radia integration
    - cad_import: STEP file import workflow
    - surface_mesh: 2D surface mesh for PEEC
    - transfinite_hex: Structured hex mesh
    - radia_ferrite: GMSH -> Radia magnetic solve
    - ngsolve_poisson: GMSH -> NGSolve Poisson equation
    """
    key = example.lower().strip()
    if key in EXAMPLES:
        return EXAMPLES[key]

    available = ", ".join(EXAMPLES.keys())
    return f"Unknown example: '{example}'. Available: {available}"


@mcp.tool()
def gmsh_script_template(workflow: str = "volume_tet") -> str:
    """Get customizable GMSH script templates with TODO markers.

    Templates provide starting points with clear TODO markers for customization.

    Available templates:
    - volume_tet: Volume tetrahedral mesh (default)
    - volume_hex: Transfinite hexahedral mesh
    - surface_peec: Surface mesh for PEEC conductors
    - cad_to_radia: STEP import -> Radia integration
    - cad_to_ngsolve: STEP import -> NGSolve FEM
    """
    key = workflow.lower().strip()
    if key in TEMPLATES:
        return TEMPLATES[key]

    available = ", ".join(TEMPLATES.keys())
    return f"Unknown template: '{workflow}'. Available: {available}"


@mcp.tool()
def lint_gmsh_script(filepath: str) -> str:
    """Lint a single GMSH Python script for common issues.

    Checks 14 rules covering:
    - Missing initialize/finalize/synchronize (CRITICAL)
    - Kernel mixing, generate ordering (CRITICAL/HIGH)
    - Missing physical groups, model.add (HIGH/MODERATE)
    - Hardcoded paths, unit conversion, unicode print (MODERATE)

    Args:
        filepath: Path to the Python script to lint.
    """
    # Resolve path
    p = Path(filepath)
    if not p.is_absolute():
        p = PROJECT_ROOT / p

    if not p.exists():
        return f"File not found: {p}"
    if not p.suffix == '.py':
        return f"Not a Python file: {p}"

    findings = _lint_file(str(p))

    # Use relative path for display
    try:
        display_path = str(p.relative_to(PROJECT_ROOT))
    except ValueError:
        display_path = str(p)

    return _format_findings(display_path, findings)


@mcp.tool()
def lint_gmsh_directory(directory: str = ".") -> str:
    """Lint all Python scripts in a directory for GMSH issues.

    Recursively scans for .py files and runs all 14 GMSH lint rules.

    Args:
        directory: Directory path to scan (default: current directory).
    """
    d = Path(directory)
    if not d.is_absolute():
        d = PROJECT_ROOT / d

    if not d.exists():
        return f"Directory not found: {d}"
    if not d.is_dir():
        return f"Not a directory: {d}"

    py_files = sorted(d.rglob("*.py"))
    if not py_files:
        return f"No Python files found in {d}"

    # Counts by severity
    counts = {'CRITICAL': 0, 'HIGH': 0, 'MODERATE': 0, 'LOW': 0, 'ERROR': 0}
    results = []

    for py_file in py_files:
        findings = _lint_file(str(py_file))
        if findings:
            try:
                display_path = str(py_file.relative_to(PROJECT_ROOT))
            except ValueError:
                display_path = str(py_file)
            results.append(_format_findings(display_path, findings))
            for f in findings:
                counts[f['severity']] = counts.get(f['severity'], 0) + 1

    # Summary
    total = sum(counts.values())
    summary = f"Scanned {len(py_files)} files, {total} issue(s) found.\n"
    if total > 0:
        summary += "  " + ", ".join(
            f"{k}: {v}" for k, v in counts.items() if v > 0
        ) + "\n"

    if results:
        return summary + "\n" + "\n\n".join(results)
    return summary + "All files clean."


@mcp.tool()
def get_gmsh_lint_rules() -> str:
    """List all 14 GMSH lint rules with severity and description."""
    header = "# GMSH Lint Rules\n\n"
    header += "| # | Rule | Severity | Description |\n"
    header += "|---|------|----------|-------------|\n"

    rows = []
    for i, rule in enumerate(ALL_RULES, 1):
        doc = rule.__doc__ or ""
        # Extract severity and description from docstring
        parts = doc.strip().split(":", 1)
        if len(parts) == 2:
            severity = parts[0].strip()
            desc = parts[1].strip()
        else:
            severity = "?"
            desc = doc.strip()
        name = rule.__name__.replace("check_", "")
        rows.append(f"| {i} | `{name}` | {severity} | {desc} |")

    return header + "\n".join(rows)


@mcp.tool()
def gmsh_element_types() -> str:
    """GMSH element type code reference table.

    Shows type codes, node counts, and Radia/NGSolve support for each element.
    """
    return ELEMENT_TYPE_REFERENCE


@mcp.tool()
def gmsh_vs_cubit(aspect: str = "overview") -> str:
    """Compare GMSH and Cubit for mesh generation.

    Aspects:
    - overview: General feature comparison
    - hex: Hexahedral meshing capabilities
    - mesh_quality: Mesh quality and optimization
    - automation: CI/CD and scripting automation
    """
    key = aspect.lower().strip()
    if key in COMPARISON:
        return COMPARISON[key]

    available = ", ".join(COMPARISON.keys())
    return f"Unknown aspect: '{aspect}'. Available: {available}"


# ============================================================
# MCP Prompts
# ============================================================

@mcp.prompt()
def new_gmsh_mesh(geometry: str, element_type: str = "tet") -> str:
    """Generate a prompt for creating a GMSH meshing script."""
    return f"""Create a GMSH Python script to mesh the following geometry:

Geometry: {geometry}
Element type: {element_type}

Requirements:
1. Use OCC kernel (gmsh.model.occ.*) unless geo kernel is specifically needed
2. Call gmsh.initialize() and gmsh.finalize()
3. Call gmsh.model.add("model_name")
4. Call gmsh.model.occ.synchronize() after geometry creation
5. Define physical groups for all material regions
6. Set Mesh.MshFileVersion to 2.2 (Radia/NGSolve compatibility)
7. All coordinates in meters
8. No Unicode symbols in print statements (cp932 Windows compatibility)

For hex mesh: use transfinite algorithm with setTransfiniteCurve/Surface/Volume.
For tet mesh: use default Delaunay algorithm.
"""


@mcp.prompt()
def gmsh_to_ngsolve_radia(workflow: str = "radia") -> str:
    """Generate a prompt for GMSH -> NGSolve/Radia pipeline."""
    return f"""Set up a GMSH to {"Radia" if workflow == "radia" else "NGSolve"} pipeline:

Steps:
1. Create/import geometry in GMSH
2. Define physical groups for material regions
3. Generate mesh (Mesh.MshFileVersion = 2.2)
4. Write .msh file

{"5. Import with gmsh_to_radia() from gmsh_mesh_import" if workflow == "radia" else "5. Import with ReadGmsh() from netgen.read_gmsh or Mesh()"}
{"6. Set material (mu_r for soft iron, magnetization for PM)" if workflow == "radia" else "6. Define FE space and solve problem"}

Key conventions:
- All coordinates in meters
- Physical groups required for material assignment
- Use fragment() for conformal multi-material interfaces
- MshFileVersion 2.2 for compatibility
"""


# ============================================================
# MCP Resources
# ============================================================

@mcp.resource("gmsh://element-types")
def resource_element_types() -> str:
    """GMSH element type code reference."""
    return ELEMENT_TYPE_REFERENCE


@mcp.resource("gmsh://workflow-decision")
def resource_workflow_decision() -> str:
    """Decision guide for GMSH workflow selection."""
    return get_gmsh_workflow_documentation("overview")


# ============================================================
# Self-test
# ============================================================

def _selftest():
    """Run self-test: lint fixtures and verify expected results."""
    import importlib.resources

    print("=== GMSH MCP Server Self-Test ===\n")

    # Test 1: Bad fixture should have findings
    fixtures_dir = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures"
    bad_file = fixtures_dir / "bad_gmsh_script.py"
    if bad_file.exists():
        findings = _lint_file(str(bad_file))
        n = len(findings)
        status = "PASS" if n > 0 else "FAIL"
        print(f"[{status}] bad_gmsh_script.py: {n} finding(s) (expected > 0)")
        if n > 0:
            for f in findings:
                print(f"  L{f['line']:>4d} [{f['severity']}] {f['rule']}")
    else:
        print(f"[SKIP] bad_gmsh_script.py not found at {bad_file}")

    # Test 2: Clean fixture should have zero findings
    clean_file = fixtures_dir / "clean_gmsh_script.py"
    if clean_file.exists():
        findings = _lint_file(str(clean_file))
        n = len(findings)
        status = "PASS" if n == 0 else "FAIL"
        print(f"[{status}] clean_gmsh_script.py: {n} finding(s) (expected 0)")
        if n > 0:
            for f in findings:
                print(f"  L{f['line']:>4d} [{f['severity']}] {f['rule']}")
    else:
        print(f"[SKIP] clean_gmsh_script.py not found at {clean_file}")

    # Test 3: All knowledge base lookups return non-empty
    print("\nKnowledge base checks:")
    for prefix, getter in [
        ("api", get_gmsh_api_reference),
        ("scripting", get_gmsh_scripting_documentation),
        ("workflow", get_gmsh_workflow_documentation),
    ]:
        result = getter("all")
        status = "PASS" if len(result) > 100 else "FAIL"
        print(f"  [{status}] {prefix}: {len(result)} chars")

    # Test 4: All examples exist
    print(f"\nCode examples: {len(EXAMPLES)} available")
    for key in EXAMPLES:
        print(f"  [OK] {key}")

    # Test 5: All templates exist
    print(f"\nScript templates: {len(TEMPLATES)} available")
    for key in TEMPLATES:
        print(f"  [OK] {key}")

    # Test 6: Rules count
    n_rules = len(ALL_RULES)
    status = "PASS" if n_rules == 14 else "FAIL"
    print(f"\n[{status}] Lint rules: {n_rules} (expected 14)")

    print("\n=== Self-test complete ===")


# ============================================================
# Entry point
# ============================================================

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        _selftest()
    else:
        mcp.run(transport="stdio")


if __name__ == '__main__':
    main()
