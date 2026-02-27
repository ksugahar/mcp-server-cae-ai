"""
Netgen/NGSolve high-order curving workflow knowledge base.

This is the most important knowledge module. It covers:
- Workflow decision tree (simple vs complex vs Gmsh 2nd order)
- Step-by-step workflows for each geometry type
- SetGeomInfo API reference
- Seam line problem and solutions
- Troubleshooting guide
"""

WORKFLOW_OVERVIEW = """
# Netgen High-Order Curving: Workflow Overview

## Background: Why This Workflow Exists

Coreform Cubit uses the **ACIS** CAD kernel. Netgen/NGSolve uses **Open Cascade
(OCC)**. These kernels represent the same geometry differently — for example,
ACIS represents a cylinder as 1 surface, while OCC splits it at a seam line
into 2 faces. The **STEP file** acts as a bridge between the two kernels.

The overall workflow is:

1. Convert geometry to OCC representation via **STEP file**
   - Simple shapes: Create in Cubit (ACIS) → export STEP → reimport STEP
   - Complex shapes: Create directly in OCC → export STEP
2. Load STEP into **both** Cubit (for meshing) and OCC (for geometry reference)
3. Mesh with Cubit → **in-memory** `netgen.meshing.Mesh` object (no file I/O)
4. Compute UV parameters (**geominfo**) from OCC geometry → attach to mesh
5. `mesh.Curve(order)` uses geominfo + OCC geometry → high-order nodes on surfaces

The mesh is transferred **in-memory** via `export_netgen()`, which returns a
`netgen.meshing.Mesh` object directly. No intermediate mesh file is needed
(though file output is also possible via other export functions).

## Choose Your Workflow

1. **Is your geometry planar (no curved surfaces)?**
   -> Use any export format. Curving is not needed.
   -> Simplest: `export_gmsh_v2()` + `ReadGmsh()`

2. **Do you only need 2nd order (not 3rd+)?**
   -> Use the **Gmsh 2nd order** workflow (simplest):
   ```
   Cubit -> block element type tetra10 -> export_gmsh_v2() -> ReadGmsh()
   ```
   No geometry reference needed. Achieves ~0.001% accuracy.

3. **Is your geometry a simple analytic shape (cylinder, sphere, torus, cone)?**
   -> Use the **SIMPLE** workflow:
   ```
   Cubit (ACIS) -> STEP export -> STEP reimport (now OCC-compatible)
   -> mesh -> export_netgen(geometry=geo) -> set_*_geominfo()
   -> mesh.Curve(order)
   ```

4. **Is your geometry complex (Boolean operations, multiple curved surfaces)?**
   -> Use the **COMPLEX (name-based)** workflow:
   ```
   OCC -> name_occ_faces() -> STEP export
   -> Cubit import (noheal) -> mesh
   -> export_netgen_with_names(cubit, geo) -> set_*_geominfo()
   -> mesh.Curve(order)
   ```

## Accuracy Comparison

| Method | Curve(2) Error | Curve(3) Error | Max Order | Complexity |
|--------|----------------|----------------|-----------|------------|
| SetGeomInfo (simple) | ~0.003% | ~0.0006% | Unlimited | Medium |
| SetGeomInfo (name-based) | ~0.002% | ~0.0004% | Unlimited | High |
| Gmsh 2nd order (ReadGmsh) | ~0.001% | N/A | 2 | Low |
| 1st order (no curving) | ~1.4% | N/A | 1 | None |

## Key Principle

Cubit (ACIS kernel) generates the 1st order mesh topology. The STEP file
bridges ACIS and OCC representations. SetGeomInfo attaches UV parameters
from OCC geometry to mesh elements. Netgen's `mesh.Curve(order)` then
projects high-order nodes onto exact CAD surfaces. This enables:
- Arbitrary curve orders (2, 3, 4, 5, ...)
- Nodes placed exactly on CAD surfaces
- In-memory mesh transfer (no intermediate file I/O)
"""

