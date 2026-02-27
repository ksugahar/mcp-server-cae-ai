"""
Cubit Python scripting knowledge base for mesh export.

Covers block registration, element order control, mesh schemes,
STEP exchange, initialization, and common mistakes.

Includes content migrated from Radia project's cubit_meshing_knowledge.py.
"""

CUBIT_OVERVIEW = """
# Cubit Mesh Generation Overview

Coreform Cubit provides structured and unstructured meshing with export to
multiple formats via the `cubit_mesh_export` module.

## Typical Workflow

```
1. Create geometry (Cubit commands or STEP import)
2. Set mesh scheme (tetmesh, map, sweep, etc.)
3. Set element size or interval count
4. Generate mesh
5. Register blocks
6. Export to desired format
```

## Element Types

| Element | Cubit Type | Nodes (1st) | Nodes (2nd) | Best For |
|---------|-----------|-------------|-------------|----------|
| Tet | TET | 4 | 10 | Complex geometry, auto-mesh |
| Hex | HEX | 8 | 20/27 | Structured grids, high accuracy |
| Wedge | WEDGE | 6 | 15 | Transition elements |
| Pyramid | PYRAMID | 5 | 13 | Hex-tet transition |
| Tri | TRI | 3 | 6 | Surface mesh |
| Quad | QUAD | 4 | 8/9 | Structured surface mesh |

## Why Cubit for FEM?

- **Structured hex meshing**: Higher accuracy per element
- **Interval control**: Precise element count along curves
- **Sweep meshing**: Efficient for extruded geometries
- **Multi-block**: Different mesh densities per region
- **Quality control**: Built-in mesh quality metrics
"""

CUBIT_BLOCKS = """
# Block Registration

## Why Blocks are Required

All `cubit_mesh_export` functions read mesh data from blocks.
**No blocks = no export.** This is the most common mistake.

## Mesh Element Blocks (Recommended)

```python
# 3D domain elements
cubit.cmd("block 1 add tet all")
cubit.cmd('block 1 name "domain"')

# 2D boundary elements
cubit.cmd("block 2 add tri all")
cubit.cmd('block 2 name "boundary"')
```

## Geometry Blocks (Alternative)

Blocks can contain geometry instead of mesh elements:

```python
cubit.cmd("block 1 add volume 1")    # All 3D elements in volume 1
cubit.cmd("block 2 add surface 1")   # All 2D elements on surface 1
```

| Block Contains | Elements Returned |
|----------------|-------------------|
| Volume | tet, hex, wedge, pyramid (3D only) |
| Surface | tri, quad (2D only) |
| Curve | edge (1D only) |
| Vertex | node (0D only) |

## Important: Element Order and Geometry Blocks

For 2nd order conversion, you MUST use mesh element blocks:

```python
# This works:
cubit.cmd("block 1 add tet all")
cubit.cmd("block 1 element type tetra10")   # Converts to 2nd order

# This does NOT work for 2nd order:
cubit.cmd("block 1 add volume 1")
cubit.cmd("block 1 element type tetra10")   # No effect on geometry blocks!
```

## Multiple Blocks

Use separate blocks for different materials or boundary conditions:

```python
cubit.cmd("block 1 add tet all in volume 1")
cubit.cmd('block 1 name "iron"')
cubit.cmd("block 2 add tet all in volume 2")
cubit.cmd('block 2 name "air"')
cubit.cmd("block 3 add tri all in surface 1")
cubit.cmd('block 3 name "dirichlet"')
```

## Mixed Element Warning

If a block contains multiple 3D element types (e.g., tet + hex), a warning
is displayed with 2nd order conversion instructions. For mixed blocks,
separate `element type` commands are needed:

```python
cubit.cmd("block 1 element type hex20")
cubit.cmd("block 1 element type tetra10")
```
"""

