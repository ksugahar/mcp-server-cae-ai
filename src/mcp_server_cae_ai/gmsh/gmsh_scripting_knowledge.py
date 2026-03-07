"""
GMSH scripting best practices and workflow documentation.

Covers initialization, kernel selection, common mistakes, and integration patterns.
"""

GMSH_SCRIPTING_OVERVIEW = """
# GMSH Scripting Overview

GMSH is a free, open-source mesh generator with a built-in Python API.
It supports 1D/2D/3D mesh generation with Delaunay, Frontal, and other algorithms.

## Why GMSH?

| Advantage | Details |
|-----------|---------|
| **Free & open source** | GPL license, no licensing cost |
| **Cross-platform** | Windows, Linux, macOS |
| **Python API** | Full scripting via `pip install gmsh` |
| **OCC integration** | Boolean ops, STEP import via OpenCASCADE |
| **Active development** | Regular releases, responsive community |

## Typical Workflow

```python
import gmsh

gmsh.initialize()
gmsh.model.add("model_name")

# 1. Create geometry (geo or occ kernel)
# 2. Synchronize
# 3. Define physical groups
# 4. Set mesh options
# 5. Generate mesh
# 6. Write output

gmsh.finalize()
```

## GMSH vs Cubit

| Feature | GMSH | Cubit |
|---------|------|-------|
| Cost | Free | Commercial |
| Hex meshing | Limited (transfinite only) | Excellent (sweep, map, pave) |
| Tet meshing | Excellent (Delaunay/Frontal) | Good (tetmesh) |
| Boolean ops | OCC kernel | ACIS kernel |
| STEP import | Yes (via OCC) | Yes (via ACIS) |
| Mesh size control | Fields (very flexible) | Intervals, sizing functions |
| 2nd order | Built-in | Built-in |
| Python API | Yes | Yes |

**Use GMSH when**: Free tool needed, tet mesh sufficient, simple hex (transfinite).
**Use Cubit when**: Complex hex meshing required (sweep, webcut, map).
"""


GMSH_INITIALIZATION = """
# GMSH Initialization

## Required Boilerplate

```python
import gmsh

gmsh.initialize()                        # MUST be first GMSH call
gmsh.model.add("my_model")              # Create a named model
gmsh.option.setNumber("General.Terminal", 1)  # Show progress

# ... your code ...

gmsh.finalize()                          # MUST be last GMSH call
```

## Suppress Output

```python
gmsh.option.setNumber("General.Terminal", 0)   # Silent mode
gmsh.option.setNumber("General.Verbosity", 0)  # No messages at all
```

## Command-Line Arguments

```python
gmsh.initialize(sys.argv)    # Pass CLI args (useful for GUI mode)
gmsh.initialize(["-noenv"])  # Skip reading gmshrc
```

## Exception Safety

```python
import gmsh

gmsh.initialize()
try:
    gmsh.model.add("model")
    # ... geometry and meshing ...
    gmsh.write("output.msh")
finally:
    gmsh.finalize()  # Always cleanup
```
"""


GMSH_GEO_WORKFLOW = """
# Built-in Kernel (geo) Workflow

Bottom-up construction: points -> curves -> surfaces -> volumes.

## Step-by-Step

```python
import gmsh

gmsh.initialize()
gmsh.model.add("geo_example")

# 1. Define points
lc = 0.01  # mesh size
p1 = gmsh.model.geo.addPoint(0, 0, 0, lc)
p2 = gmsh.model.geo.addPoint(0.1, 0, 0, lc)
p3 = gmsh.model.geo.addPoint(0.1, 0.05, 0, lc)
p4 = gmsh.model.geo.addPoint(0, 0.05, 0, lc)

# 2. Define curves
l1 = gmsh.model.geo.addLine(p1, p2)
l2 = gmsh.model.geo.addLine(p2, p3)
l3 = gmsh.model.geo.addLine(p3, p4)
l4 = gmsh.model.geo.addLine(p4, p1)

# 3. Define curve loop + surface
loop = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
surf = gmsh.model.geo.addPlaneSurface([loop])

# 4. Extrude to create volume
result = gmsh.model.geo.extrude([(2, surf)], 0, 0, 0.02)

# 5. MUST synchronize before meshing
gmsh.model.geo.synchronize()

# 6. Physical groups
gmsh.model.addPhysicalGroup(3, [result[1][1]], 1)
gmsh.model.setPhysicalName(3, 1, "block")

# 7. Mesh
gmsh.model.mesh.generate(3)
gmsh.write("geo_example.msh")

gmsh.finalize()
```

## When to Use geo Kernel

- Full control over every entity
- Simple shapes (no booleans needed)
- Teaching/learning GMSH
- Legacy scripts

## Limitations

- No boolean operations
- No STEP import
- More verbose than OCC
"""