WORKFLOW_CYLINDER = """
# Simple Workflow: Cylinder

## Parameters
- `radius`: Cylinder radius
- `height`: Cylinder height
- `center`: Center of cylinder (midpoint of axis)
- `axis`: 'x', 'y', or 'z'

## Step-by-Step

```python
import cubit_mesh_export
from netgen.occ import OCCGeometry
from ngsolve import Mesh

R = 0.5   # Radius
H = 2.0   # Height

# Step 1: Create geometry in Cubit
cubit.cmd(f"create cylinder height {H} radius {R}")

# Step 2: Export STEP
cubit.cmd('export step "cylinder.step" overwrite')

# Step 3: Reimport STEP (critical for seam-aware topology)
cubit.cmd("reset")
cubit.cmd('import step "cylinder.step" heal')

# Step 4: Mesh
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.15")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd('block 1 name "domain"')
cubit.cmd("block 2 add tri all")
cubit.cmd('block 2 name "boundary"')

# Step 5: Export to Netgen with geometry
geo = OCCGeometry("cylinder.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)

# Step 6: Set UV parameters
modified = cubit_mesh_export.set_cylinder_geominfo(
    ngmesh, radius=R, height=H, center=(0, 0, 0), axis='z'
)

# Step 7: High-order curving
mesh = Mesh(ngmesh)
mesh.Curve(3)   # 3rd order: ~0.0006% error
```

## Why STEP Reimport?
The STEP file bridges the ACIS and OCC CAD kernels:
- Cubit (ACIS kernel) represents a cylinder as 1 surface.
- OCC splits the cylinder at the seam line into 2 faces.
- Reimporting the STEP file makes Cubit adopt OCC-compatible topology.
- The mesh then aligns with OCC face boundaries.
Without reimport, elements may cross the seam, causing mesh.Curve() to fail.
"""

WORKFLOW_SPHERE = """
# Simple Workflow: Sphere

## Parameters
- `radius`: Sphere radius
- `center`: Center of sphere

## Step-by-Step

```python
import cubit_mesh_export
from netgen.occ import OCCGeometry
from ngsolve import Mesh

R = 0.5

# Step 1: Create geometry in Cubit
cubit.cmd(f"create sphere radius {R}")

# Step 2: Export STEP
cubit.cmd('export step "sphere.step" overwrite')

# Step 3: Reimport STEP
cubit.cmd("reset")
cubit.cmd('import step "sphere.step" heal')

# Step 4: Mesh
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.1")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

# Step 5: Export to Netgen with geometry
geo = OCCGeometry("sphere.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)

# Step 6: Set UV parameters
cubit_mesh_export.set_sphere_geominfo(ngmesh, radius=R, center=(0, 0, 0))

# Step 7: Curve
mesh = Mesh(ngmesh)
mesh.Curve(3)
```
"""

WORKFLOW_TORUS = """
# Simple Workflow: Torus

## Parameters
- `major_radius`: Distance from torus center to tube center
- `minor_radius`: Tube radius
- `center`: Center of torus
- `axis`: 'x', 'y', or 'z'

## Step-by-Step

```python
import cubit_mesh_export
from netgen.occ import OCCGeometry
from ngsolve import Mesh

R_MAJOR = 1.0
R_MINOR = 0.3

# Step 1: Create geometry in Cubit
cubit.cmd(f"create torus major {R_MAJOR} minor {R_MINOR}")

# Step 2: Export STEP
cubit.cmd('export step "torus.step" overwrite')

# Step 3: Reimport STEP
cubit.cmd("reset")
cubit.cmd('import step "torus.step" heal')

# Step 4: Mesh
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.08")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

# Step 5: Export to Netgen with geometry
geo = OCCGeometry("torus.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)

# Step 6: Set UV parameters
cubit_mesh_export.set_torus_geominfo(
    ngmesh, major_radius=R_MAJOR, minor_radius=R_MINOR,
    center=(0, 0, 0), axis='z'
)

# Step 7: Curve
mesh = Mesh(ngmesh)
mesh.Curve(3)
```
"""

WORKFLOW_CONE = """
# Simple Workflow: Cone

## Parameters
- `base_radius`: Radius at the base of the cone
- `height`: Height of the cone
- `center`: Center of cone base
- `axis`: 'x', 'y', or 'z'

## Step-by-Step

```python
import cubit_mesh_export
from netgen.occ import OCCGeometry
from ngsolve import Mesh

R_BASE = 0.5
H = 2.0

# Step 1: Create geometry in Cubit
cubit.cmd(f"create cone height {H} radius {R_BASE} top 0")

# Step 2: Export STEP
cubit.cmd('export step "cone.step" overwrite')

# Step 3: Reimport STEP
cubit.cmd("reset")
cubit.cmd('import step "cone.step" heal')

# Step 4: Mesh
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.1")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

# Step 5: Export to Netgen with geometry
geo = OCCGeometry("cone.step")
ngmesh = cubit_mesh_export.export_netgen(cubit, geometry=geo)

# Step 6: Set UV parameters
cubit_mesh_export.set_cone_geominfo(
    ngmesh, base_radius=R_BASE, height=H,
    center=(0, 0, 0), axis='z'
)

# Step 7: Curve
mesh = Mesh(ngmesh)
mesh.Curve(3)
```

## Note on Cone UV Parameters
- `u`: Angular parameter [0, 2*pi] around cone axis
- `v`: Height parameter [0, 1] (0 at base, 1 at apex)
"""