CUBIT_ELEMENT_ORDER = """
# Element Order Control

## Creating 2nd Order Elements

1. Create mesh (generates 1st order by default)
2. Add elements to block
3. Set element type to convert

```python
cubit.cmd("mesh volume 1")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 1 element type tetra10")   # Now 2nd order
```

## Element Type Commands

| 1st Order | 2nd Order | Command |
|-----------|-----------|---------|
| TET4 | TET10 | `block X element type tetra10` |
| HEX8 | HEX20 | `block X element type hex20` |
| HEX8 | HEX27 | `block X element type hex27` |
| WEDGE6 | WEDGE15 | `block X element type wedge15` |
| PYRAMID5 | PYRAMID13 | `block X element type pyramid13` |
| TRI3 | TRI6 | `block X element type tri6` |
| QUAD4 | QUAD8 | `block X element type quad8` |
| QUAD4 | QUAD9 | `block X element type quad9` |
| EDGE2 | EDGE3 | `block X element type bar3` |

## get_connectivity vs get_expanded_connectivity

```python
cubit.cmd("block 1 element type tetra10")
tet_id = cubit.get_block_tets(1)[0]

# get_connectivity: ALWAYS returns corner nodes only
nodes_1st = cubit.get_connectivity("tet", tet_id)
print(len(nodes_1st))   # Always 4

# get_expanded_connectivity: Returns ALL nodes
nodes_all = cubit.get_expanded_connectivity("tet", tet_id)
print(len(nodes_all))   # 10 for TET10, 4 for TET4
```

## Which Export Functions Use Which API

| Export Function | API | Respects Element Type |
|----------------|-----|----------------------|
| `export_vtk()` | `get_expanded_connectivity()` | Yes |
| `export_vtu()` | `get_expanded_connectivity()` | Yes |
| `export_gmsh_v2()` | `get_expanded_connectivity()` | Yes |
| `export_gmsh_v4()` | `get_expanded_connectivity()` | Yes |
| `export_exodus()` | `get_expanded_connectivity()` | Yes |
| `export_netgen()` | `get_connectivity()` | No (always 1st order) |
| `export_nastran()` | `get_connectivity()` | No (1st order only) |
| `export_meg()` | `get_connectivity()` | No (1st order only) |

## Design: Why export_netgen Uses 1st Order

Netgen's `mesh.Curve(order)` generates high-order nodes from CAD geometry.
This enables arbitrary orders (2, 3, 4, 5, ...) with exact placement on surfaces.
Cubit's role is topology (1st order mesh); Netgen's role is p-refinement.
"""

CUBIT_MESH_SCHEMES = """
# Mesh Schemes

## Tetrahedral (Auto)

```python
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.1")       # Target edge length
cubit.cmd("mesh volume all")
```

Best for: Complex geometry, automatic meshing.

## Map (Structured Quad/Hex)

```python
cubit.cmd("surface 1 scheme map")
cubit.cmd("curve 1 interval 10")
cubit.cmd("mesh surface 1")
```

Best for: Simple geometries with mappable topology.

## Sweep (Extruded)

```python
cubit.cmd("volume 1 scheme sweep source surface 1 target surface 2")
cubit.cmd("mesh volume 1")
```

Best for: Extruded or revolution geometries.

## Interval Control

```python
# Set number of elements along a curve
cubit.cmd("curve 1 interval 10")

# Set element size
cubit.cmd("volume 1 size 0.05")

# Gradation (size varies)
cubit.cmd("volume 1 sizing function type skeleton")
```

## Mesh Quality

```python
cubit.cmd("quality volume all shape")
cubit.cmd("quality volume all aspect ratio")
cubit.cmd("quality volume all jacobian")
```

## Hex Meshing Resolution Guidelines

| Resolution | Interval | Typical Elements | Use Case |
|-----------|----------|-----------------|----------|
| Coarse | 1-2 | 50-200 | Quick validation |
| Medium | 3-5 | 500-2000 | Standard analysis |
| Fine | 6-10 | 2000-10000 | High accuracy |
| Very Fine | 10+ | 10000+ | Convergence study |
"""

CUBIT_STEP_EXCHANGE = """
# STEP Import/Export

## Role of STEP in the Workflow

The STEP file serves as a bridge between Cubit's **ACIS** CAD kernel and
Netgen's **Open Cascade (OCC)** CAD kernel. These kernels represent
geometry differently (e.g., cylinder = 1 surface in ACIS, 2 faces in OCC).

By exchanging geometry via STEP:
- Cubit can mesh with OCC-compatible face boundaries
- OCC can provide the geometry reference for high-order curving
- Both tools work on the same geometric representation

## Exporting STEP from Cubit

```python
cubit.cmd('export step "geometry.step" overwrite')
```

## Importing STEP into Cubit

```python
# With healing (recommended for simple shapes)
cubit.cmd('import step "geometry.step" heal')

# Without healing (recommended for name-based workflow)
cubit.cmd('import step "geometry.step" noheal')
```

## heal vs noheal

| Option | Behavior | Use When |
|--------|----------|----------|
| `heal` | Repairs topology, merges surfaces | Simple shapes, STEP reimport workflow |
| `noheal` | Preserves original topology and names | Name-based workflow, preserving OCC face names |

## STEP Reimport Pattern (ACIS to OCC Conversion)

This pattern converts Cubit's internal ACIS representation to OCC-compatible
topology, ensuring the mesh respects OCC face boundaries (e.g., seam lines):

```python
# 1. Create geometry in Cubit (ACIS kernel)
cubit.cmd("create cylinder height 2 radius 0.5")

# 2. Export to STEP (ACIS -> STEP)
cubit.cmd('export step "cyl.step" overwrite')

# 3. Reset and reimport (STEP -> OCC-compatible topology)
cubit.cmd("reset")
cubit.cmd('import step "cyl.step" heal')

# Now Cubit's topology matches OCC's face splitting
```

## Surface Name Preservation

When importing STEP with named faces (from `name_occ_faces`):
- Use `noheal` to preserve surface names
- Check names: `cubit.get_entity_name('surface', sid)`
"""

