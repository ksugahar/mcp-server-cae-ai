"""
GMSH Python API reference documentation.

Organized by API namespace with practical examples.
"""

GMSH_API_OVERVIEW = """
# GMSH Python API Overview

GMSH provides a Python API for geometry creation, meshing, and file I/O.
All functions are accessed through the `gmsh` module.

## Two CAD Kernels

| Kernel | Namespace | Strengths |
|--------|-----------|-----------|
| **Built-in (geo)** | `gmsh.model.geo.*` | Bottom-up construction, full control |
| **OpenCASCADE (occ)** | `gmsh.model.occ.*` | Boolean ops, STEP import, primitives |

**Rule**: Use ONE kernel per script. Never mix `geo.*` and `occ.*`.

## Lifecycle

```python
import gmsh
gmsh.initialize()           # Must be first
gmsh.model.add("my_model")  # Create named model
# ... geometry + mesh ...
gmsh.finalize()              # Must be last
```

## Key Namespaces

| Namespace | Purpose |
|-----------|---------|
| `gmsh.model.geo.*` | Built-in kernel geometry |
| `gmsh.model.occ.*` | OpenCASCADE kernel geometry |
| `gmsh.model.mesh.*` | Mesh generation and queries |
| `gmsh.model.mesh.field.*` | Mesh size field control |
| `gmsh.option.*` | Global options |
| `gmsh.model.*` | Physical groups, entities |
| `gmsh.write()` / `gmsh.open()` | File I/O |

## Synchronize

After creating geometry with either kernel, call `synchronize()` before
meshing or assigning physical groups:

```python
gmsh.model.occ.synchronize()  # or gmsh.model.geo.synchronize()
```

## Tag System

GMSH uses integer **tags** to identify entities. Tags start at 1 (not 0).
Each `add*` function returns the tag of the created entity.

```python
tag = gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)  # returns volume tag
```

If you pass tag=-1 (default), GMSH auto-assigns.
"""


GMSH_GEO_POINTS_CURVES = """
# Built-in Kernel: Points and Curves

## Points

```python
# addPoint(x, y, z, meshSize=0, tag=-1)
p1 = gmsh.model.geo.addPoint(0, 0, 0, 0.1)     # with mesh size
p2 = gmsh.model.geo.addPoint(1, 0, 0, 0.1)
p3 = gmsh.model.geo.addPoint(1, 1, 0, 0.05)     # finer mesh here
p4 = gmsh.model.geo.addPoint(0, 1, 0, 0.1)
```

- `meshSize`: Target element size at this point (0 = use default)
- All coordinates in meters (Radia convention)

## Lines

```python
# addLine(startTag, endTag, tag=-1)
l1 = gmsh.model.geo.addLine(p1, p2)
l2 = gmsh.model.geo.addLine(p2, p3)
l3 = gmsh.model.geo.addLine(p3, p4)
l4 = gmsh.model.geo.addLine(p4, p1)
```

## Circle Arcs

```python
# addCircleArc(startTag, centerTag, endTag, tag=-1)
center = gmsh.model.geo.addPoint(0, 0, 0, 0.1)
p_start = gmsh.model.geo.addPoint(1, 0, 0, 0.1)
p_end = gmsh.model.geo.addPoint(0, 1, 0, 0.1)
arc = gmsh.model.geo.addCircleArc(p_start, center, p_end)
```

## Splines

```python
# addSpline(pointTags, tag=-1)
spline = gmsh.model.geo.addSpline([p1, p2, p3, p4])

# addBSpline(pointTags, tag=-1)
bspline = gmsh.model.geo.addBSpline([p1, p2, p3, p4])
```

## Curve Loop

```python
# addCurveLoop(curveTags, tag=-1)
# Negative tag = reversed direction
loop = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
```

**Important**: Curve loop must be closed (end of each curve = start of next).
"""