WORKFLOW_COMPLEX_NAMED = """
# Complex Workflow: Name-based Face Mapping

Use this workflow for Boolean operations, multi-surface geometries, or any case
where automatic face mapping is unreliable.

## Key Idea

OCC face names survive STEP round-trip. By naming faces before STEP export,
we can reliably map Cubit surfaces to OCC faces, even after Boolean operations.

## Step-by-Step

```python
import cubit_mesh_export
from netgen.occ import OCCGeometry, Box, Cylinder, gp_Pnt, gp_Ax2, gp_Dir
from ngsolve import Mesh

BRICK_SIZE = 2.0
R_HOLE = 0.3

# Step 1: Create geometry in OCC (NOT Cubit)
brick = Box(gp_Pnt(-1, -1, -1), gp_Pnt(1, 1, 1))
cyl = Cylinder(gp_Ax2(gp_Pnt(0, 0, -2), gp_Dir(0, 0, 1)), R_HOLE, 4)
shape = brick - cyl   # Boolean subtraction

# Step 2: Name OCC faces (CRITICAL!)
cubit_mesh_export.name_occ_faces(shape)
# Each face gets name "occ_face_0", "occ_face_1", etc.

# Step 3: Export STEP from OCC
shape.WriteStep("geometry.step")

# Step 4: Load OCCGeometry for mesh reference
geo = OCCGeometry("geometry.step")

# Step 5: Import STEP into Cubit and mesh
cubit.cmd('import step "geometry.step" noheal')
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.15")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

# Step 6: Export with name-based mapping
ngmesh = cubit_mesh_export.export_netgen_with_names(cubit, geo)

# Step 7: Set UV for curved surfaces
cubit_mesh_export.set_cylinder_geominfo(
    ngmesh, radius=R_HOLE, height=BRICK_SIZE,
    center=(0, 0, 0), axis='z'
)

# Step 8: High-order curving
mesh = Mesh(ngmesh)
mesh.Curve(3)  # ~0.0004% error
```

## Why Create Geometry in OCC?

- OCC supports face naming (`name_occ_faces`)
- Names survive STEP file format
- Cubit reads names as surface names on import
- `export_netgen_with_names` reads Cubit surface names to build correct mapping
- This avoids the unreliable geometric heuristic matching

## Multiple Curved Surfaces

For shapes with multiple curved surface types, call each SetGeomInfo separately:

```python
# Example: Brick with cylindrical hole and spherical cavity
cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=0.3, height=2.0)
cubit_mesh_export.set_sphere_geominfo(ngmesh, radius=0.5, center=(1, 0, 0))
```
"""

WORKFLOW_GMSH_2ND_ORDER = """
# Alternative: Gmsh 2nd Order Workflow (Simplest)

If you only need 2nd order elements and don't need 3rd order or higher,
this is the simplest approach with excellent accuracy (~0.001%).

## Step-by-Step

```python
import cubit_mesh_export
from netgen.read_gmsh import ReadGmsh
from ngsolve import Mesh

# Step 1: Create geometry and mesh in Cubit
cubit.cmd("create sphere radius 1")
cubit.cmd("volume 1 scheme tetmesh")
cubit.cmd("volume 1 size 0.2")
cubit.cmd("mesh volume 1")

# Step 2: Register blocks with 2nd order elements
cubit.cmd("block 1 add tet all in volume 1")
cubit.cmd("block 1 element type tetra10")    # Convert to 2nd order
cubit.cmd("block 2 add tri all")
cubit.cmd("block 2 element type tri6")       # 2nd order boundary

# Step 3: Export to Gmsh v2.2
cubit_mesh_export.export_gmsh_v2(cubit, "mesh.msh")

# Step 4: Read into NGSolve
mesh = Mesh(ReadGmsh("mesh.msh"))
# Done! No geometry reference needed.
```

## Advantages
- No STEP file exchange
- No geometry reference (OCCGeometry) needed
- No SetGeomInfo calls
- No seam line problems
- Very simple workflow

## Limitations
- Limited to 2nd order (no 3rd, 4th, 5th...)
- Cubit places mid-edge nodes, not exact CAD placement
- Accuracy is still excellent (~0.001%) for most applications
"""