CUBIT_INITIALIZATION = """
# Cubit Python Initialization

## Standard Boilerplate

```python
import sys

# Add Cubit to Python path
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")

import cubit
cubit.init(['cubit', '-nojournal', '-batch'])

# Add cubit_mesh_export to path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cubit_mesh_export
```

## With NGSolve

Scripts using both Cubit and NGSolve need both in sys.path:

```python
import sys
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")

# If using a custom NGSolve build:
# sys.path.insert(0, "path/to/ngsolve/install/Lib/site-packages")

import cubit
cubit.init(['cubit', '-nojournal', '-batch'])

from netgen.occ import OCCGeometry
from ngsolve import Mesh
import cubit_mesh_export
```

## Reset Between Operations

```python
cubit.cmd("reset")   # Clear all geometry and mesh
```

## Batch Mode Flags

| Flag | Description |
|------|-------------|
| `-nojournal` | Don't create journal file |
| `-batch` | No GUI, batch mode |
| `-nographics` | Disable graphics (faster) |
"""

CUBIT_MIXED_ELEMENTS = """
# Mixed Element Types

## Warning System

The module automatically warns when blocks contain multiple 3D element types:

```
WARNING: Block 1 ('mixed') contains multiple 3D element types: hex, tet
  To convert all elements to 2nd order, you need to issue separate commands:
    block 1 element type hex20
    block 1 element type tetra10
```

## Why It Matters

A single `element type` command only converts one type:
```python
cubit.cmd("block 1 element type tetra10")  # Only converts tets, not hexes
```

## Solution

Issue separate commands for each element type:
```python
cubit.cmd("block 1 element type hex20")
cubit.cmd("block 1 element type tetra10")
cubit.cmd("block 1 element type wedge15")
```
"""

CUBIT_COMMON_MISTAKES = """
# Common Cubit Scripting Mistakes

## 1. CRITICAL: No Block Registration Before Export

```python
# WRONG: Export without blocks -> empty file!
cubit.cmd("mesh volume 1")
cubit_mesh_export.export_vtk(cubit, "mesh.vtk")

# RIGHT: Register blocks first
cubit.cmd("mesh volume 1")
cubit.cmd("block 1 add tet all")
cubit_mesh_export.export_vtk(cubit, "mesh.vtk")
```

## 2. CRITICAL: Geometry Block with 2nd Order Conversion

```python
# WRONG: Geometry block, element type has no effect
cubit.cmd("block 1 add volume 1")
cubit.cmd("block 1 element type tetra10")   # Does nothing!

# RIGHT: Mesh element block
cubit.cmd("block 1 add tet all in volume 1")
cubit.cmd("block 1 element type tetra10")   # Works!
```

## 3. HIGH: Using get_connectivity for 2nd Order

```python
# WRONG: Always returns 4 nodes for tet
nodes = cubit.get_connectivity("tet", tet_id)        # 4 nodes

# RIGHT: Returns 10 nodes for TET10
nodes = cubit.get_expanded_connectivity("tet", tet_id)  # 10 nodes
```

## 4. HIGH: Element Type Before Adding to Block

```python
# WRONG: Set type before add
cubit.cmd("block 1 element type tetra10")
cubit.cmd("block 1 add tet all")

# RIGHT: Add first, then set type
cubit.cmd("block 1 add tet all")
cubit.cmd("block 1 element type tetra10")
```

## 5. HIGH: Missing STEP Reimport for Curved Surfaces

```python
# WRONG: Direct mesh without reimport -> seam mismatch
cubit.cmd("create cylinder height 2 radius 0.5")
cubit.cmd("mesh volume 1")
geo = OCCGeometry("cyl.step")  # Face boundaries don't match!

# RIGHT: Export and reimport STEP first
cubit.cmd("create cylinder height 2 radius 0.5")
cubit.cmd('export step "cyl.step" overwrite')
cubit.cmd("reset")
cubit.cmd('import step "cyl.step" heal')
cubit.cmd("mesh volume 1")     # Now matches OCC topology
```

## 6. MODERATE: Missing Boundary Element Block

```python
# INCOMPLETE: Volume block only
cubit.cmd("block 1 add tet all")

# COMPLETE: Both volume and surface blocks
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")   # Needed for boundary conditions
```

## 7. MODERATE: Hardcoded Absolute Paths

```python
# WRONG: Breaks on other machines
sys.path.insert(0, "S:/Projects/cubit_mesh_export")

# RIGHT: Use relative paths
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

## 8. HIGH: Mixed Hex-Tet Mesh for JMAG Without PYRAM=False

```python
# WRONG: JMAG cannot read CPYRAM elements
cubit.cmd("block 1 add hex all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 1 add pyramid all")
cubit_mesh_export.export_nastran(cubit, "mesh.bdf")  # Pyramids as CPYRAM!

# RIGHT: Use PYRAM=False for JMAG
cubit_mesh_export.export_nastran(cubit, "mesh.bdf", PYRAM=False)
# Or use pure tet mesh to avoid pyramids entirely
```

## 9. LOW: Using 'modify mesh volume X order 2'

```python
# WRONG: May not work reliably
cubit.cmd("modify mesh volume 1 order 2")

# RIGHT: Use block element type
cubit.cmd("block 1 element type tetra10")
```
"""