GMSH_GEO_SURFACES_VOLUMES = """
# Built-in Kernel: Surfaces and Volumes

## Plane Surface

```python
# addPlaneSurface(wireTags, tag=-1)
# First wire is outer boundary, rest are holes
loop = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
surf = gmsh.model.geo.addPlaneSurface([loop])

# Surface with hole
outer = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])
inner = gmsh.model.geo.addCurveLoop([l5, l6, l7, l8])
surf = gmsh.model.geo.addPlaneSurface([outer, inner])
```

## Surface Loop and Volume

```python
# addSurfaceLoop(surfaceTags, tag=-1)
sloop = gmsh.model.geo.addSurfaceLoop([s1, s2, s3, s4, s5, s6])

# addVolume(shellTags, tag=-1)
vol = gmsh.model.geo.addVolume([sloop])
```

## Extrude

```python
# extrude(dimTags, dx, dy, dz, numElements=[], heights=[], recombine=False)
result = gmsh.model.geo.extrude([(2, surf)], 0, 0, 0.1)
# result = list of (dim, tag) pairs for created entities
# result[0] = (3, vol_tag)  -- the extruded volume
# result[1] = (2, top_surf) -- the top surface
```

**Structured extrusion** (fixed layers):
```python
result = gmsh.model.geo.extrude([(2, surf)], 0, 0, 0.1,
                                 numElements=[10], heights=[1.0])
```

## Revolve

```python
# revolve(dimTags, x, y, z, ax, ay, az, angle, ...)
# Revolve around axis (ax,ay,az) passing through point (x,y,z)
result = gmsh.model.geo.revolve([(2, surf)], 0, 0, 0, 0, 0, 1, 3.14159)
```
"""


GMSH_OCC_PRIMITIVES = """
# OpenCASCADE Kernel: Primitives

OCC provides high-level shape creation. Recommended for most Radia workflows.

## Box

```python
# addBox(x, y, z, dx, dy, dz, tag=-1)
box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)
# Creates box from (x,y,z) to (x+dx, y+dy, z+dz)
```

## Sphere

```python
# addSphere(xc, yc, zc, radius, tag=-1, angle1=-pi/2, angle2=pi/2, angle3=2*pi)
sphere = gmsh.model.occ.addSphere(0, 0, 0, 0.05)
```

## Cylinder

```python
# addCylinder(x, y, z, dx, dy, dz, r, tag=-1, angle=2*pi)
# Axis from (x,y,z) to (x+dx, y+dy, z+dz), radius r
cyl = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 0.1, 0.02)
```

## Cone

```python
# addCone(x, y, z, dx, dy, dz, r1, r2, tag=-1, angle=2*pi)
cone = gmsh.model.occ.addCone(0, 0, 0, 0, 0, 0.1, 0.05, 0.02)
```

## Torus

```python
# addTorus(x, y, z, r1, r2, tag=-1, angle=2*pi)
# r1 = major radius, r2 = minor radius
torus = gmsh.model.occ.addTorus(0, 0, 0, 0.1, 0.02)
```

## Wedge

```python
# addWedge(x, y, z, dx, dy, dz, tag=-1, ltx=0)
# ltx = top x-length (0 = triangular cross-section)
wedge = gmsh.model.occ.addWedge(0, 0, 0, 0.1, 0.05, 0.1)
```

## Extrude and Revolve (OCC)

```python
# extrude(dimTags, dx, dy, dz, ...)
result = gmsh.model.occ.extrude([(2, surf)], 0, 0, 0.1)

# revolve(dimTags, x, y, z, ax, ay, az, angle)
result = gmsh.model.occ.revolve([(2, surf)], 0, 0, 0, 0, 0, 1, 3.14159)
```

All coordinates in **meters** (Radia convention).
"""