SETGEOMINFO_REFERENCE = """
# SetGeomInfo API Reference

These functions set UV parameters on Netgen boundary elements, enabling
`mesh.Curve(order)` to project high-order nodes onto exact CAD surfaces.

## set_cylinder_geominfo()

```python
set_cylinder_geominfo(ngmesh, radius, height, center=(0,0,0), axis='z', tol=0.01)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ngmesh | Mesh | required | `netgen.meshing.Mesh` object |
| radius | float | required | Cylinder radius |
| height | float | required | Cylinder height |
| center | tuple | (0,0,0) | Center of cylinder (midpoint of axis) |
| axis | str | 'z' | Cylinder axis ('x', 'y', or 'z') |
| tol | float | 0.01 | Tolerance for surface detection |

Returns: Number of vertex geominfo entries modified.

UV mapping:
- `u`: Angular parameter [0, 1] around cylinder axis
- `v`: Height parameter [0, 1] along axis

## set_sphere_geominfo()

```python
set_sphere_geominfo(ngmesh, radius, center=(0,0,0), tol=0.01)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ngmesh | Mesh | required | `netgen.meshing.Mesh` object |
| radius | float | required | Sphere radius |
| center | tuple | (0,0,0) | Center of sphere |
| tol | float | 0.01 | Tolerance for surface detection |

UV mapping:
- `u`: Azimuthal angle [0, 1]
- `v`: Polar angle [0, 1]

## set_torus_geominfo()

```python
set_torus_geominfo(ngmesh, major_radius, minor_radius, center=(0,0,0), axis='z', tol=0.01)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ngmesh | Mesh | required | `netgen.meshing.Mesh` object |
| major_radius | float | required | Distance from center to tube center |
| minor_radius | float | required | Tube radius |
| center | tuple | (0,0,0) | Center of torus |
| axis | str | 'z' | Torus axis ('x', 'y', or 'z') |
| tol | float | 0.01 | Tolerance for surface detection |

UV mapping:
- `u`: Major angle [0, 1] around torus center
- `v`: Minor angle [0, 1] around tube

## set_cone_geominfo()

```python
set_cone_geominfo(ngmesh, base_radius, height, center=(0,0,0), axis='z', tol=0.01)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ngmesh | Mesh | required | `netgen.meshing.Mesh` object |
| base_radius | float | required | Radius at the base |
| height | float | required | Cone height |
| center | tuple | (0,0,0) | Center of cone base |
| axis | str | 'z' | Cone axis ('x', 'y', or 'z') |
| tol | float | 0.01 | Tolerance for surface detection |

UV mapping:
- `u`: Angular parameter [0, 2*pi]
- `v`: Height parameter [0, 1] (0 at base, 1 at apex)

## Name-based Functions

### name_occ_faces()

```python
name_occ_faces(shape, prefix="occ_face_")
```

Assigns unique names to all faces of an OCC shape. Names survive STEP round-trip.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| shape | TopoDS_Shape | required | OCC shape to name |
| prefix | str | "occ_face_" | Prefix for face names |

Returns: Number of faces named.

### export_netgen_with_names()

```python
export_netgen_with_names(cubit, geometry)
```

Exports Cubit mesh to Netgen using face name mapping. Reads Cubit surface names
(e.g., "occ_face_42") and maps them to OCC face indices.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| cubit | object | required | Cubit Python interface |
| geometry | OCCGeometry | required | OCC geometry with named faces |

Returns: `netgen.meshing.Mesh` object.

## How It Works Internally

1. Iterates through all 2D boundary elements in ngmesh
2. Checks if all vertices lie on the target surface (within tolerance)
3. For matching elements, computes UV parameters from vertex coordinates
4. Calls `el.SetGeomInfo(vertex_index, u, v)` on each Element2D
5. Returns total count of modified vertex entries

## Requirements

- NGSolve with SetGeomInfo API support (PR #232)
- Coreform Cubit 2025.3+
"""