CUBIT_BLOCKS_ONLY_POLICY = """
# Blocks-Only Policy (No Nodesets or Sidesets)

## Core Rule

This module uses **blocks only** for mesh export. Nodesets and sidesets are **never used**.

## Why?

In Cubit, **only blocks** support element order specification:

```python
cubit.cmd("block 1 element type tetra10")   # Works: converts to 2nd order
# nodesets and sidesets have NO equivalent command
```

To maintain consistent element order control across all export formats
(Gmsh, VTK, Nastran, MEG, Netgen, Exodus), we standardize on blocks exclusively.

## Boundary Conditions with Blocks

Boundary conditions are defined using **separate blocks for boundary elements**,
not using nodesets or sidesets:

```python
# Domain elements (3D)
cubit.cmd("block 1 add tet all in volume 1")
cubit.cmd('block 1 name "domain"')
cubit.cmd("block 1 element type tetra10")    # 2nd order

# Boundary elements (2D)
cubit.cmd("block 2 add tri all in surface 1")
cubit.cmd('block 2 name "boundary"')
cubit.cmd("block 2 element type tri6")       # 2nd order

# Multiple boundary conditions
cubit.cmd("block 3 add tri all in surface 2")
cubit.cmd('block 3 name "dirichlet"')
cubit.cmd("block 4 add tri all in surface 3")
cubit.cmd('block 4 name "neumann"')
```

## Common Mistakes

```python
# WRONG: Using nodesets (this module ignores them)
cubit.cmd("nodeset 1 add surface 1")     # NOT supported

# WRONG: Using sidesets (this module ignores them)
cubit.cmd("sideset 1 add surface 1")     # NOT supported

# RIGHT: Use blocks for everything
cubit.cmd("block 2 add tri all in surface 1")
cubit.cmd('block 2 name "boundary"')
```

## Design Rationale

| Feature | Blocks | Nodesets | Sidesets |
|---------|--------|----------|----------|
| Element order control | Yes | No | No |
| Named groups | Yes | Yes | Yes |
| 2nd order conversion | Yes | N/A | N/A |
| Export support | All formats | None | None |
"""

# Migrated from Radia project: hex and tet meshing workflows
CUBIT_HEX_WORKFLOW = """
# Hexahedral Mesh Workflow

## Example: Simple Brick

```python
import cubit
cubit.init(['cubit', '-nojournal', '-batch'])

# Create geometry
cubit.cmd('create brick x 1 y 1 z 1')

# Set mesh intervals for structured hex mesh
cubit.cmd('curve all interval 4')

# Mesh
cubit.cmd('volume all scheme auto')
cubit.cmd('mesh volume all')

# Register blocks
cubit.cmd('block 1 add hex all')
cubit.cmd('block 2 add quad all')
```

## Example: Multi-body Union

```python
# C-type geometry (multiple bricks united)
cubit.cmd('create brick x 0.1 y 0.3 z 0.1')  # Vertical leg 1
cubit.cmd('create brick x 0.3 y 0.1 z 0.1')  # Top bar
cubit.cmd('create brick x 0.1 y 0.3 z 0.1')  # Vertical leg 2

# Position parts
cubit.cmd('move volume 1 x -0.1 y 0')
cubit.cmd('move volume 2 x 0 y 0.1')
cubit.cmd('move volume 3 x 0.1 y 0')

# Union
cubit.cmd('unite volume all')

# Mesh
cubit.cmd('curve all interval 2')
cubit.cmd('volume all scheme auto')
cubit.cmd('mesh volume all')
```

## When to Give Up on Hex and Switch to Tet

Not all geometries can be hex-meshed in Cubit. If webcut and decomposition
fail to produce mappable/sweepable sub-volumes, switch to tetmesh:

```python
# Try hex first
cubit.cmd("volume all scheme auto")
cubit.cmd("mesh volume all")

# If meshing fails or produces poor quality, switch to tet
cubit.cmd("delete mesh")
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.1")
cubit.cmd("mesh volume all")
```

**Warning**: Switching from hex to tet may introduce pyramid transition
elements at hex-tet interfaces. Some solvers (notably JMAG) cannot read
standard pyramid elements — use `PYRAM=False` for Nastran export.

## JMAG Compatibility

JMAG requires degenerate hex pyramids, not standard CPYRAM elements:

```python
# For JMAG: use PYRAM=False
cubit_mesh_export.export_nastran(cubit, "mesh.bdf", PYRAM=False)
```

With `PYRAM=False`, pyramid elements are written as degenerate CHEXA
(8-node hex with repeated nodes) instead of CPYRAM (5-node), which JMAG
can read.

## Tips

- Use `curve X interval N` for precise element counts
- `volume all scheme auto` selects best scheme automatically
- For sweepable volumes, Cubit auto-detects and uses sweep
- Check quality: `cubit.cmd('quality volume all shape')`
"""