GMSH_OCC_WORKFLOW = """
# OpenCASCADE Kernel (occ) Workflow

Top-down construction: primitives + booleans. Recommended for most applications.

## Step-by-Step

```python
import gmsh

gmsh.initialize()
gmsh.model.add("occ_example")

# 1. Create primitives
box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)
hole = gmsh.model.occ.addCylinder(0.05, 0.025, 0, 0, 0, 0.02, 0.01)

# 2. Boolean operations
result, map = gmsh.model.occ.cut([(3, box)], [(3, hole)])

# 3. MUST synchronize
gmsh.model.occ.synchronize()

# 4. Physical groups
vol_tags = [t for d, t in result if d == 3]
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "block_with_hole")

# 5. Mesh
gmsh.model.mesh.generate(3)
gmsh.write("occ_example.msh")

gmsh.finalize()
```

## When to Use occ Kernel

- Complex geometry (booleans)
- CAD import (STEP/IGES)
- Conformal multi-material interfaces (fragment)
- Production workflows

## OCC Advantages

- Boolean ops: fuse, cut, intersect, fragment
- STEP/IGES/BREP import via `importShapes()`
- High-level primitives (Box, Sphere, Cylinder, etc.)
- Automatic surface/curve generation
"""


GMSH_PHYSICAL_GROUPS_GUIDE = """
# Physical Groups Guide

Physical groups are **essential** for downstream tools (NGSolve, Radia).
Without them, material/boundary information is lost.

## Always Define Physical Groups

```python
# WRONG: No physical groups
gmsh.model.mesh.generate(3)
gmsh.write("output.msh")  # Elements have no material identity

# CORRECT: With physical groups
gmsh.model.addPhysicalGroup(3, [vol_tag], 1)
gmsh.model.setPhysicalName(3, 1, "iron_core")
gmsh.model.mesh.generate(3)
gmsh.write("output.msh")  # Elements tagged with material
```

## Multi-Material Setup

```python
# After creating geometry with fragment() for conformal interface:
result, map = gmsh.model.occ.fragment([(3, core)], [(3, magnet)])
gmsh.model.occ.synchronize()

# Assign physical groups (tag numbers from fragment result)
gmsh.model.addPhysicalGroup(3, [core_new_tag], 1)
gmsh.model.setPhysicalName(3, 1, "iron")

gmsh.model.addPhysicalGroup(3, [magnet_new_tag], 2)
gmsh.model.setPhysicalName(3, 2, "magnet")
```

## Boundary Physical Groups

```python
# For boundary conditions in NGSolve
# Get boundary surfaces of a volume
surfs = gmsh.model.getBoundary([(3, vol_tag)], oriented=False)
surf_tags = [abs(t) for d, t in surfs]

gmsh.model.addPhysicalGroup(2, surf_tags, 10)
gmsh.model.setPhysicalName(2, 10, "outer_boundary")
```

## Usage in Downstream Tools

```python
# NGSolve: physical group name = material name
mesh = Mesh("output.msh")
fes = H1(mesh, definedon="iron")

# Radia: physical group number = filter
core = gmsh_to_radia("output.msh", mu_r=1000, physical_group=1)
```
"""


GMSH_MESH_SIZE_CONTROL = """
# Mesh Size Control

## Per-Point Sizing (geo kernel)

```python
# meshSize parameter in addPoint
p1 = gmsh.model.geo.addPoint(0, 0, 0, 0.001)  # fine
p2 = gmsh.model.geo.addPoint(1, 0, 0, 0.01)   # coarse
```

## Global Size Limits

```python
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0.001)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.01)
```

## Per-Entity Sizing (occ kernel)

```python
# After synchronize, set size on specific entities
gmsh.model.mesh.setSize([(0, p1), (0, p2)], 0.002)

# Set size on all points of a volume
pts = gmsh.model.getBoundary([(3, vol)], combined=False,
                              oriented=False, recursive=True)
gmsh.model.mesh.setSize(pts, 0.005)
```

## Mesh Size Fields (Most Flexible)

See api topic "mesh_fields" for detailed field documentation.

## Transfinite Meshing (Structured)

```python
# Structured mesh on curves
gmsh.model.mesh.setTransfiniteCurve(curve_tag, n_points)
gmsh.model.mesh.setTransfiniteCurve(curve_tag, n_points, "Bump", 0.1)

# Structured mesh on surfaces (requires 3 or 4 boundary curves)
gmsh.model.mesh.setTransfiniteSurface(surf_tag)

# Structured mesh on volumes (requires 6 faces for hex)
gmsh.model.mesh.setTransfiniteVolume(vol_tag)

# Recombine to get quads/hexes
gmsh.model.mesh.setRecombine(2, surf_tag)  # 2D: tri -> quad
```

## Curvature-Based Sizing

```python
# Automatically refine near curved surfaces
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 20)
# 20 = approximately 20 elements per 2*pi radians
```
"""