SEAM_PROBLEM = """
# The Seam Line Problem (ACIS/OCC Kernel Mismatch)

## What Is the Seam Line?

When a cylinder (or sphere, torus, etc.) is represented in OCC (OpenCASCADE),
the parametric surface must be "cut" somewhere to create a bounded parameter
domain. For a cylinder, OCC cuts at the y=0 plane, creating a seam line.

## What Goes Wrong

This is a consequence of the ACIS/OCC kernel mismatch:

1. **Cubit (ACIS kernel)**: Represents cylinder surface as 1 face
2. **STEP export**: Writes parametric surface data
3. **OCC reimport**: Splits at seam line -> 2 faces
4. **Mismatch**: If Cubit meshes the ACIS geometry (1 face), some elements
   span across the OCC seam boundary

Elements crossing the seam have vertices on both sides of the parametric
discontinuity. When `mesh.Curve()` tries to interpolate high-order nodes,
it produces incorrect results for these elements.

## Solution 1: STEP Reimport (Simple Shapes)

Export and reimport the STEP file — this converts Cubit's internal
representation from ACIS to OCC-compatible topology:

```python
cubit.cmd("create cylinder height 2 radius 0.5")   # ACIS: 1 surface
cubit.cmd('export step "cyl.step" overwrite')       # ACIS -> STEP
cubit.cmd("reset")
cubit.cmd('import step "cyl.step" heal')   # STEP -> OCC-compatible: 2 faces
cubit.cmd("mesh volume all")               # Mesh respects OCC seam boundary
```

After reimport, Cubit's mesh aligns with OCC face boundaries because the
STEP file carries the OCC-compatible surface parametrization.

## Solution 2: Name-based Workflow (Complex Shapes)

For complex geometries (Boolean operations), create geometry directly in OCC:

```python
from netgen.occ import Box, Cylinder, gp_Pnt, gp_Ax2, gp_Dir

brick = Box(gp_Pnt(-1,-1,-1), gp_Pnt(1,1,1))
cyl = Cylinder(gp_Ax2(gp_Pnt(0,0,-2), gp_Dir(0,0,1)), 0.3, 4)
shape = brick - cyl

cubit_mesh_export.name_occ_faces(shape)   # Name before STEP export
shape.WriteStep("geometry.step")
```

This avoids the seam problem entirely because:
- Geometry is created in OCC (no ACIS/OCC mismatch)
- Face names provide reliable mapping
- No heuristic face matching needed

## When the Seam Doesn't Matter

- **Planar geometries**: No seam exists on flat surfaces
- **Gmsh 2nd order workflow**: No geometry reference needed
- **1st order meshes**: No curving, seam is irrelevant
"""

TROUBLESHOOTING = """
# Troubleshooting Netgen High-Order Curving

## mesh.Curve() Fails or Produces Wrong Results

### Symptom: RuntimeError or distorted elements

**Cause 1**: Missing SetGeomInfo for curved surfaces
```
Fix: Call set_*_geominfo() for each curved surface before mesh.Curve()
```

**Cause 2**: Elements crossing seam line
```
Fix: Use STEP reimport (simple) or name-based workflow (complex)
```

**Cause 3**: Wrong geometry reference
```
Fix: Ensure OCCGeometry is loaded from the SAME STEP file used for Cubit import
```

**Cause 4**: Wrong SetGeomInfo parameters
```
Fix: Verify radius, height, center, axis match the actual geometry
     The center parameter is the midpoint of the axis for cylinders.
     For 'create cylinder height H radius R', center is (0,0,0).
```

## Empty Mesh (0 Elements)

**Cause**: No blocks registered
```
Fix: cubit.cmd("block 1 add tet all")
     cubit.cmd("block 2 add tri all")
```

## Missing Boundary Elements

**Cause**: Only volume element block, no surface element block
```
Fix: cubit.cmd("block 2 add tri all")  # Add boundary elements
```

## "No face name matching" Warning

**Cause**: Surface names don't match expected pattern (export_netgen_with_names)
```
Fix: 1. Verify name_occ_faces() was called before STEP export
     2. Check Cubit surface names: cubit.get_entity_name('surface', sid)
     3. Use 'noheal' when importing STEP: cubit.cmd('import step "x.step" noheal')
```

## SetGeomInfo Returns 0 Modified Entries

**Cause 1**: Tolerance too small
```
Fix: Increase tol parameter (e.g., tol=0.05)
```

**Cause 2**: No boundary elements on the target surface
```
Fix: Ensure block 2 has tri elements: cubit.cmd("block 2 add tri all")
```

**Cause 3**: Wrong center/axis parameters
```
Fix: Verify geometry center and axis match Cubit's coordinate system
```

## Volume Error > 1%

**Cause**: 1st order mesh without curving
```
Fix: Apply the SetGeomInfo + mesh.Curve() workflow
     Or use Gmsh 2nd order alternative
```

## Netgen Import Error: "No module named 'netgen'"

```
Fix: NGSolve must be installed in the Python environment.
     For Cubit's Python: Cannot use NGSolve (different interpreter).
     Run with system Python that has NGSolve installed.

     # System Python with NGSolve:
     python my_script.py

     # NOT Cubit's Python:
     # "C:/Program Files/Coreform Cubit 2025.3/bin/python3/python.exe" my_script.py
```

Note: Scripts that use both Cubit and NGSolve typically use Cubit's Python
with NGSolve added to sys.path, or use system Python with Cubit added to sys.path.
"""