CUBIT_TET_WORKFLOW = """
# Tetrahedral Mesh Workflow

## Example: Sphere

```python
import cubit
cubit.init(['cubit', '-nojournal', '-batch'])

# Create sphere
cubit.cmd('create sphere radius 0.5')

# Set tetrahedral meshing
cubit.cmd('volume 1 scheme tetmesh')
cubit.cmd('volume 1 size 0.05')    # Target edge length
cubit.cmd('mesh volume 1')

# Register blocks
cubit.cmd('block 1 add tet all')
cubit.cmd('block 2 add tri all')

# Check
n_tets = cubit.get_tet_count()
print(f"Tets: {n_tets}")
```

## Tips for Tetrahedral Meshing

1. **Webcut complex shapes**: Split into convex subdomains for better quality
   ```python
   cubit.cmd('webcut volume 1 with plane xplane')
   ```
2. **Control element size**: `volume N size S` where S is target edge length
3. **Quality check**: `quality volume all shape`
4. **Gradation**: `volume N sizing function type skeleton` for size grading
"""


CUBIT_2D_MESH_WORKFLOW = """
# 2D Mesh Workflow

## Overview

Several export formats support 2D mesh export:
- `export_nastran(cubit, "file.bdf", DIM="2D")`
- `export_meg(cubit, "file.meg", DIM='K')` (planar)
- `export_meg(cubit, "file.meg", DIM='R')` (axisymmetric)
- `export_gmsh_v4(cubit, "file.msh", DIM="2D")`
- `export_vtk` / `export_vtu` (surface elements in blocks)

## Surface Creation

```python
# Planar rectangle
cubit.cmd("create surface rectangle width 2 height 2 zplane")

# Circle
cubit.cmd("create surface circle radius 1 zplane")

# From imported geometry
cubit.cmd('import step "plate.step"')
```

## Mesh Schemes for Surfaces

| Scheme | Command | Element Type | Best For |
|--------|---------|-------------|----------|
| trimesh | `surface N scheme trimesh` | TRI3 | Complex 2D shapes |
| paving | `surface N scheme paving` | QUAD4 | Structured-like quad |
| map | `surface N scheme map` | QUAD4 | Simple rectangular domains |

```python
# Tri mesh
cubit.cmd("surface 1 scheme trimesh")
cubit.cmd("surface 1 size 0.3")
cubit.cmd("mesh surface 1")

# Quad mesh (paving)
cubit.cmd("surface 1 scheme paving")
cubit.cmd("surface 1 size 0.3")
cubit.cmd("mesh surface 1")
```

## Block Registration for 2D

```python
# Triangular elements
cubit.cmd("block 1 add tri all")
cubit.cmd('block 1 name "plate"')

# Quadrilateral elements
cubit.cmd("block 1 add quad all")
cubit.cmd('block 1 name "plate"')

# Edge elements (boundary)
cubit.cmd("block 2 add edge all in curve all")
cubit.cmd('block 2 name "boundary"')
```

## 2D Export Examples

### Nastran 2D
```python
cubit.cmd("create surface rectangle width 2 height 2 zplane")
cubit.cmd("surface 1 scheme trimesh")
cubit.cmd("surface 1 size 0.3")
cubit.cmd("mesh surface 1")
cubit.cmd("block 1 add tri all")
cubit.cmd('block 1 name "plate"')
cubit_mesh_export.export_nastran(cubit, "plate.bdf", DIM="2D")
```

### MEG 2D Planar (DIM='K')
```python
cubit.cmd("create surface rectangle width 2 height 2 zplane")
cubit.cmd("surface 1 scheme trimesh")
cubit.cmd("surface 1 size 0.3")
cubit.cmd("mesh surface 1")
cubit.cmd("block 1 add tri all")
cubit.cmd("block 1 name 'MMB3K'")
cubit_mesh_export.export_meg(cubit, "plate.meg", DIM='K')
```

### MEG Axisymmetric (DIM='R')
```python
cubit.cmd("create surface rectangle width 2 height 2 yplane")
cubit.cmd("surface 1 move 1 0 1")   # Positive X quadrant (r > 0)
cubit.cmd("surface 1 scheme trimesh")
cubit.cmd("surface 1 size 0.3")
cubit.cmd("mesh surface 1")
cubit.cmd("block 1 add tri all")
cubit.cmd("block 1 name 'MMB3R'")
cubit_mesh_export.export_meg(cubit, "axisym.meg", DIM='R')
```

### Gmsh v4 2D
```python
cubit.cmd("create surface rectangle width 2 height 2 zplane")
cubit.cmd("surface 1 scheme trimesh")
cubit.cmd("surface 1 size 0.3")
cubit.cmd("mesh surface 1")
cubit.cmd("block 1 add tri all")
cubit_mesh_export.export_gmsh_v4(cubit, "plate.msh", DIM="2D")
```

## 2D Normal Orientation

For 2D exports (Nastran DIM="2D", Gmsh v4 DIM="2D", MEG DIM='K'):
- Normals are oriented in +Z direction
- Z coordinates may be set to 0

For MEG axisymmetric (DIM='R'):
- Coordinates are R (mapped from X), Z
- Geometry must be in XZ plane (Y=0) with X > 0
"""