GMSH_ELEMENT_TYPES = """
# GMSH Element Types

## 1st Order Elements

| Code | Name | Nodes | Radia Support |
|------|------|-------|---------------|
| 1 | Line2 | 2 | N/A |
| 2 | Tri3 | 3 | Surface mesh (PEEC) |
| 3 | Quad4 | 4 | Surface mesh (PEEC) |
| 4 | Tet4 | 4 | ObjTetrahedron (MMM) |
| 5 | Hex8 | 8 | ObjHexahedron (MSC) |
| 6 | Wedge6 | 6 | ObjWedge (MSC) |
| 7 | Pyramid5 | 5 | Not supported |

## 2nd Order Elements

| Code | Name | Nodes | Radia Support |
|------|------|-------|---------------|
| 8 | Line3 | 3 | N/A |
| 9 | Tri6 | 6 | Surface mesh (PEEC, 2nd order) |
| 10 | Quad9 | 9 | Surface mesh (PEEC, 2nd order) |
| 11 | Tet10 | 10 | Planned |
| 12 | Hex27 | 27 | Planned |

## Setting Element Order

```python
# Generate 1st order mesh
gmsh.model.mesh.generate(3)

# Elevate to 2nd order
gmsh.model.mesh.setOrder(2)
```

**Important**: Radia currently supports 1st order only (Tet4, Hex8, Wedge6).
Use 1st order for `gmsh_to_radia()` import.
"""


GMSH_MSH_FORMAT = """
# MSH File Format

## Version 2.2 vs 4.1

| Feature | v2.2 | v4.1 |
|---------|------|------|
| **Compatibility** | Radia, NGSolve ReadGmsh | GMSH native |
| **Physical groups** | Basic | Extended metadata |
| **Partitioning** | No | Yes |
| **File size** | Smaller | Larger |
| **Default** | No | Yes (GMSH 4.x) |

## Setting Version

```python
# For Radia and NGSolve: ALWAYS use v2.2
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
```

## v2.2 File Structure

```
$MeshFormat
2.2 0 8
$EndMeshFormat
$PhysicalNames
N
dim tag "name"
...
$EndPhysicalNames
$Nodes
N
tag x y z
...
$EndNodes
$Elements
N
tag type n_tags tags... nodes...
...
$EndElements
```

## Reading MSH Files in Radia

```python
# Direct file parsing (no gmsh dependency needed)
from gmsh_mesh_import import gmsh_to_radia
obj = gmsh_to_radia("mesh.msh", mu_r=1000)
# Only supports v2.2 ASCII format

# Via GMSH API (any format)
import gmsh
gmsh.open("mesh.msh")
# ... query nodes/elements ...
```

## When to Use Each Version

- **v2.2**: Radia import, NGSolve ReadGmsh, maximum compatibility
- **v4.1**: GMSH-internal workflows, partitioned meshes, rich metadata
"""