WORKFLOW_MULTI_SURFACE = """
# Multi-Surface SetGeomInfo Workflow

For geometries containing multiple curved surface types, call each
SetGeomInfo function separately. Each function only modifies elements
on its matching surface (within tolerance).

## Example: Cylinder with Spherical End Caps

```python
import cubit_mesh_export
from netgen.occ import OCCGeometry, Cylinder, Sphere, gp_Pnt, gp_Ax2, gp_Dir
from ngsolve import Mesh

# Create geometry with multiple curved surface types in OCC
cyl = Cylinder(gp_Ax2(gp_Pnt(0, 0, -1), gp_Dir(0, 0, 1)), 0.5, 2)
sphere_top = Sphere(gp_Pnt(0, 0, 1), 0.5)
sphere_bot = Sphere(gp_Pnt(0, 0, -1), 0.5)
# Boolean operations to create capsule shape
shape = cyl + (sphere_top * cyl)  # Example: adjust for your geometry

cubit_mesh_export.name_occ_faces(shape)
shape.WriteStep("capsule.step")
geo = OCCGeometry("capsule.step")

# Import, mesh, export...
cubit.cmd('import step "capsule.step" noheal')
cubit.cmd("volume all scheme tetmesh")
cubit.cmd("volume all size 0.08")
cubit.cmd("mesh volume all")
cubit.cmd("block 1 add tet all")
cubit.cmd("block 2 add tri all")

ngmesh = cubit_mesh_export.export_netgen_with_names(cubit, geo)

# Apply SetGeomInfo for EACH surface type separately
cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=0.5, height=2.0)
cubit_mesh_export.set_sphere_geominfo(ngmesh, radius=0.5, center=(0, 0, 1))
cubit_mesh_export.set_sphere_geominfo(ngmesh, radius=0.5, center=(0, 0, -1))

mesh = Mesh(ngmesh)
mesh.Curve(3)
```

## How Tolerance Works

Each `set_*_geominfo()` function:
1. Iterates all 2D boundary elements
2. Checks if ALL vertices lie on the target surface (within `tol`)
3. Only modifies matching elements, skips the rest

This means overlapping calls are safe - each function only touches its surface.

## Checking Coverage

```python
# After all SetGeomInfo calls, verify modification counts
n1 = cubit_mesh_export.set_cylinder_geominfo(ngmesh, ...)
n2 = cubit_mesh_export.set_sphere_geominfo(ngmesh, ...)
print(f"Cylinder: {n1} entries, Sphere: {n2} entries")

# If either returns 0, check:
# - Tolerance too small (increase tol)
# - Wrong center/radius/axis parameters
# - Boundary elements missing (need block with tri/quad)
```

## Order Independence

SetGeomInfo calls are independent and can be called in any order.
Each function writes UV parameters for its own surface type.
"""

WORKFLOW_FREEFORM = """
# Handling Unsupported Surface Types

SetGeomInfo currently supports 4 analytic surface types:
cylinder, sphere, torus, cone.

For other surfaces (ellipsoid, BSpline, freeform), there are alternatives.

## Option 1: Gmsh 2nd Order (Simplest)

If 2nd order accuracy is sufficient, avoid SetGeomInfo entirely:

```python
cubit.cmd("block 1 element type tetra10")
cubit_mesh_export.export_gmsh_v2(cubit, "mesh.msh")
mesh = Mesh(ReadGmsh("mesh.msh"))   # No geometry needed
```

## Option 2: Approximate with Nearest Analytic Shape

If the surface is close to an analytic shape, use the nearest approximation:
- Oblate/prolate spheroid -> sphere (with some error)
- Truncated cone -> cone
- Barrel shape -> cylinder (rough approximation)

The error from approximation is typically small for mesh.Curve(2).

## Option 3: OCC Geometry Without SetGeomInfo

For arbitrary OCC surfaces, export_netgen with geometry enables basic
face mapping without SetGeomInfo. mesh.Curve() may still work for
low orders on well-meshed geometries:

```python
geo = OCCGeometry("freeform.step")
ngmesh = cubit_mesh_export.export_netgen_with_names(cubit, geo)
# No SetGeomInfo - let Netgen try to curve from face geometry alone
mesh = Mesh(ngmesh)
mesh.Curve(2)  # May work, verify accuracy
```

## Option 4: Extend SetGeomInfo (Advanced)

For project-specific surfaces, the UV computation pattern can be extended.
See the existing `compute_cylinder_uv()` function in `cubit_mesh_export.py`
as a template. The key steps are:

1. Define `compute_my_surface_uv(x, y, z, ...) -> (u, v)`
2. Define `set_my_surface_geominfo(ngmesh, ..., tol=0.01) -> int`
3. The function iterates boundary elements and calls `el.SetGeomInfo(i, u, v)`

## Surface Type Identification

To identify which surface types are in your geometry:

```python
from netgen.occ import OCCGeometry
geo = OCCGeometry("geometry.step")
for i, face in enumerate(geo.shape.faces):
    print(f"Face {i}: type = {face.type}, name = {face.name}")
```

Common OCC surface types:
- Plane, Cylinder, Cone, Sphere, Torus (analytic - SetGeomInfo supported)
- BezierSurface, BSplineSurface (freeform - need Option 1-4)
- SurfaceOfRevolution, SurfaceOfLinearExtrusion (sometimes mappable)
"""

