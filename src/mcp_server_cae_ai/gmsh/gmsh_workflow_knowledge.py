"""
GMSH end-to-end workflow documentation.

Covers complete pipelines from CAD to Radia/NGSolve.
"""

GMSH_WORKFLOW_OVERVIEW = """
# GMSH Workflow Decision Guide

## Which Workflow?

```
Need volume mesh for Radia?
├── Yes: Simple shape?
│   ├── Yes: Use OCC primitives + generate(3)
│   │         -> gmsh_to_radia()
│   └── No: Have STEP file?
│       ├── Yes: OCC importShapes + generate(3)
│       │         -> gmsh_to_radia()
│       └── No: Build with OCC booleans
│                -> gmsh_to_radia()
│
Need surface mesh for PEEC/BEM?
├── Yes: generate(2) -> gmsh_surface_to_ngsolve()
│
Need mesh for NGSolve FEM?
├── Yes: generate(3) + physical groups
│         -> ReadGmsh() or Mesh("file.msh")
│
Need structured hex mesh?
├── Simple box/cylinder: GMSH transfinite
└── Complex geometry: Use Cubit instead
```

## Key Rules

1. Always use **one kernel** (geo OR occ, never both)
2. Always **synchronize()** before meshing
3. Always define **physical groups**
4. Use **MshFileVersion 2.2** for Radia/NGSolve
5. Coordinates in **meters** (Radia convention)
"""


GMSH_RADIA_VOLUME_MESH = """
# GMSH -> Radia Volume Mesh Workflow

## Overview

```
GMSH (geometry + mesh) -> .msh file -> gmsh_to_radia() -> Radia objects
```

## Step-by-Step

```python
import gmsh
import radia as rad
from gmsh_mesh_import import gmsh_to_radia

# === GMSH Phase ===
gmsh.initialize()
gmsh.model.add("iron_core")

# Create geometry (example: C-shaped core)
box1 = gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.02, 0.02)      # bottom
box2 = gmsh.model.occ.addBox(0, 0, 0, 0.02, 0.08, 0.02)      # left
box3 = gmsh.model.occ.addBox(0, 0.06, 0, 0.1, 0.02, 0.02)    # top

# Fuse into single volume
all_boxes = [(3, box1), (3, box2), (3, box3)]
result, _ = gmsh.model.occ.fuse([all_boxes[0]], all_boxes[1:])
gmsh.model.occ.synchronize()

# Physical group
vol_tags = [t for d, t in result if d == 3]
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "iron")

# Mesh settings
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.005)
gmsh.model.mesh.generate(3)
gmsh.write("iron_core.msh")
gmsh.finalize()

# === Radia Phase ===
rad.UtiDelAll()

# Import mesh as Radia objects
core = gmsh_to_radia("iron_core.msh", mu_r=1000)

# Add permanent magnet
magnet = rad.ObjRecMag([0.05, 0.04, 0.01], [0.06, 0.02, 0.02],
                        [0, 0, 954930])
assembly = rad.ObjCnt([core, magnet])

# Solve
result = rad.Solve(assembly, 0.0001, 1000, 0)

# Compute field
B = rad.Fld(assembly, 'b', [0.05, 0.04, 0.04])
print(f"B at gap center: {B}")
```

## Element Types Supported

| GMSH Type | Radia Function | Solver |
|-----------|---------------|--------|
| Tet4 (code 4) | ObjTetrahedron | MMM (3 DOF) |
| Hex8 (code 5) | ObjHexahedron | MSC (6 DOF) |
| Wedge6 (code 6) | ObjWedge | MSC (5 DOF) |

## Tips

- Use `unit_scale=0.001` if mesh is in mm
- Use `physical_group=N` to import only one region
- Default algorithm (Delaunay) produces Tet4; use transfinite for Hex8
"""