GMSH_COMMON_MISTAKES = """
# Common GMSH Scripting Mistakes

## 1. Missing synchronize() (CRITICAL)

```python
# WRONG
gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
gmsh.model.mesh.generate(3)  # FAILS: geometry not synchronized

# CORRECT
gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
gmsh.model.occ.synchronize()  # Finalize geometry
gmsh.model.mesh.generate(3)
```

## 2. Mixing geo and occ kernels (CRITICAL)

```python
# WRONG: Two kernels in same script
gmsh.model.geo.addPoint(0, 0, 0, 0.1)
gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)  # Conflict!

# CORRECT: Use one kernel only
gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
gmsh.model.occ.synchronize()
```

## 3. setOrder before generate (HIGH)

```python
# WRONG
gmsh.model.mesh.setOrder(2)
gmsh.model.mesh.generate(3)

# CORRECT
gmsh.model.mesh.generate(3)
gmsh.model.mesh.setOrder(2)
```

## 4. No physical groups (HIGH)

```python
# WRONG: Elements lose material identity
gmsh.model.mesh.generate(3)
gmsh.write("output.msh")

# CORRECT
gmsh.model.addPhysicalGroup(3, [1], 1)
gmsh.model.setPhysicalName(3, 1, "material")
gmsh.model.mesh.generate(3)
gmsh.write("output.msh")
```

## 5. Tag collisions after booleans

```python
# After boolean ops, original tags may change
box = gmsh.model.occ.addBox(...)       # tag=1
cyl = gmsh.model.occ.addCylinder(...)  # tag=2
result, map = gmsh.model.occ.cut([(3, box)], [(3, cyl)])
# box tag may now be different! Use result to get new tags
new_tag = result[0][1]  # Correct tag after boolean
```

## 6. Forgetting gmsh.finalize()

Resources leak if `finalize()` is not called. Use try/finally pattern.

## 7. Wrong units

```python
# WRONG: mm coordinates
gmsh.model.occ.addBox(0, 0, 0, 100, 50, 20)  # 100mm? 100m?

# CORRECT: meters (Radia convention)
gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)  # 100mm = 0.1m
```

## 8. Missing gmsh.model.add()

```python
# WRONG: Uses default unnamed model
gmsh.initialize()
gmsh.model.occ.addBox(...)

# CORRECT: Named model
gmsh.initialize()
gmsh.model.add("my_model")
gmsh.model.occ.addBox(...)
```
"""


GMSH_NGSOLVE_INTEGRATION = """
# GMSH + NGSolve Integration

## Import via ReadGmsh (Recommended)

```python
from netgen.read_gmsh import ReadGmsh
from ngsolve import *

# GMSH side: use v2.2 format
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.write("model.msh")

# NGSolve side
ngmesh = ReadGmsh("model.msh")
mesh = Mesh(ngmesh)
```

## Direct Mesh Import

```python
from ngsolve import *
mesh = Mesh("model.msh")  # NGSolve reads .msh directly
```

## Physical Groups -> Boundaries/Materials

```python
# GMSH: define physical groups
gmsh.model.addPhysicalGroup(3, [1], 1)
gmsh.model.setPhysicalName(3, 1, "iron")

gmsh.model.addPhysicalGroup(2, [5, 6], 2)
gmsh.model.setPhysicalName(2, 2, "outer")

# NGSolve: use names directly
fes = H1(mesh, order=2, definedon="iron")
a = BilinearForm(fes)
# Boundary conditions by name
a += ... * ds("outer")
```

## High-Order Curving

```python
# GMSH: generate 2nd order mesh
gmsh.model.mesh.generate(3)
gmsh.model.mesh.setOrder(2)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.write("model.msh")

# NGSolve: import preserves 2nd order nodes
mesh = Mesh("model.msh")
# No need for mesh.Curve() -- already curved from GMSH
```

## Best Practices

1. Always use `Mesh.MshFileVersion = 2.2`
2. Define physical groups for ALL regions
3. For FEM: use `fragment()` to create conformal interfaces
4. For Radia field evaluation: use `rad.RadiaField()` CoefficientFunction
"""


GMSH_RADIA_INTEGRATION = """
# GMSH + Radia Integration

## Volume Mesh for MMM/MSC

```python
from gmsh_mesh_import import gmsh_to_radia
import radia as rad

rad.UtiDelAll()

# Simple: one material
core = gmsh_to_radia("ferrite.msh", mu_r=1000)

# With magnetization (permanent magnet)
magnet = gmsh_to_radia("magnet.msh", magnetization=[0, 0, 954930])

# With unit conversion (if mesh in mm)
obj = gmsh_to_radia("model_mm.msh", mu_r=1000, unit_scale=0.001)

# Filter by physical group
core = gmsh_to_radia("multi.msh", mu_r=1000, physical_group=1)
```

## Surface Mesh for PEEC/BEM

```python
from gmsh_mesh_import import gmsh_surface_to_ngsolve

# Create NGSolve surface mesh for BEM
mesh = gmsh_surface_to_ngsolve("conductor.msh", label="conductor")

# Use with ngbem or PEEC
from ngsolve import *
fes = HDivSurface(mesh, order=0)
```

## Mesh Info (No Radia Required)

```python
from gmsh_mesh_import import get_mesh_info
info = get_mesh_info("model.msh")
# Returns: node_count, element counts, bounding box, physical groups
```

## Complete Workflow

```python
import gmsh
import radia as rad
from gmsh_mesh_import import gmsh_to_radia

# 1. Create geometry in GMSH
gmsh.initialize()
gmsh.model.add("c_magnet")
# ... create geometry ...
gmsh.model.occ.synchronize()
gmsh.model.addPhysicalGroup(3, [1], 1)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("c_magnet.msh")
gmsh.finalize()

# 2. Import to Radia
rad.UtiDelAll()
core = gmsh_to_radia("c_magnet.msh", mu_r=1000)
magnet = rad.ObjRecMag([0, 0, 0], [0.1, 0.05, 0.02], [0, 0, 954930])
assembly = rad.ObjCnt([core, magnet])

# 3. Solve and compute field
result = rad.Solve(assembly, 0.0001, 1000, 0)
B = rad.Fld(assembly, 'b', [0, 0, 0.05])
```
"""