CUBIT_TROUBLESHOOTING = """
# Troubleshooting & Debugging Guide

## Problem: Export Produces Empty File (0 Elements)

**Cause**: No blocks registered before calling export function.
**Fix**:
```python
# MUST register blocks before any export
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")
```
**Diagnostic**: Check block contents:
```python
print(f"Tets in block 1: {len(cubit.get_block_tets(1))}")
```

## Problem: 2nd Order Elements Not Appearing

**Cause 1**: Geometry block used instead of mesh element block.
```python
# WRONG: Geometry block - element type command has no effect
cubit.cmd("block 1 add volume 1")
cubit.cmd("block 1 element type tetra10")  # Silently does nothing!

# RIGHT: Mesh element block
cubit.cmd("block 1 add tet all")
cubit.cmd("block 1 element type tetra10")  # Converts to 2nd order
```

**Cause 2**: Element type set before adding elements.
```python
# WRONG: Order matters
cubit.cmd("block 1 element type tetra10")  # Set type first
cubit.cmd("block 1 add tet all")           # Add after - type is reset

# RIGHT
cubit.cmd("block 1 add tet all")           # Add first
cubit.cmd("block 1 element type tetra10")  # Then set type
```

**Cause 3**: Using get_connectivity instead of get_expanded_connectivity.
```python
# get_connectivity ALWAYS returns 1st order nodes
nodes = cubit.get_connectivity("tet", tet_id)  # Always 4 nodes

# get_expanded_connectivity returns actual nodes
nodes = cubit.get_expanded_connectivity("tet", tet_id)  # 10 for TET10
```

**Diagnostic**: Check element order:
```python
tet_id = cubit.get_block_tets(1)[0]
n1 = len(cubit.get_connectivity("tet", tet_id))
n2 = len(cubit.get_expanded_connectivity("tet", tet_id))
print(f"1st order nodes: {n1}, Actual nodes: {n2}")
# If n1 == n2 == 4, still 1st order. If n2 == 10, it's 2nd order.
```

## Problem: SetGeomInfo Produces Wrong Results

**Cause 1**: Seam line mismatch (mesh elements cross OCC face boundary).
```python
# Fix: Use STEP reimport
cubit.cmd('export step "geometry.step" overwrite')
cubit.cmd("reset")
cubit.cmd('import step "geometry.step" heal')
cubit.cmd("mesh volume all")  # Now mesh respects OCC face boundaries
```

**Cause 2**: Wrong parameters (radius, center, axis).
Verify parameters match the Cubit geometry exactly.
For `create cylinder height H radius R`, center is (0,0,0).
For moved geometry, adjust center accordingly.

**Cause 3**: Tolerance too small (returns 0 modified entries).
```python
# Default tol=0.01 may be too small for coarse meshes
modified = cubit_mesh_export.set_cylinder_geominfo(
    ngmesh, radius=R, height=H, tol=0.05  # Increase tolerance
)
```

## Problem: name_occ_faces Names Not Found in Cubit

**Cause**: Used `heal` instead of `noheal` on STEP import.
```python
# WRONG: heal rewrites topology, loses face names
cubit.cmd('import step "geometry.step" heal')

# RIGHT: noheal preserves OCC face names
cubit.cmd('import step "geometry.step" noheal')
```

**Diagnostic**: Check surface names:
```python
for sid in cubit.get_entities('surface'):
    name = cubit.get_entity_name('surface', sid)
    print(f"Surface {sid}: '{name}'")
# Names should be like "occ_face_0", "occ_face_1", etc.
```

## Problem: Mesh Quality Too Low

**Diagnostic**:
```python
cubit.cmd("quality volume all shape")
cubit.cmd("quality volume all aspect ratio")
```

**Fixes**:
```python
# Reduce element size
cubit.cmd("volume 1 size 0.05")

# Smooth after meshing
cubit.cmd("smooth volume 1")

# Webcut complex regions
cubit.cmd("webcut volume 1 with plane xplane")
```

## Problem: "No module named 'cubit'" / "No module named 'netgen'"

**cubit not found**: Add Cubit's bin directory to sys.path:
```python
sys.path.append("C:/Program Files/Coreform Cubit 2025.3/bin")
```

**netgen not found**: NGSolve must be installed in the Python environment.
Scripts using both Cubit and NGSolve need both paths configured.

## Problem: JMAG Cannot Read Nastran File (Pyramid Elements)

**Cause**: JMAG does not support standard CPYRAM (5-node pyramid) elements.
When Cubit produces mixed hex-tet meshes, pyramid transition elements are generated.

**Fix**: Use `PYRAM=False` to write pyramids as degenerate CHEXA:
```python
cubit_mesh_export.export_nastran(cubit, "mesh.bdf", PYRAM=False)
```

**Alternative**: Avoid pyramids entirely by using pure tet mesh:
```python
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit_mesh_export.export_nastran(cubit, "mesh.bdf")
```

## Problem: Hex Meshing Fails on Complex Geometry

**Cause**: Not all geometries are decomposable into sweepable/mappable sub-volumes.

**Fixes** (try in order):
1. Webcut to simplify:
   ```python
   cubit.cmd("webcut volume 1 with plane xplane")
   cubit.cmd("merge all")
   cubit.cmd("volume all scheme auto")
   cubit.cmd("mesh volume all")
   ```
2. Use `scheme auto` (Cubit may choose a mix):
   ```python
   cubit.cmd("volume all scheme auto")
   ```
3. Give up on hex and use tet:
   ```python
   cubit.cmd("volume all scheme tetmesh")
   ```

## Problem: export_netgen Returns Mesh with 0 Boundary Elements

**Cause**: No surface element block (block with tri/quad).
```python
# Add boundary element block
cubit.cmd("block 2 add tri all")   # For tet meshes
cubit.cmd("block 2 add quad all")  # For hex meshes
```
"""