WORKFLOW_ACCURACY = """
# Accuracy Guide: Choosing the Right Order

## Volume Error by Method and Order

| Method | Order 1 | Order 2 | Order 3 | Order 4 | Order 5 |
|--------|---------|---------|---------|---------|---------|
| No curving | ~1.4% | - | - | - | - |
| Gmsh 2nd order | - | ~0.001% | - | - | - |
| SetGeomInfo | ~1.4% | ~0.003% | ~0.0004% | ~0.00005% | ~0.000006% |

## When Higher Order Matters

- **Structural/thermal FEM**: Order 2 usually sufficient
- **Electromagnetics (curl-curl)**: Order 2-3 recommended
- **Acoustic/wave propagation**: Order 3-5 for dispersion control
- **Geometry verification only**: Order 2 is fine

## Mesh Size vs Order Trade-off

For a target accuracy, you can either:
- **h-refinement**: More elements, keep order low
- **p-refinement**: Fewer elements, increase order

High-order curving (order 3+) is most beneficial when:
- Geometry has high curvature
- Coarse meshes are needed (computational cost)
- High accuracy is required on curved boundaries

## Verification Pattern

Always verify accuracy after curving:

```python
import math
from ngsolve import Integrate, CF, BND

# Volume check
expected_vol = math.pi * R**2 * H  # Exact volume
computed_vol = Integrate(CF(1), mesh)
vol_error = abs(computed_vol - expected_vol) / expected_vol * 100

# Surface area check (optional)
expected_area = 2 * math.pi * R * H + 2 * math.pi * R**2
computed_area = Integrate(CF(1), mesh, VOL_or_BND=BND)
area_error = abs(computed_area - expected_area) / expected_area * 100

print(f"Volume error: {vol_error:.4f}%")
print(f"Area error: {area_error:.4f}%")
```
"""


TOLERANCE_TUNING = """
# Tolerance Tuning Guide for SetGeomInfo

## What `tol` Controls

The `tol` parameter in `set_*_geominfo()` determines whether a boundary element
lies on the target surface. For each 2D element, the function checks:

```
For each vertex (x, y, z):
    distance = |actual_radius - expected_radius|   # For cylinder/sphere/etc.
    if distance < tol:
        vertex is on surface
    else:
        vertex is NOT on surface → skip element
```

An element is matched **only if ALL its vertices** are within `tol` of the surface.

## Default: tol = 0.01

Works well for most meshes where element size > 0.05.

## When to Increase tol

**Symptom**: `set_*_geominfo()` returns 0 (no entries modified).

| Situation | Suggested tol |
|-----------|---------------|
| Coarse mesh (size > 0.5) | 0.05 – 0.1 |
| Large geometry (radius > 10) | 0.1 – 0.5 |
| `size` comparable to `tol` | tol = size / 2 |

```python
# Default tol=0.01 may miss elements on coarse meshes
modified = cubit_mesh_export.set_cylinder_geominfo(
    ngmesh, radius=10.0, height=50.0, tol=0.5
)
print(f"Modified: {modified}")  # Should be > 0
```

## When to Decrease tol

**Symptom**: Elements from adjacent (non-target) surfaces are incorrectly matched.

This can happen when two surfaces are very close together:
```python
# Two concentric cylinders, gap = 0.1
# Use small tol to distinguish them
cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=1.0, tol=0.01)
cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=1.1, tol=0.01)
```

## Diagnostic Pattern

```python
# Step 1: Try default
n = cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=R, height=H)
print(f"Modified: {n}")

# Step 2: If n == 0, increase tol
if n == 0:
    n = cubit_mesh_export.set_cylinder_geominfo(ngmesh, radius=R, height=H, tol=0.1)
    print(f"Modified with tol=0.1: {n}")

# Step 3: Verify with volume check after Curve()
mesh = Mesh(ngmesh)
mesh.Curve(3)
vol = Integrate(CF(1), mesh)
print(f"Volume error: {abs(vol - expected) / expected * 100:.4f}%")
```

## Rule of Thumb

```
tol ≈ mesh_element_size / 5
```

Too large → matches wrong surfaces. Too small → misses target surface.
"""