GMSH_OCC_BOOLEANS = """
# OpenCASCADE Kernel: Boolean Operations

## Fuse (Union)

```python
# fuse(objectDimTags, toolDimTags, tag=-1, removeObject=True, removeTool=True)
box1 = gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
box2 = gmsh.model.occ.addBox(0.5, 0, 0, 1, 1, 1)
result, map = gmsh.model.occ.fuse([(3, box1)], [(3, box2)])
# result: list of (dim, tag) of resulting entities
```

## Cut (Subtraction)

```python
# cut(objectDimTags, toolDimTags, tag=-1, removeObject=True, removeTool=True)
box = gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
hole = gmsh.model.occ.addCylinder(0.5, 0.5, 0, 0, 0, 1, 0.2)
result, map = gmsh.model.occ.cut([(3, box)], [(3, hole)])
```

## Intersect

```python
# intersect(objectDimTags, toolDimTags, tag=-1, removeObject=True, removeTool=True)
result, map = gmsh.model.occ.intersect([(3, box1)], [(3, box2)])
```

## Fragment (Common)

```python
# fragment(objectDimTags, toolDimTags, tag=-1, removeObject=True, removeTool=True)
# Creates conformal mesh at interfaces (critical for multi-material)
result, map = gmsh.model.occ.fragment([(3, box1)], [(3, box2)])
```

**fragment** is the most important boolean for FEM/BEM:
- Creates shared surfaces between touching volumes
- Enables conformal mesh at material interfaces
- Required for NGSolve multi-material models

## Keeping Original Shapes

```python
# Set removeObject/removeTool=False to keep originals
result, map = gmsh.model.occ.fuse([(3, box1)], [(3, box2)],
                                   removeObject=False, removeTool=False)
```
"""


GMSH_OCC_TRANSFORMS = """
# OpenCASCADE Kernel: Transforms

## Translate

```python
# translate(dimTags, dx, dy, dz)
gmsh.model.occ.translate([(3, box)], 0.1, 0, 0)
```

## Rotate

```python
# rotate(dimTags, x, y, z, ax, ay, az, angle)
# Rotate around axis (ax,ay,az) passing through (x,y,z)
import math
gmsh.model.occ.rotate([(3, box)], 0, 0, 0, 0, 0, 1, math.pi/4)
```

## Dilate (Scale)

```python
# dilate(dimTags, x, y, z, a, b, c)
# Scale by (a,b,c) around point (x,y,z)
gmsh.model.occ.dilate([(3, box)], 0, 0, 0, 2, 2, 2)  # double size
```

## Mirror (Symmetry)

```python
# symmetry(dimTags, a, b, c, d)
# Mirror through plane ax+by+cz+d=0
gmsh.model.occ.symmetry([(3, box)], 1, 0, 0, 0)  # mirror in YZ plane
```

## Copy

```python
# copy(dimTags)
new_tags = gmsh.model.occ.copy([(3, box)])
# Returns list of (dim, tag) for new entities
```

## Combined Example

```python
import gmsh, math

gmsh.initialize()
gmsh.model.add("transforms")

box = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.05, 0.02)
copies = []
for i in range(4):
    c = gmsh.model.occ.copy([(3, box)])
    gmsh.model.occ.rotate(c, 0, 0, 0, 0, 0, 1, i * math.pi / 2)
    copies.extend(c)

gmsh.model.occ.synchronize()
gmsh.model.mesh.generate(3)
gmsh.finalize()
```
"""