GMSH_RADIA_PEEC_SURFACE = """
# GMSH -> Radia PEEC Surface Mesh Workflow

## Overview

```
GMSH (surface geometry) -> .msh -> gmsh_surface_to_ngsolve() -> NGSolve Mesh -> BEM/PEEC
```

## Step-by-Step

```python
import gmsh
from gmsh_mesh_import import gmsh_surface_to_ngsolve

# === GMSH Phase: Create surface mesh ===
gmsh.initialize()
gmsh.model.add("conductor")

# Define conductor surface (example: rectangular plate)
p1 = gmsh.model.occ.addPoint(0, 0, 0)
p2 = gmsh.model.occ.addPoint(0.1, 0, 0)
p3 = gmsh.model.occ.addPoint(0.1, 0.01, 0)
p4 = gmsh.model.occ.addPoint(0, 0.01, 0)
# Use OCC rectangle
rect = gmsh.model.occ.addRectangle(0, 0, 0, 0.1, 0.01)

gmsh.model.occ.synchronize()

# Physical group for the surface
gmsh.model.addPhysicalGroup(2, [rect], 1)
gmsh.model.setPhysicalName(2, 1, "conductor")

# SURFACE mesh only (not volume!)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.005)
gmsh.model.mesh.generate(2)  # 2D only!
gmsh.write("conductor.msh")
gmsh.finalize()

# === NGSolve Phase: Import ===
mesh = gmsh_surface_to_ngsolve("conductor.msh", label="conductor")

# Use with ngbem or PEEC
from ngsolve import *
fes = HDivSurface(mesh, order=0)
```

## For PEEC Edge Extraction

```python
from gmsh_mesh_import import extract_surface_edges

edges = extract_surface_edges("coil.msh", unit_scale=1.0)
# edges['edges']: list of (v0, v1) pairs
# edges['edge_centers']: (n_edges, 3) array
# edges['edge_lengths']: (n_edges,) array
```

## Notes

- Use `generate(2)` for surface-only mesh
- Tri3 and Quad4 elements supported
- Quad4 automatically split into 2 triangles for NGSolve
- 2nd order (Tri6, Quad8/9) also supported for ngbem
"""


GMSH_NGSOLVE_IMPORT = """
# GMSH -> NGSolve FEM Workflow

## Method 1: ReadGmsh (Recommended)

```python
from netgen.read_gmsh import ReadGmsh
from ngsolve import *

ngmesh = ReadGmsh("model.msh")
mesh = Mesh(ngmesh)
```

## Method 2: Direct Import

```python
from ngsolve import *
mesh = Mesh("model.msh")
```

## Complete FEM Example

```python
import gmsh
from netgen.read_gmsh import ReadGmsh
from ngsolve import *

# === GMSH ===
gmsh.initialize()
gmsh.model.add("poisson")

sphere = gmsh.model.occ.addSphere(0, 0, 0, 1.0)
gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(3, [sphere], 1)
gmsh.model.setPhysicalName(3, 1, "domain")

# Boundary
surfs = gmsh.model.getBoundary([(3, sphere)], oriented=False)
surf_tags = [abs(t) for _, t in surfs]
gmsh.model.addPhysicalGroup(2, surf_tags, 2)
gmsh.model.setPhysicalName(2, 2, "boundary")

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.2)
gmsh.model.mesh.generate(3)
gmsh.write("sphere.msh")
gmsh.finalize()

# === NGSolve ===
ngmesh = ReadGmsh("sphere.msh")
mesh = Mesh(ngmesh)

fes = H1(mesh, order=2, dirichlet="boundary")
u, v = fes.TnT()
a = BilinearForm(grad(u) * grad(v) * dx).Assemble()
f = LinearForm(1 * v * dx).Assemble()

gfu = GridFunction(fes)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs()) * f.vec
```

## Tips

- Always set `MshFileVersion = 2.2` for ReadGmsh
- Physical group names become material/boundary identifiers
- For high-order: generate then `setOrder(2)` before writing
- For Radia CoefficientFunction: `rad.RadiaField(obj, 'b')`
"""