CUBIT_DESIGN_PHILOSOPHY = """
# Design Philosophy: Why This Module Exists

## Core Idea

This module does **NOT** use Cubit's built-in export commands
(`export genesis`, `export mesh`, `cubit.cmd("export ...")`, etc.) for most formats.
Instead, it reads mesh data via the **Cubit Python API** and constructs output
files directly in Python.

## How It Works

```
Cubit Python API                    Output file
  get_block_id_list()      ──┐
  get_block_tets(id)       ──┤
  get_connectivity()       ──┼──>  Python constructs  ──>  .msh / .vtk / .bdf / .meg
  get_expanded_connectivity()─┤
  get_nodal_coordinates()  ──┘
```

Each export function:
1. Iterates through all blocks
2. Gets element IDs and connectivity via Cubit API
3. Gets node coordinates via `get_nodal_coordinates()`
4. Writes the output file format directly

## Why Not Use Built-in Export?

Cubit's built-in export covers a limited set of formats (Exodus, STEP, SAT, etc.).
For formats like Gmsh, VTK, Nastran, MEG, and Netgen, there is no built-in export
command. This module fills that gap by providing format-specific writers that read
from Cubit's mesh data.

## Exception: export_exodus()

`export_exodus()` is the **only** function that uses a Cubit command internally:
```python
cubit.cmd('export mesh "filename.exo" overwrite')
```
This is because Exodus II is Cubit's native format and the built-in command
provides full fidelity (all element types, nodesets, sidesets, etc.).

## API Summary

| API Function | Returns | Used By |
|-------------|---------|---------|
| `get_block_id_list()` | All block IDs | All export functions |
| `get_block_tets(id)` | Tet IDs in block | All formats with tet support |
| `get_block_hexes(id)` | Hex IDs in block | All formats with hex support |
| `get_connectivity(type, id)` | Corner nodes only | nastran, meg, netgen |
| `get_expanded_connectivity(type, id)` | All nodes (incl. mid-edge) | gmsh, vtk, vtu, exodus |
| `get_nodal_coordinates(node_id)` | (x, y, z) | All export functions |

## For AI Assistants: Script Generation Rule

When generating Cubit export scripts, **never** use:
```python
# WRONG: No such built-in command for these formats
cubit.cmd('export gmsh "mesh.msh"')     # Does not exist
cubit.cmd('export vtk "mesh.vtk"')      # Does not exist
cubit.cmd('export nastran "mesh.bdf"')  # Does not exist
```

**Always** use the module functions:
```python
# RIGHT: Use cubit_mesh_export functions
cubit_mesh_export.export_gmsh_v2(cubit, "mesh.msh")
cubit_mesh_export.export_vtk(cubit, "mesh.vtk")
cubit_mesh_export.export_nastran(cubit, "mesh.bdf", DIM="3D")
```
"""