GMSH_OCC_CAD_IMPORT = """
# OpenCASCADE Kernel: CAD Import

## STEP Import

```python
# importShapes(fileName, highestDimOnly=True, format="")
volumes = gmsh.model.occ.importShapes("model.step")
# Returns list of (dim, tag) pairs
# highestDimOnly=True: only highest dimension entities (volumes for 3D)
```

## IGES Import

```python
volumes = gmsh.model.occ.importShapes("model.iges")
```

## BREP Import

```python
volumes = gmsh.model.occ.importShapes("model.brep")
```

## STL Import (via merge)

```python
gmsh.merge("model.stl")
# STL is triangulated surface -- no volume information
```

## Workflow: STEP -> Mesh -> Radia

```python
import gmsh

gmsh.initialize()
gmsh.model.add("cad_import")

# Import STEP
volumes = gmsh.model.occ.importShapes("ferrite_core.step")
gmsh.model.occ.synchronize()

# Assign physical group
vol_tags = [t for d, t in volumes if d == 3]
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "core")

# Mesh
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("ferrite_core.msh")

gmsh.finalize()

# Load into Radia
from gmsh_mesh_import import gmsh_to_radia
core = gmsh_to_radia("ferrite_core.msh", mu_r=1000)
```

## Tips for CAD Import

1. Use `highestDimOnly=True` (default) to get only volumes
2. Set `Mesh.MshFileVersion` to 2.2 for best Radia/NGSolve compatibility
3. For complex models, use `fragment()` to create conformal interfaces
4. Physical groups are essential for material assignment
"""


GMSH_MESH_GENERATION = """
# Mesh Generation

## Generate

```python
# generate(dim=3)
gmsh.model.mesh.generate(3)  # 3D volume mesh (tets/hexes)
gmsh.model.mesh.generate(2)  # 2D surface mesh (tris/quads)
gmsh.model.mesh.generate(1)  # 1D curve mesh (lines)
```

## Set Order

```python
# setOrder(order) -- elevate element order AFTER generating
gmsh.model.mesh.generate(3)
gmsh.model.mesh.setOrder(2)  # Convert to 2nd order (Tet10, Tri6, etc.)
```

**Important**: Generate first, then set order. Not the other way around.

## Recombine (Quad/Hex)

```python
# Recombine triangles into quads (2D)
gmsh.model.mesh.recombine()

# Or per-surface
gmsh.option.setNumber("Mesh.RecombineAll", 1)
```

## Optimize

```python
# optimize(method="", force=False, niter=1, dimTags=[])
gmsh.model.mesh.optimize("Netgen")     # Netgen optimizer
gmsh.model.mesh.optimize("Laplace2D")  # Laplace smoothing
gmsh.model.mesh.optimize("")           # Default optimizer
```

## Mesh Algorithms

```python
# 2D algorithms
gmsh.option.setNumber("Mesh.Algorithm", 6)  # Frontal-Delaunay (default)
# 1=MeshAdapt, 2=Automatic, 3=Initial mesh only, 5=Delaunay, 6=Frontal-Delaunay
# 7=BAMG, 8=Frontal-Delaunay for Quads, 9=Packing of Parallelograms, 11=Quasi-structured Quad

# 3D algorithms
gmsh.option.setNumber("Mesh.Algorithm3D", 1)  # Delaunay (default)
# 1=Delaunay, 3=Initial mesh only, 4=Frontal, 7=MMG3D, 10=HXT
```

## Mesh Size

```python
# Global mesh size
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0.001)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.01)

# Per-entity sizing via gmsh.model.mesh.setSize
gmsh.model.mesh.setSize(gmsh.model.getEntities(0), 0.01)  # all points
```
"""