UV_MATH_EXPLANATION = """
# UV Computation Mathematics

## What Are UV Parameters?

UV parameters are 2D coordinates on a 3D surface. They tell `mesh.Curve()`
where each mesh vertex sits on the CAD surface, enabling exact high-order
node placement.

```
3D point (x, y, z) ──compute_*_uv()──> 2D parameter (u, v)
                                              │
mesh.Curve(order) uses (u, v) + OCC geometry ──> high-order node positions
```

## Cylinder UV: compute_cylinder_uv()

Maps 3D point to (angle, height) on cylinder surface:

```
    axis = 'z':
    ┌─────────────┐ v=1  (top)
    │             │
    │  cylinder   │
    │  surface    │
    │             │
    └─────────────┘ v=0  (bottom)
    u=0          u=1
    (θ=0)        (θ=2π)

    u = atan2(y - cy, x - cx) / (2π)     [0, 1]
    v = (z - cz + H/2) / H               [0, 1]
```

For other axes, the angular and height coordinates rotate accordingly:
- `axis='y'`: θ = atan2(z-cz, x-cx), v = (y-cy+H/2)/H
- `axis='x'`: θ = atan2(z-cz, y-cy), v = (x-cx+H/2)/H

## Sphere UV: compute_sphere_uv()

Maps 3D point to (azimuth, polar) on sphere:

```
    u = atan2(y - cy, x - cx) / (2π)     [0, 1]  (azimuthal angle)
    v = acos((z - cz) / r) / π           [0, 1]  (polar angle)

    v=0: north pole (z = +r)
    v=0.5: equator (z = 0)
    v=1: south pole (z = -r)
```

## Torus UV: compute_torus_uv()

Maps 3D point to (major angle, minor angle):

```
    axis = 'z':

    Top view (u):                Cross-section (v):
         u=0.25                    v=0.25
          ╱───╲                      ┌─┐
    u=0.5│  o  │u=0              v=0.5│ │v=0
          ╲───╱                      └─┘
         u=0.75                    v=0.75

    θ = atan2(y - cy, x - cx)           (major angle)
    r_major = sqrt((x-cx)² + (y-cy)²)   (distance from axis)
    φ = atan2(z - cz, r_major - R)      (minor angle)

    u = θ / (2π)     [0, 1]
    v = φ / (2π)     [0, 1]
```

## Cone UV: compute_cone_uv()

Maps 3D point to (angle, height) on cone surface:

```
    axis = 'z':

    u = atan2(y - cy, x - cx)    [0, 2π]  (angle)
    v = (z - cz + H/2) / H       [0, 1]   (0=base, 1=apex)
```

Note: Cone UV uses u in [0, 2π] (not [0, 1] like cylinder).

## How SetGeomInfo Uses UV

```python
for el in ngmesh.Elements2D():
    # Check if element is on target surface
    if all_vertices_on_surface(el, tol):
        for i, vertex in enumerate(el.vertices):
            x, y, z = points[vertex.nr - 1]
            u, v = compute_*_uv(x, y, z, ...)
            el.SetGeomInfo(i, u, v)  # Attach UV to vertex
```

After SetGeomInfo, `mesh.Curve(order)`:
1. Reads (u, v) for each boundary vertex
2. Uses OCC geometry to evaluate surface at intermediate (u, v) points
3. Places high-order nodes exactly on the CAD surface
"""


def get_netgen_documentation(workflow: str = "overview") -> str:
	"""Return Netgen workflow documentation by topic."""
	topics = {
		"overview": WORKFLOW_OVERVIEW,
		"simple_cylinder": WORKFLOW_CYLINDER,
		"simple_sphere": WORKFLOW_SPHERE,
		"simple_torus": WORKFLOW_TORUS,
		"simple_cone": WORKFLOW_CONE,
		"complex_named": WORKFLOW_COMPLEX_NAMED,
		"multi_surface": WORKFLOW_MULTI_SURFACE,
		"freeform": WORKFLOW_FREEFORM,
		"accuracy": WORKFLOW_ACCURACY,
		"gmsh_2nd_order": WORKFLOW_GMSH_2ND_ORDER,
		"setgeominfo_api": SETGEOMINFO_REFERENCE,
		"seam_problem": SEAM_PROBLEM,
		"troubleshooting": TROUBLESHOOTING,
		"tolerance_tuning": TOLERANCE_TUNING,
		"uv_math": UV_MATH_EXPLANATION,
	}

	workflow = workflow.lower().strip()
	if workflow == "all":
		return "\n\n".join(topics.values())
	elif workflow in topics:
		return topics[workflow]
	else:
		return (
			f"Unknown workflow: '{workflow}'. "
			f"Available: all, {', '.join(topics.keys())}"
		)