CUBIT_APREPRO_JOURNAL = """
# Running Python Scripts from Cubit (APREPRO Journal)

## The `play` Command

Cubit can execute Python scripts directly via the journal system:

```
Cubit> play "export_mesh.py"
```

This is the standard way to run `cubit_mesh_export` scripts from within Cubit's
GUI or command line. The `play` command:

1. Executes the Python file using Cubit's embedded Python interpreter
2. The `cubit` module is already available (no `import cubit` needed in some contexts)
3. All `cubit.cmd()` calls execute directly in the running Cubit session

## Script Template for `play`

```python
# export_mesh.py - Run with: play "export_mesh.py"
import cubit_mesh_export

# Mesh is already generated in Cubit GUI
# Just register blocks and export

cubit.cmd("block 1 add tet all")
cubit.cmd('block 1 name "domain"')
cubit.cmd("block 2 add tri all")
cubit.cmd('block 2 name "boundary"')

# Export to desired format
cubit_mesh_export.export_gmsh_v2(cubit, "mesh.msh")
cubit_mesh_export.export_vtk(cubit, "mesh.vtk")
```

## Prerequisites

The `cubit_mesh_export` package must be installed in Cubit's Python environment:

```bash
# Windows
"C:\\Program Files\\Coreform Cubit 2025.3\\bin\\python3\\python.exe" -m pip install coreform-cubit-mesh-export

# Linux/Mac
/path/to/cubit/bin/python3/python -m pip install coreform-cubit-mesh-export
```

## APREPRO Variables

Cubit's journal system supports APREPRO variable substitution:

```
# In Cubit journal file (.jou)
{radius = 0.5}
{height = 2.0}
create cylinder height {height} radius {radius}
volume 1 scheme tetmesh
volume 1 size 0.1
mesh volume 1
play "export_mesh.py"
```

APREPRO variables are expanded before the command is executed. However,
APREPRO variables do NOT propagate into Python scripts run via `play`.
To pass parameters, use environment variables or file-based communication.

## Journal + Python Hybrid Workflow

A common pattern uses a `.jou` file for geometry/meshing and a `.py` file for export:

```
# workflow.jou - Run with: cubit -batch -nographics -nojournal workflow.jou
reset
import step "geometry.step" heal
volume all scheme tetmesh
volume all size 0.1
mesh volume all
play "export_mesh.py"
```

```bash
# Execute from command line
"C:\\Program Files\\Coreform Cubit 2025.3\\bin\\coreform_cubit.exe" -batch -nographics -nojournal workflow.jou
```

## Batch Mode vs GUI Mode

| Mode | Command | `cubit` Available | Use Case |
|------|---------|-------------------|----------|
| GUI | `play "script.py"` in command panel | Yes (pre-imported) | Interactive |
| Batch | `coreform_cubit -batch ... journal.jou` | Yes (pre-imported) | Automated |
| Standalone | `python script.py` (with sys.path) | Need `import cubit` | Development |
"""


def get_cubit_documentation(topic: str = "all") -> str:
	"""Return Cubit scripting documentation by topic."""
	topics = {
		"overview": CUBIT_OVERVIEW,
		"blocks": CUBIT_BLOCKS,
		"blocks_only_policy": CUBIT_BLOCKS_ONLY_POLICY,
		"element_order": CUBIT_ELEMENT_ORDER,
		"mesh_schemes": CUBIT_MESH_SCHEMES,
		"step_exchange": CUBIT_STEP_EXCHANGE,
		"initialization": CUBIT_INITIALIZATION,
		"mixed_elements": CUBIT_MIXED_ELEMENTS,
		"common_mistakes": CUBIT_COMMON_MISTAKES,
		"hex_workflow": CUBIT_HEX_WORKFLOW,
		"tet_workflow": CUBIT_TET_WORKFLOW,
		"2d_mesh": CUBIT_2D_MESH_WORKFLOW,
		"troubleshooting": CUBIT_TROUBLESHOOTING,
		"design_philosophy": CUBIT_DESIGN_PHILOSOPHY,
		"aprepro_journal": CUBIT_APREPRO_JOURNAL,
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