GMSH_CAD_IMPORT = """
# CAD Import Workflow

## STEP -> GMSH -> Mesh

```python
import gmsh

gmsh.initialize()
gmsh.model.add("cad_import")

# Import STEP file
volumes = gmsh.model.occ.importShapes("assembly.step")
gmsh.model.occ.synchronize()

# List imported volumes
print(f"Imported {len(volumes)} entities")
for dim, tag in volumes:
    print(f"  dim={dim}, tag={tag}")

# Assign physical groups
vol_tags = [t for d, t in volumes if d == 3]
for i, tag in enumerate(vol_tags, 1):
    gmsh.model.addPhysicalGroup(3, [tag], i)
    gmsh.model.setPhysicalName(3, i, f"part_{i}")

# Mesh
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.01)
gmsh.model.mesh.generate(3)
gmsh.write("assembly.msh")

gmsh.finalize()
```

## Multi-Part Assembly with Fragment

```python
# Import multiple STEP files and create conformal mesh
vol1 = gmsh.model.occ.importShapes("core.step")
vol2 = gmsh.model.occ.importShapes("magnet.step")

# Fragment for conformal interface
all_vols = vol1 + vol2
result, map = gmsh.model.occ.fragment(
    [v for v in all_vols if v[0] == 3][:1],
    [v for v in all_vols if v[0] == 3][1:]
)
gmsh.model.occ.synchronize()
```

## IGES Import

```python
volumes = gmsh.model.occ.importShapes("model.iges")
```

## Tips

1. Use `fragment()` for multi-material assemblies (conformal interface)
2. Check imported geometry: `gmsh.model.getEntities(3)` for volumes
3. For complex CAD: adjust `Geometry.Tolerance` if boolean ops fail
4. Set mesh size per volume using fields or per-entity sizing
"""


GMSH_HEX_MESHING = """
# Hex Meshing in GMSH

## Approach: Transfinite Algorithm

GMSH hex meshing uses the transfinite algorithm, which requires:
1. All curves have transfinite constraints
2. All surfaces have transfinite constraints + recombine
3. All volumes have transfinite constraints

## Simple Box (Works Well)

```python
import gmsh

gmsh.initialize()
gmsh.model.add("hex_box")

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

gmsh.model.addPhysicalGroup(3, [box], 1)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(3)
gmsh.write("hex_box.msh")
gmsh.finalize()
```

## Graded Hex Mesh

```python
# Different number of elements per direction
# X-curves: 20 elements
for tag in x_curves:
    gmsh.model.mesh.setTransfiniteCurve(tag, 21)
# Y-curves: 10 elements
for tag in y_curves:
    gmsh.model.mesh.setTransfiniteCurve(tag, 11)
# Z-curves: 5 elements with progression
for tag in z_curves:
    gmsh.model.mesh.setTransfiniteCurve(tag, 6, "Progression", 1.3)
```

## Limitations

| Geometry | GMSH Hex | Solution |
|----------|----------|----------|
| Simple box | Easy | Transfinite |
| Cylinder (mapped) | Possible but tricky | Need corner specification |
| L-shape | Requires decomposition | Manual webcut or use Cubit |
| Complex solid | Very difficult | Use Cubit |
| Multi-material | fragment + per-volume transfinite | Complex setup |

## GMSH vs Cubit for Hex

| Feature | GMSH | Cubit |
|---------|------|-------|
| Simple structured hex | Good (transfinite) | Excellent (map) |
| Swept hex | Very limited | Excellent (sweep) |
| Topology decomposition | No (manual only) | webcut command |
| Auto hex | No | Some (pave scheme) |
| Mixed hex-tet | No automatic transition | autoscheme |
| Cost | Free | Commercial |

**Recommendation**: Use GMSH transfinite for simple boxes and cylinders.
Use Cubit for anything more complex.
"""


GMSH_MESH_REFINEMENT = """
# Mesh Refinement

## Local Refinement with Fields

```python
import gmsh

gmsh.initialize()
gmsh.model.add("refined")

# Create geometry
box = gmsh.model.occ.addBox(-0.1, -0.1, -0.1, 0.2, 0.2, 0.2)
gmsh.model.occ.synchronize()

# Distance from center point
p_center = gmsh.model.occ.addPoint(0, 0, 0)
gmsh.model.occ.synchronize()

f1 = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(f1, "PointsList", [p_center])

# Threshold: fine near center, coarse far
f2 = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(f2, "InField", f1)
gmsh.model.mesh.field.setNumber(f2, "SizeMin", 0.005)
gmsh.model.mesh.field.setNumber(f2, "SizeMax", 0.02)
gmsh.model.mesh.field.setNumber(f2, "DistMin", 0.01)
gmsh.model.mesh.field.setNumber(f2, "DistMax", 0.05)

gmsh.model.mesh.field.setAsBackgroundMesh(f2)

# Disable other sizing to let field control
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

gmsh.model.addPhysicalGroup(3, [box], 1)
gmsh.model.mesh.generate(3)
gmsh.write("refined.msh")
gmsh.finalize()
```

## Refinement Near Surfaces

```python
# Refine near specific surfaces (e.g., magnet surface)
f1 = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(f1, "SurfacesList", [surf_tag])
gmsh.model.mesh.field.setNumber(f1, "Sampling", 200)

f2 = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(f2, "InField", f1)
gmsh.model.mesh.field.setNumber(f2, "SizeMin", 0.001)
gmsh.model.mesh.field.setNumber(f2, "SizeMax", 0.01)
gmsh.model.mesh.field.setNumber(f2, "DistMin", 0.002)
gmsh.model.mesh.field.setNumber(f2, "DistMax", 0.02)

gmsh.model.mesh.field.setAsBackgroundMesh(f2)
```

## Curvature-Based Refinement

```python
# Automatic refinement on curved surfaces
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 20)
# ~20 elements per 2*pi of curvature
```
"""