GMSH_MESH_ACCESS = """
# Mesh Access (Query API)

## Get Nodes

```python
# getNodes(dim=-1, tag=-1, includeBoundary=False, returnParametricCoord=True)
node_tags, coords, param_coords = gmsh.model.mesh.getNodes()
# node_tags: 1D array of node tags
# coords: flattened [x1,y1,z1, x2,y2,z2, ...] array
# param_coords: parametric coordinates (usually not needed)

# Reshape coordinates
import numpy as np
points = np.array(coords).reshape(-1, 3)
```

## Get Elements

```python
# getElements(dim=-1, tag=-1)
elem_types, elem_tags, node_tags = gmsh.model.mesh.getElements()
# elem_types: list of element type codes per dimension
# elem_tags: list of arrays of element tags
# node_tags: list of arrays of node tags per element

# Get elements of specific dimension
elem_types, elem_tags, node_tags = gmsh.model.mesh.getElements(dim=3)
```

## GMSH Element Type Codes

| Code | Type | Nodes | Description |
|------|------|-------|-------------|
| 1 | Line2 | 2 | 1st order line |
| 2 | Tri3 | 3 | 1st order triangle |
| 3 | Quad4 | 4 | 1st order quadrilateral |
| 4 | Tet4 | 4 | 1st order tetrahedron |
| 5 | Hex8 | 8 | 1st order hexahedron |
| 6 | Wedge6 | 6 | 1st order wedge/prism |
| 7 | Pyramid5 | 5 | 1st order pyramid |
| 8 | Line3 | 3 | 2nd order line |
| 9 | Tri6 | 6 | 2nd order triangle |
| 10 | Quad9 | 9 | 2nd order quadrilateral |
| 11 | Tet10 | 10 | 2nd order tetrahedron |
| 12 | Hex27 | 27 | 2nd order hexahedron |

## Element Properties

```python
# getElementProperties(elementType)
name, dim, order, n_nodes, local_coords, n_primary = \\
    gmsh.model.mesh.getElementProperties(4)
# name="Tetrahedron 4", dim=3, order=1, n_nodes=4
```

## Get Elements by Type

```python
# getElementsByType(elementType, tag=-1, task=0, numTasks=1)
tags, node_tags = gmsh.model.mesh.getElementsByType(4)  # All tets
# tags: element tags
# node_tags: flattened node connectivity
```
"""


GMSH_MESH_FIELDS = """
# Mesh Size Fields

Fields control local mesh density. Essential for refinement near features.

## Distance Field

```python
# Distance from curves/points
f1 = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(f1, "CurvesList", [1, 2, 3])
gmsh.model.mesh.field.setNumber(f1, "Sampling", 100)
```

## Threshold Field

```python
# Size transition based on distance
f2 = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(f2, "InField", f1)     # Reference Distance field
gmsh.model.mesh.field.setNumber(f2, "SizeMin", 0.001)   # Min size (near)
gmsh.model.mesh.field.setNumber(f2, "SizeMax", 0.01)    # Max size (far)
gmsh.model.mesh.field.setNumber(f2, "DistMin", 0.005)   # Start transition
gmsh.model.mesh.field.setNumber(f2, "DistMax", 0.05)    # End transition
```

## Min Field

```python
# Take minimum of multiple fields
f3 = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(f3, "FieldsList", [f2, f4])
```

## MathEval Field

```python
# Analytical mesh size function
f4 = gmsh.model.mesh.field.add("MathEval")
gmsh.model.mesh.field.setString(f4, "F", "0.001 + 0.01 * sqrt(x*x + y*y)")
```

## Box Field

```python
f5 = gmsh.model.mesh.field.add("Box")
gmsh.model.mesh.field.setNumber(f5, "VIn", 0.001)    # Size inside box
gmsh.model.mesh.field.setNumber(f5, "VOut", 0.01)    # Size outside box
gmsh.model.mesh.field.setNumber(f5, "XMin", -0.05)
gmsh.model.mesh.field.setNumber(f5, "XMax", 0.05)
gmsh.model.mesh.field.setNumber(f5, "YMin", -0.05)
gmsh.model.mesh.field.setNumber(f5, "YMax", 0.05)
gmsh.model.mesh.field.setNumber(f5, "ZMin", -0.01)
gmsh.model.mesh.field.setNumber(f5, "ZMax", 0.01)
```

## Set Background Mesh

```python
# MUST set background mesh for fields to take effect
gmsh.model.mesh.field.setAsBackgroundMesh(f3)
```

## Complete Example

```python
# Refine near edge of magnet
f1 = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(f1, "CurvesList", [1, 2, 3, 4])
gmsh.model.mesh.field.setNumber(f1, "Sampling", 100)

f2 = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(f2, "InField", f1)
gmsh.model.mesh.field.setNumber(f2, "SizeMin", 0.001)
gmsh.model.mesh.field.setNumber(f2, "SizeMax", 0.01)
gmsh.model.mesh.field.setNumber(f2, "DistMin", 0.002)
gmsh.model.mesh.field.setNumber(f2, "DistMax", 0.02)

gmsh.model.mesh.field.setAsBackgroundMesh(f2)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
```
"""