GMSH_TRANSFINITE = """
# Transfinite (Structured) Meshing

Transfinite meshing creates structured grids. Required for hex elements in GMSH.

## Transfinite Curve

```python
# setTransfiniteCurve(tag, numNodes, meshType="Progression", coef=1.0)
gmsh.model.mesh.setTransfiniteCurve(l1, 11)  # 11 nodes = 10 elements

# With grading (geometric progression)
gmsh.model.mesh.setTransfiniteCurve(l1, 11, "Progression", 1.2)

# With symmetry (bump grading)
gmsh.model.mesh.setTransfiniteCurve(l1, 11, "Bump", 0.1)
```

## Transfinite Surface

```python
# setTransfiniteSurface(tag, arrangement="Left", cornerTags=[])
# Surface must have 3 or 4 boundary curves
gmsh.model.mesh.setTransfiniteSurface(s1)

# Recombine to get quads (required for hex volumes)
gmsh.model.mesh.setRecombine(2, s1)
```

## Transfinite Volume

```python
# setTransfiniteVolume(tag, cornerTags=[])
# Volume must have 6 faces (mapped hex), 5 faces (wedge), or 4 faces (tet)
gmsh.model.mesh.setTransfiniteVolume(v1)
```

## Complete Hex Example

```python
import gmsh

gmsh.initialize()
gmsh.model.add("hex_box")

# OCC box
box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)
gmsh.model.occ.synchronize()

# Get all curves and set transfinite
curves = gmsh.model.getEntities(1)
for dim, tag in curves:
    gmsh.model.mesh.setTransfiniteCurve(tag, 11)

# Get all surfaces and set transfinite + recombine
surfaces = gmsh.model.getEntities(2)
for dim, tag in surfaces:
    gmsh.model.mesh.setTransfiniteSurface(tag)
    gmsh.model.mesh.setRecombine(2, tag)

# Set transfinite volume
volumes = gmsh.model.getEntities(3)
for dim, tag in volumes:
    gmsh.model.mesh.setTransfiniteVolume(tag)

gmsh.model.addPhysicalGroup(3, [volumes[0][1]], 1)
gmsh.model.setPhysicalName(3, 1, "domain")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("hex_box.msh")

gmsh.finalize()
```

## Limitations vs Cubit

| Feature | GMSH Transfinite | Cubit Hex |
|---------|-----------------|-----------|
| Simple box | Yes | Yes |
| Swept volumes | Limited | Excellent |
| Webcut decomposition | No | Yes |
| Complex topology | Very limited | Good |
| Automatic hex | No | Some (pave, map) |

**Recommendation**: For simple structured hex, GMSH transfinite works well.
For complex hex meshing, use Cubit.
"""


def get_gmsh_scripting_documentation(topic: str = "all") -> str:
    """Get GMSH scripting documentation by topic."""
    TOPICS = {
        "overview": GMSH_SCRIPTING_OVERVIEW,
        "initialization": GMSH_INITIALIZATION,
        "geo_workflow": GMSH_GEO_WORKFLOW,
        "occ_workflow": GMSH_OCC_WORKFLOW,
        "physical_groups_guide": GMSH_PHYSICAL_GROUPS_GUIDE,
        "mesh_size_control": GMSH_MESH_SIZE_CONTROL,
        "element_types": GMSH_ELEMENT_TYPES,
        "msh_format": GMSH_MSH_FORMAT,
        "common_mistakes": GMSH_COMMON_MISTAKES,
        "ngsolve_integration": GMSH_NGSOLVE_INTEGRATION,
        "radia_integration": GMSH_RADIA_INTEGRATION,
        "transfinite": GMSH_TRANSFINITE,
    }

    topic = topic.lower().strip()

    if topic == "all":
        toc = "# GMSH Scripting Guide\n\nTopics: " + ", ".join(TOPICS.keys()) + "\n\n"
        return toc + "\n\n---\n\n".join(TOPICS.values())

    if topic in TOPICS:
        return TOPICS[topic]

    return f"Unknown topic: '{topic}'. Valid topics: {', '.join(TOPICS.keys())}"