GMSH_2D_SURFACE_MESH = """
# 2D Surface Mesh for PEEC/BEM

## When to Use Surface Mesh

- PEEC conductor analysis (SIBC handles skin effect)
- BEM with ngbem (surface integral equations)
- Shielding analysis (thin conductors)

## Create Surface Mesh

```python
import gmsh

gmsh.initialize()
gmsh.model.add("surface_conductor")

# Rectangular conductor
rect = gmsh.model.occ.addRectangle(0, 0, 0, 0.1, 0.01)
gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(2, [rect], 1)
gmsh.model.setPhysicalName(2, 1, "conductor")

# Surface mesh ONLY
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.mesh.generate(2)  # 2D, not 3D!
gmsh.write("conductor.msh")
gmsh.finalize()
```

## Import for PEEC

```python
from gmsh_mesh_import import gmsh_surface_to_ngsolve

# NGSolve mesh for BEM
mesh = gmsh_surface_to_ngsolve("conductor.msh")
```

## Complex Conductor Shapes

```python
# Coil cross-section: extrude along curve
import gmsh, math

gmsh.initialize()
gmsh.model.add("coil")

# Create circle (cross-section outline)
circle = gmsh.model.occ.addCircle(0, 0, 0, 0.05)  # radius 50mm
loop = gmsh.model.occ.addCurveLoop([circle])
disk = gmsh.model.occ.addPlaneSurface([loop])

# Extrude around axis for toroidal coil
# Or use addTorus for simple torus conductor
torus = gmsh.model.occ.addTorus(0, 0, 0, 0.1, 0.01)
gmsh.model.occ.synchronize()

# Get SURFACE of torus (not volume)
surfs = gmsh.model.getBoundary([(3, torus)], oriented=False)
surf_tags = [abs(t) for _, t in surfs]
gmsh.model.addPhysicalGroup(2, surf_tags, 1)

# Surface mesh for BEM
gmsh.model.mesh.generate(2)
```
"""


GMSH_CUBIT_VS_GMSH = """
# GMSH vs Cubit: When to Use Which

## Quick Decision

| Need | Use |
|------|-----|
| Free tool | GMSH |
| Complex hex mesh | Cubit |
| Simple tet mesh | GMSH |
| STEP import + boolean | GMSH (OCC) or Cubit (ACIS) |
| Structured hex box | Either (GMSH transfinite) |
| Swept volumes | Cubit |
| Large assembly | Either |
| CI/CD automation | GMSH (no license) |
| Teaching/learning | GMSH (free, pip install) |

## Feature Comparison

| Feature | GMSH | Cubit |
|---------|------|-------|
| **Cost** | Free (GPL) | Commercial |
| **Install** | `pip install gmsh` | Installer + license |
| **Tet meshing** | Excellent | Good |
| **Hex meshing** | Limited (transfinite) | Excellent |
| **Wedge meshing** | Via transfinite | sweep |
| **Pyramid** | Limited | Limited |
| **Boolean ops** | OCC kernel | ACIS kernel |
| **STEP import** | Yes (OCC) | Yes (ACIS) |
| **Mesh size control** | Fields (very flexible) | Intervals, sizing |
| **2nd order** | setOrder(2) | element type |
| **Python API** | Yes | Yes |
| **GUI** | Yes (Fltk) | Yes (Qt) |
| **Mesh quality** | Good | Excellent (hex) |
| **Journal files** | No equivalent | .jou for reproducibility |

## Recommended Workflow

```
Simple geometry + tet mesh
  -> GMSH (free, easy, good quality)

Complex hex mesh (C-magnet, transformer core)
  -> Cubit (superior hex algorithms)

STEP import + basic mesh
  -> GMSH (free, OCC handles most cases)

Multi-material conformal mesh
  -> GMSH fragment() + physical groups
  -> Or Cubit webcut + blocks

CI/CD pipeline
  -> GMSH (no license needed on CI server)
```

## Combined Workflow

Use Cubit for hex generation, export to GMSH format:

```
Cubit (hex mesh) -> export GMSH -> gmsh_to_radia()
                                -> ReadGmsh() -> NGSolve
```

The `cubit_mesh_export` library handles the Cubit -> GMSH export.
"""