GMSH_PHYSICAL_GROUPS = """
# Physical Groups

Physical groups assign meaning (material, boundary condition) to mesh entities.
They are **essential** for NGSolve and Radia import.

## Create Physical Group

```python
# addPhysicalGroup(dim, tags, tag=-1, name="")
# dim: 0=point, 1=curve, 2=surface, 3=volume
pg1 = gmsh.model.addPhysicalGroup(3, [1, 2], 1)     # volumes 1,2 -> group 1
gmsh.model.setPhysicalName(3, 1, "iron_core")

pg2 = gmsh.model.addPhysicalGroup(3, [3], 2)
gmsh.model.setPhysicalName(3, 2, "magnet")

# Boundary surfaces
pg3 = gmsh.model.addPhysicalGroup(2, [1, 2, 3], 3)
gmsh.model.setPhysicalName(2, 3, "outer_boundary")
```

## Dimension Conventions

| Dim | Entity Type | Use |
|-----|-------------|-----|
| 0 | Points | Point sources, probes |
| 1 | Curves | Wire currents, ports |
| 2 | Surfaces | Boundary conditions, PEEC conductors |
| 3 | Volumes | Materials (iron, magnet, air) |

## NGSolve Material Mapping

Physical group names become material/boundary names in NGSolve:

```python
# GMSH side
gmsh.model.addPhysicalGroup(3, [1], 1)
gmsh.model.setPhysicalName(3, 1, "iron")

# NGSolve side
from ngsolve import *
mesh = Mesh("model.msh")
fes = H1(mesh, definedon="iron")  # Physical group name used directly
```

## Radia Material Mapping

For `gmsh_to_radia()`, use `physical_group` parameter:

```python
from gmsh_mesh_import import gmsh_to_radia
core = gmsh_to_radia("model.msh", mu_r=1000, physical_group=1)
# Only elements in physical group 1 are imported
```

## Multiple Materials

```python
# Define each material region as separate physical group
gmsh.model.addPhysicalGroup(3, [core_vol], 1)
gmsh.model.setPhysicalName(3, 1, "iron_core")

gmsh.model.addPhysicalGroup(3, [magnet_vol], 2)
gmsh.model.setPhysicalName(3, 2, "magnet")

# Import separately with different materials
core = gmsh_to_radia("model.msh", mu_r=1000, physical_group=1)
magnet = gmsh_to_radia("model.msh", magnetization=[0, 0, 954930], physical_group=2)
```
"""


GMSH_OPTIONS = """
# GMSH Options

## Mesh Options

```python
# Mesh algorithm (2D)
gmsh.option.setNumber("Mesh.Algorithm", 6)        # 6=Frontal-Delaunay (default)

# Mesh algorithm (3D)
gmsh.option.setNumber("Mesh.Algorithm3D", 1)       # 1=Delaunay (default)

# Mesh file version
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)  # 2.2 for Radia/NGSolve

# Element size
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0.001)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.01)
gmsh.option.setNumber("Mesh.CharacteristicLengthFactor", 1.0)

# Mesh size from curvature
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 20)  # elements per 2*pi

# Mesh optimization
gmsh.option.setNumber("Mesh.Optimize", 1)          # Optimize (default)
gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)     # Netgen optimizer

# Recombine (quad/hex)
gmsh.option.setNumber("Mesh.RecombineAll", 1)
gmsh.option.setNumber("Mesh.Recombine3DAll", 1)     # Try hex
```

## General Options

```python
# Terminal output
gmsh.option.setNumber("General.Terminal", 1)    # Print to terminal
gmsh.option.setNumber("General.Terminal", 0)    # Suppress output

# Verbosity (0=silent, 1=errors, 2=warnings, 3=direct, 4=info, 99=debug)
gmsh.option.setNumber("General.Verbosity", 3)

# Number of threads
gmsh.option.setNumber("General.NumThreads", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads3D", 4)
```

## Geometry Options

```python
# Geometry tolerance
gmsh.option.setNumber("Geometry.Tolerance", 1e-6)
gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-6)

# OCC options
gmsh.option.setNumber("Geometry.OCCFixDegenerated", 1)
gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)
```

## Recommended Settings for Radia

```python
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)   # Radia/NGSolve compatibility
gmsh.option.setNumber("General.Terminal", 1)          # Show progress
gmsh.option.setNumber("Mesh.Algorithm3D", 1)          # Delaunay
gmsh.option.setNumber("Mesh.Optimize", 1)             # Optimize quality
```
"""


GMSH_FILE_IO = """
# File I/O

## Write Mesh

```python
# write(fileName)
# Format detected from extension
gmsh.write("output.msh")      # GMSH format (default v4, set MshFileVersion for v2)
gmsh.write("output.vtk")      # VTK Legacy
gmsh.write("output.stl")      # STL (surface only)
gmsh.write("output.step")     # STEP (geometry only, no mesh)
gmsh.write("output.brep")     # BREP (geometry only)
gmsh.write("output.unv")      # UNV (Ideas/Salome)
gmsh.write("output.med")      # MED (Salome)
```

## Open/Merge Files

```python
# open(fileName) -- replaces current model
gmsh.open("existing_mesh.msh")

# merge(fileName) -- adds to current model
gmsh.merge("additional.msh")
```

## MSH Format Versions

| Version | Setting | Notes |
|---------|---------|-------|
| **2.2** | `Mesh.MshFileVersion = 2.2` | Best for Radia, NGSolve ReadGmsh |
| **4.1** | `Mesh.MshFileVersion = 4.1` | Default, richer metadata |

**Recommendation**: Always use v2.2 for Radia and NGSolve:
```python
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
```

## Binary vs ASCII

```python
gmsh.option.setNumber("Mesh.Binary", 0)   # ASCII (default, readable)
gmsh.option.setNumber("Mesh.Binary", 1)   # Binary (smaller, faster)
```

## Save Physical Groups Only

```python
# Only save elements in physical groups (recommended)
gmsh.option.setNumber("Mesh.SaveAll", 0)   # Default: only physical groups
gmsh.option.setNumber("Mesh.SaveAll", 1)   # Save all elements
```
"""


def get_gmsh_api_reference(topic: str = "all") -> str:
    """Get GMSH API reference documentation by topic."""
    TOPICS = {
        "overview": GMSH_API_OVERVIEW,
        "geo_points_curves": GMSH_GEO_POINTS_CURVES,
        "geo_surfaces_volumes": GMSH_GEO_SURFACES_VOLUMES,
        "occ_primitives": GMSH_OCC_PRIMITIVES,
        "occ_booleans": GMSH_OCC_BOOLEANS,
        "occ_transforms": GMSH_OCC_TRANSFORMS,
        "occ_cad_import": GMSH_OCC_CAD_IMPORT,
        "mesh_generation": GMSH_MESH_GENERATION,
        "mesh_access": GMSH_MESH_ACCESS,
        "mesh_fields": GMSH_MESH_FIELDS,
        "physical_groups": GMSH_PHYSICAL_GROUPS,
        "options": GMSH_OPTIONS,
        "file_io": GMSH_FILE_IO,
    }

    topic = topic.lower().strip()

    if topic == "all":
        toc = "# GMSH API Reference\n\nTopics: " + ", ".join(TOPICS.keys()) + "\n\n"
        return toc + "\n\n---\n\n".join(TOPICS.values())

    if topic in TOPICS:
        return TOPICS[topic]

    return f"Unknown topic: '{topic}'. Valid topics: {', '.join(TOPICS.keys())}"