GMSH_TROUBLESHOOTING = """
# GMSH Troubleshooting

## "No elements in mesh"

**Cause**: Missing `synchronize()` before `generate()`.

```python
# Fix: Add synchronize
gmsh.model.occ.synchronize()
gmsh.model.mesh.generate(3)
```

## "Invalid mesh" / Zero-volume elements

**Cause**: Degenerate geometry, very small features, or bad topology.

```python
# Fix 1: Increase geometry tolerance
gmsh.option.setNumber("Geometry.Tolerance", 1e-4)

# Fix 2: Heal geometry
gmsh.model.occ.healShapes()
gmsh.model.occ.synchronize()

# Fix 3: Optimize after generation
gmsh.model.mesh.generate(3)
gmsh.model.mesh.optimize("Netgen")
```

## "ReadGmsh fails" / NGSolve import error

**Cause**: Wrong MSH version (v4 instead of v2.2).

```python
# Fix: Set v2.2
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
```

## "No physical groups" warning from Radia/NGSolve

**Cause**: Physical groups not defined before writing.

```python
# Fix: Add physical groups
gmsh.model.addPhysicalGroup(3, vol_tags, 1)
gmsh.model.setPhysicalName(3, 1, "material")
```

## Mesh too coarse / too fine

```python
# Fix: Control mesh size
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0.001)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.01)
```

## Boolean operation fails

```python
# Fix 1: Increase tolerance
gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-4)

# Fix 2: Heal shapes first
gmsh.model.occ.healShapes()

# Fix 3: Use fragment instead of fuse/cut
result, map = gmsh.model.occ.fragment(obj, tool)
```

## Transfinite fails

**Cause**: Surface has wrong number of boundary curves (need 3 or 4).

```python
# Check boundary
bounds = gmsh.model.getBoundary([(2, surf_tag)])
print(f"Surface {surf_tag} has {len(bounds)} boundary curves")
# Must be 3 or 4 for transfinite
```

## Performance: Large meshes

```python
# Enable multi-threading
gmsh.option.setNumber("General.NumThreads", 4)
gmsh.option.setNumber("Mesh.MaxNumThreads3D", 4)

# Use binary format for large meshes
gmsh.option.setNumber("Mesh.Binary", 1)

# Use HXT algorithm (faster for large meshes)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT
```

## Memory issues

```python
# Reduce element count
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", larger_value)

# Or use adaptive refinement (fine only where needed)
# See mesh_fields documentation
```
"""


def get_gmsh_workflow_documentation(topic: str = "all") -> str:
    """Get GMSH workflow documentation by topic."""
    TOPICS = {
        "overview": GMSH_WORKFLOW_OVERVIEW,
        "radia_volume_mesh": GMSH_RADIA_VOLUME_MESH,
        "radia_peec_surface": GMSH_RADIA_PEEC_SURFACE,
        "ngsolve_import": GMSH_NGSOLVE_IMPORT,
        "cad_import": GMSH_CAD_IMPORT,
        "hex_meshing": GMSH_HEX_MESHING,
        "mesh_refinement": GMSH_MESH_REFINEMENT,
        "2d_surface_mesh": GMSH_2D_SURFACE_MESH,
        "cubit_vs_gmsh": GMSH_CUBIT_VS_GMSH,
        "troubleshooting": GMSH_TROUBLESHOOTING,
    }

    topic = topic.lower().strip()

    if topic == "all":
        toc = "# GMSH Workflow Guide\n\nTopics: " + ", ".join(TOPICS.keys()) + "\n\n"
        return toc + "\n\n---\n\n".join(TOPICS.values())

    if topic in TOPICS:
        return TOPICS[topic]

    return f"Unknown topic: '{topic}'. Valid topics: {', '.join(TOPICS.keys())}"
