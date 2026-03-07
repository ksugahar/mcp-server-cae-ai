"""
Radia library usage knowledge base for Radia MCP server.

Covers the core Radia BEM library API: geometry creation, materials,
solving, field computation, mesh import, and best practices.
"""

RADIA_OVERVIEW = """
# Radia Library Overview

Radia is a boundary element method (BEM) / integral method library for
computing magnetostatic fields in unbounded domains. Written in C++ with
Python bindings (pybind11).

## Key Advantages over FEM

- **No air mesh**: Only discretize magnetic materials, not surrounding air
- **Naturally open boundaries**: No truncation or absorbing layers
- **Exact for permanent magnets**: Analytical integrals for simple shapes
- **Efficient for thin structures**: No volume meshing of thin conductors

## Core Workflow

```
1. rad.UtiDelAll()       # Clear previous objects
2. Create geometry       # ObjHexahedron, ObjRecMag, etc.
3. Apply materials       # MatLin, MatSatIsoFrm, etc.
4. rad.Solve(...)        # Compute magnetization
5. rad.Fld(...)          # Evaluate fields
6. rad.UtiDelAll()       # Cleanup
```

Note: Radia always uses meters. All coordinates are in meters.

## Module Structure

- `import radia as rad` - Main module (re-exports from _radia_pybind)
- C++ backend: pybind11 bindings in _radia_pybind.pyd
"""

RADIA_GEOMETRY = """
# Geometry Creation

## Simple Objects

| Function | Description | DOF Type |
|----------|-------------|----------|
| `ObjRecMag(center, dims, M)` | Rectangular magnet | 3 DOF (MMM) |
| `ObjHexahedron(vertices, M)` | 8-vertex hexahedron | 6 DOF (MSC) |
| `ObjTetrahedron(vertices, M)` | 4-vertex tetrahedron | 3 DOF (MMM) |
| `ObjThckPgn(z, dz, polygon, axis, M)` | Extruded polygon | varies |
| `ObjPolyhdr(vertices, faces, M)` | General polyhedron | varies |

## DOF Types

- **MMM (3 DOF)**: Volume magnetization, 3 components. For tetrahedra.
- **MSC (6 DOF)**: Magnetic surface charge on faces. For hexahedra.
  Better accuracy per element but requires convex shapes.

## Examples

```python
import radia as rad
import numpy as np

rad.UtiDelAll()

# Rectangular permanent magnet: 20x20x10 mm, Br=1.2T in Z
mag = rad.ObjRecMag([0, 0, 0], [0.02, 0.02, 0.01], [0, 0, 955000])

# Hexahedron with 8 vertices
verts = [
    [-0.01, -0.01, -0.005], [0.01, -0.01, -0.005],
    [0.01, 0.01, -0.005], [-0.01, 0.01, -0.005],
    [-0.01, -0.01, 0.005], [0.01, -0.01, 0.005],
    [0.01, 0.01, 0.005], [-0.01, 0.01, 0.005]
]
hex_elem = rad.ObjHexahedron(verts, [0, 0, 0])
```

## Current Sources

| Function | Description |
|----------|-------------|
| `ObjArcCur(center, [r_min, r_max], [phi_min, phi_max], h, n_sec, j)` | Arc/circular coil |
| `ObjFlmCur(points, current)` | Filament (Biot-Savart) |
| `ObjRaceTrk(center, radii, heights, current, n_seg)` | Racetrack coil |

```python
# Full circular coil: R=50mm, 1mm cross-section, J=1e6 A/m^2
coil = rad.ObjArcCur([0, 0, 0], [0.0495, 0.0505],
                     [-np.pi, np.pi], 0.001, 100, 1e6)
```

## Background Field

```python
# IMPORTANT: ObjBckg requires a CALLABLE, not a list!
MU_0 = 4 * np.pi * 1e-7

# Correct: lambda or function
ext = rad.ObjBckg(lambda p: [0, 0, MU_0 * 200000])

# WRONG - will fail silently or error:
# ext = rad.ObjBckg([0, 0, MU_0 * 200000])

# Non-uniform field
def gradient_field(p):
    x, y, z = p
    G = 10.0  # T/m
    return [G * y, G * x, 0]
ext = rad.ObjBckg(gradient_field)
```

## Containers

```python
container = rad.ObjCnt([obj1, obj2, obj3])
grp = rad.ObjCnt([container, background])
```
"""

RADIA_MATERIALS = """
# Material Definition

## Linear Materials

```python
# Isotropic: scalar mu_r
mat_iron = rad.MatLin(1000)  # mu_r = 1000
rad.MatApl(obj, mat_iron)

# Anisotropic: [mu_parallel, mu_perp], easy_axis
mat_aniso = rad.MatLin([5000, 100], [0, 0, 1])
rad.MatApl(obj, mat_aniso)
```

## Nonlinear Materials

### B-H Table (Industry Standard)

```python
# Format: [[H (A/m), B (T)], ...]
BH_STEEL = [
    [0.0, 0.0], [100.0, 0.1], [500.0, 0.8],
    [1000.0, 1.2], [5000.0, 1.7], [100000.0, 2.1]
]
mat = rad.MatSatIsoTab(BH_STEEL)
rad.MatApl(core, mat)
```

### Tanh Formula (Analytical)

```python
# M = ms1*tanh(ksi1*H/ms1) + ms2*tanh(ksi2*H/ms2) + ms3*tanh(ksi3*H/ms3)
mat = rad.MatSatIsoFrm(
    [1596.3, 1.1488],   # [ksi1, ms1]
    [133.11, 0.4268],   # [ksi2, ms2]
    [18.713, 0.4759]    # [ksi3, ms3]
)
rad.MatApl(core, mat)
```

### Standard Material Library

```python
# Pre-defined materials (name-based lookup)
mat = rad.MatStd('NdFeB')   # Neodymium Iron Boron
mat = rad.MatStd('Xc06')    # Low-carbon steel
rad.MatApl(obj, mat)
```

## Material Application

```python
# Apply to single object
rad.MatApl(hex_elem, mat)

# Apply to container (all children)
rad.MatApl(container, mat)
```
"""

RADIA_SOLVING = """
# Solving the Magnetostatic Problem

## rad.Solve()

```python
result = rad.Solve(obj, tolerance, max_iter, method)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| obj | int | Container with geometry + background field |
| tolerance | float | Nonlinear convergence tolerance (e.g., 0.001 = 0.1%) |
| max_iter | int | Maximum iterations |
| method | int | 0=LU (direct), 1=BiCGSTAB, 2=HACApK (H-matrix) |

## Solver Selection Guide

| Problem Size | Method | Notes |
|-------------|--------|-------|
| <500 elements | LU (0) | Fastest, O(N^3) memory |
| 500-5000 elements | BiCGSTAB (1) | Default, iterative |
| >5000 elements | HACApK (2) | H-matrix, O(N log N) |

## Return Value

```python
result = rad.Solve(grp, 0.001, 100, 0)
# result = [residual, ?, ?, max_dM, max_dH]
```

## Example

```python
rad.UtiDelAll()

# Create geometry
verts = [[-0.01,-0.01,-0.01], [0.01,-0.01,-0.01],
         [0.01,0.01,-0.01], [-0.01,0.01,-0.01],
         [-0.01,-0.01,0.01], [0.01,-0.01,0.01],
         [0.01,0.01,0.01], [-0.01,0.01,0.01]]
cube = rad.ObjHexahedron(verts, [0, 0, 0])
mat = rad.MatLin(1000)
rad.MatApl(cube, mat)

# Background field
MU_0 = 4 * np.pi * 1e-7
ext = rad.ObjBckg(lambda p: [0, 0, MU_0 * 200000])
grp = rad.ObjCnt([cube, ext])

# Solve
result = rad.Solve(grp, 0.001, 100, 0)
```

## Advanced Solver Configuration

```python
# All solver parameters via unified SolverConfig()
rad.SolverConfig(
    bicgstab_tol=1e-4,
    hacapk_eps=1e-4, hacapk_leaf=10, hacapk_eta=2.0,
    relax_param=0.3,
    newton_method=True,
    newton_damping=True, newton_damping_max_iter=5, newton_damping_min_omega=0.01
)

# Query current settings
config = rad.GetSolverConfig()
```

## IMA (Image Method of Analysis) Symmetry

IMA exploits mirror symmetry to reduce problem size (half, quarter, eighth model).
All three solvers (LU, BiCGSTAB, HACApK) support IMA via the `image=` parameter.

```python
# Quarter model with x-mirror (symmetric) and z-mirror (antisymmetric)
# For Z-directed field: Bz is parallel to x-plane (+) and perpendicular to z-plane (-)
rad.Solve(container, 0.001, 100, 2, image='+x-z')

# Pre-build matrix with IMA (optional, for matrix inspection)
handle = rad.BuildMatrix(model, image='+x-z')
matrix, dof = rad.GetInteractMatrix(handle)
```

### IMA Sign Selection Policy

| Field vs Mirror Plane | IMA Sign |
|----------------------|----------|
| Field **parallel** to mirror | **+** (symmetric) |
| Field **perpendicular** to mirror | **-** (antisymmetric) |

### Supported Symmetry Combinations

| `image=` | Reduction | Example |
|----------|-----------|---------|
| `'+x'` | Half model | x-mirror only |
| `'+x-z'` | Quarter model | x + z mirrors |
| `'+x+y-z'` | Eighth model | x + y + z mirrors |

### IMA Boundary Element Limitation

IMA may produce incorrect results (~0.5x magnitude) for **boundary elements** whose
faces lie ON the symmetry plane, when observation points are also on that plane.

**When IMA is Safe**:
- Elements offset from symmetry planes (not touching)
- Observation points off-plane
- MMM (tetrahedra) -- no limitation
"""

RADIA_PARALLELIZATION = """
# Parallelization Architecture

Radia uses NGSolve's TaskManager for all parallelism. There is no OpenMP dependency.
The TaskManager is a work-stealing thread pool initialized when `import radia` loads
ngcore.dll.

## Thread Control

Thread count is determined by the TaskManager. By default, it uses all available cores.
To control thread count from Python, use NGSolve's API:

```python
import ngsolve
ngsolve.SetNumThreads(8)  # Set thread count BEFORE solving
```

Or equivalently via the `with TaskManager(n)` context manager in NGSolve scripts.

**IMPORTANT**: `import radia` must come BEFORE `import ngsolve`. This is because
Radia's `__init__.py` imports ngsolve internally for DLL resolution (ngcore.dll),
which initializes the TaskManager. If ngsolve is imported first with a different
thread count, there can be conflicts.

## How Each Solver Uses Parallelism

| Solver | Method | Parallelization |
|--------|--------|-----------------|
| LU (method=0) | MKL `dgesv_` | `SuspendTaskManager` + `MKLThreadGuard` enables MKL multi-threading |
| BiCGSTAB (method=1) | Matrix-vector product | `ParallelFor` via TaskManager |
| HACApK (method=2) | H-matrix build + BiCGSTAB | `ParallelFor` / `ParallelForRange` via TaskManager |

### LU Solver Threading Detail

NGSolve sets `mkl_set_num_threads(1)` globally to prevent conflicts with TaskManager.
When Radia's LU solver calls `dgesv_`, it uses `MKLThreadGuard` RAII to temporarily
re-enable multi-threaded MKL, then `SuspendTaskManager` to avoid contention:

```cpp
// C++ internals (rad_relaxation_methods.cpp)
{
    ngcore::SuspendTaskManager stm;          // Pause TaskManager threads
    radia::MKLThreadGuard mkl_guard(nthreads); // Enable MKL multi-threading
    dgesv_(&n, &nrhs, A, &n, ipiv, b, &n, &info);
}   // Both guards restore original state on scope exit
```

### HACApK (H-Matrix) Threading

H-matrix construction and BiCGSTAB iterations use TaskManager `ParallelFor`:
- Matrix assembly: parallel over element pairs
- ACA+ low-rank approximation: parallel over admissible blocks
- BiCGSTAB matrix-vector product: parallel over H-matrix leaf nodes

## Querying Thread Info

```python
import radia as rad

# After rad.Solve():
stats = rad.GetSolveStats()
print(stats['num_threads'])         # e.g., 8
print(stats['taskmanager_enabled']) # True
print(stats['t_matrix_build'])      # Matrix build time [s]
print(stats['t_linear_solve'])      # Linear solve time [s]
print(stats['t_lu_decomp'])         # LU decomposition time [s] (LU only)
print(stats['t_hmatrix_build'])     # H-matrix build time [s] (HACApK only)
```

## Other Parallelized Operations

| Operation | File | Method |
|-----------|------|--------|
| Interaction matrix build | `rad_interaction.cpp` | `ParallelFor` |
| Field computation (Fld, FldLst) | `rad_field_unified.cpp` | `ParallelFor` |
| Analytical poly integrals | `rad_poly_analytical.cpp` | `ParallelFor` |
| Scalar potential batch | `rad_material_impl.cpp` | `ParallelFor` |
| Vector potential batch | `rad_material_impl.cpp` | `ParallelFor` |

## NGSolve Compatibility

Since Radia and NGSolve share the same TaskManager, they coexist naturally:

```python
import radia as rad  # Initializes TaskManager (loads ngcore.dll)
from ngsolve import *

# Radia solve (uses TaskManager internally)
rad.Solve(grp, 0.001, 100, 2)

# NGSolve BEM assembly (also uses TaskManager)
with TaskManager():
    V_op = LaplaceSL(j_trial.Trace() * ds) * j_test.Trace() * ds
```

No thread conflict because both use the same underlying TaskManager instance.

## Scaling Benchmarks (8 threads, cube hexahedron nonlinear)

| Solver | Time Scaling | Memory Scaling |
|--------|-------------|----------------|
| LU | O(N^3.5) | O(N^1.8) |
| BiCGSTAB | O(N^2.5) | O(N^1.9) |
| HACApK | O(N^1.7) | O(N^1.2) |

HACApK achieves near-linear scaling for both time and memory, enabling
problems with >10,000 elements that would be infeasible with dense solvers.
"""

RADIA_FIELDS = """
# Field Computation

## Single Point

```python
field = rad.Fld(obj, component, [x, y, z])
```

### Component Options

| Component | Type | Unit | Description |
|-----------|------|------|-------------|
| 'b', 'bx', 'by', 'bz' | vector/scalar | T | Magnetic flux density |
| 'h', 'hx', 'hy', 'hz' | vector/scalar | A/m | Magnetic field strength |
| 'a', 'ax', 'ay', 'az' | vector/scalar | T*m | Vector potential |
| 'p', 'phi' | scalar | A | Scalar potential |
| 'm', 'mx', 'my', 'mz' | vector/scalar | A/m | Magnetization |

### Examples

```python
B = rad.Fld(mag, 'b', [0, 0, 0.05])       # [Bx, By, Bz]
Bz = rad.Fld(mag, 'bz', [0, 0, 0.05])     # Scalar Bz
H = rad.Fld(mag, 'h', [0, 0, 0.05])        # [Hx, Hy, Hz]
```

## Field Along a Line

```python
field_values = rad.FldLst(obj, 'bz', start, end, n_points, 'arg')
# Returns n_points field values along line from start to end
```

## Field Integration

```python
flux = rad.FldInt(obj, component, start, end, axis)
```

## VTK Export

```python
rad.FldVTS(obj, 'output.vts',
           x_range=[-0.1, 0.1],
           y_range=[-0.1, 0.1],
           z_range=[0.0, 0.2],
           nx=21, ny=21, nz=21,
           include_B=1, include_H=0)
```

## Querying Magnetization

```python
all_M = rad.ObjM(container)    # [[center, [Mx,My,Mz]], ...]
rad.ObjSetM(obj, [Mx, My, Mz])  # Set magnetization manually
```
"""

RADIA_MESH_IMPORT = """
# NGSolve Mesh Import

Convert Netgen/NGSolve meshes to Radia geometry objects.

## Key Module

```python
from radia.netgen_mesh_import import netgen_mesh_to_radia
```

## Supported Element Types

| Element | Radia Object | DOF |
|---------|-------------|-----|
| Tetrahedron (ET.TET) | ObjTetrahedron | 3 DOF (MMM) |
| Hexahedron (ET.HEX) | ObjHexahedron | 6 DOF (MSC) |
| Wedge (ET.PRISM) | ObjWedge | 5 DOF |
| Pyramid | ObjPolyhdr | varies |

## Basic Usage

```python
import radia as rad
from ngsolve import *
from radia.netgen_mesh_import import netgen_mesh_to_radia

rad.UtiDelAll()

# Create/load NGSolve mesh
from netgen.occ import Box, Pnt, OCCGeometry
box = Box(Pnt(-0.5, -0.5, -0.5), Pnt(0.5, 0.5, 0.5))
mesh = Mesh(OCCGeometry(box).GenerateMesh(maxh=0.3))

# Convert to Radia
container = netgen_mesh_to_radia(
    mesh,
    material={'magnetization': [0, 0, 0]},
    units='m',
    material_filter='magnetic'
)

# Apply material and solve
mat = rad.MatLin(1000)
rad.MatApl(container, mat)
```

## GMSH Import

```python
from radia.gmsh_mesh_import import gmsh_to_radia

container = gmsh_to_radia(
    'mesh.msh',           # GMSH v2 ASCII format
    unit_scale=0.001,     # mm -> m conversion
    magnetization=[0, 0, 0]
)
```

## Cubit Direct Import

```python
from radia.netgen_mesh_import import cubit_hex_to_radia

# After Cubit meshing
container = cubit_hex_to_radia(
    cubit_mesh_data,
    magnetization=[0, 0, 0]
)
```

## NGSolve Magnetization -> Radia Open Boundary Field Evaluation

NGSolve FEM solves M(x) inside bounded domains but cannot easily compute fields
in unbounded external regions (needs PML). Radia provides natural open boundary
field evaluation using exact analytical formulas (NOT dipole approximation).

Pipeline:
```
NGSolve FEM Solve -> M per element -> netgen_mesh_to_radia() -> Radia objects -> rad.Fld()
```

IMPORTANT: Do NOT use dipole approximation (m=M*V). Register elements as proper
Radia ObjHexahedron/ObjTetrahedron with solved magnetization. Radia's surface
charge/surface current analytical formulas are exact for constant M per element.

```python
import radia as rad
from ngsolve import *
from radia.netgen_mesh_import import netgen_mesh_to_radia

rad.UtiDelAll()

# 1. NGSolve solves nonlinear problem -> M per element

# 2. Convert mesh to Radia objects with per-element magnetization
def material_from_ngsolve(el_idx):
    M = get_element_magnetization(gf_M, mesh, el_idx)  # user function
    return {'magnetization': M.tolist()}

container = netgen_mesh_to_radia(mesh, material=material_from_ngsolve, units='m')
# No Solve() needed - M is already known from NGSolve

# 3. Evaluate field at arbitrary external points (exact analytical formulas)
B = rad.Fld(container, 'b', [0, 0, 0.1])
```

Why Radia objects, not dipoles:
- Surface charge model is exact for constant M (zero approximation error)
- No distance limitation (dipoles fail at r < 2 * element_size)
- netgen_mesh_to_radia() already supports per-element material via callable
"""

RADIA_BEST_PRACTICES = """
# Radia Best Practices

## 1. Units: Always Meters

Radia always uses meters. All coordinates must be specified in meters.
`rad.FldUnits()` has been removed. Do not call it.

## 2. Always Clean Up

```python
rad.UtiDelAll()     # At start of script AND at end
```

## 3. ObjBckg Requires Callable

```python
# CORRECT
ext = rad.ObjBckg(lambda p: [0, 0, B_value])

# WRONG - silent failure!
ext = rad.ObjBckg([0, 0, B_value])
```

## 4. Choose Solver Method by Size

- <500 elements: LU (method=0)
- 500-5000: BiCGSTAB (method=1)
- >5000: HACApK (method=2)

## 5. Magnetization Units

- Permanent magnets: M in A/m (e.g., 955000 A/m for NdFeB, ~1.2T)
- Conversion: M = Br / mu_0

## 6. B-H Table Format

- Always [[H in A/m, B in Tesla], ...]
- Must be monotonically increasing
- Start from [0, 0]

## 7. Hexahedra Must Be Convex

- ObjHexahedron requires convex shapes
- Non-convex hexahedra cause incorrect surface normals
- For complex shapes, use tetrahedra

## 8. NGSolve Integration

- **Import radia BEFORE ngsolve**: Radia's `__init__.py` imports ngsolve
  internally to locate ngcore.dll and initialize the TaskManager thread pool.
  If ngsolve is imported first, thread pool configuration may conflict.
- Radia and NGSolve share the same TaskManager (ngcore), so they coexist
  without thread conflicts.
- Radia always uses meters (all coordinates in meters)
- Use `netgen_mesh_to_radia()` for mesh conversion (not manual extraction)

## 9. Convergence Checks

```python
result = rad.Solve(grp, 0.001, 1000, 1)
# Check result[3] (max_dM) - should decrease each iteration
# Typical convergence: 3-6 iterations for linear, 10-50 for nonlinear
```

## 10. Field Evaluation Points

- Do NOT evaluate ON element surfaces (singularity)
- Offset evaluation points slightly from boundaries
- Use rad.FldLst for systematic field profiles
"""


RADIA_PEEC = """
# PEEC (Partial Element Equivalent Circuit)

Radia includes a PEEC solver for conductor analysis: inductance, resistance,
and capacitance extraction from 3D conductor geometries.

## Architecture

```
FastHenry .inp file  -->  FastHenryParser  -->  PEECBuilder (C++)  -->  PEECCircuitSolver
                                                                    -->  CoupledPEECSolver (with mag. core)
                                                                    -->  ShieldedPEECSolver (with BEM shield)
```

## Key Modules

| Module | Class | Purpose |
|--------|-------|---------|
| `peec_matrices.pyd` | `PEECBuilder` | C++ matrix assembly (L, R, P matrices) |
| `peec_topology.py` | `PEECCircuitSolver` | MNA nodal admittance circuit solver |
| `peec_coupled.py` | `CoupledPEECSolver` | Conductor + magnetic core coupling |
| `peec_shielded.py` | `ShieldedPEECSolver` | Conductor + BEM shield coupling |
| `fasthenry_parser.py` | `FastHenryParser` | FastHenry .inp file parser |

## Quick Start: FastHenry Input

```python
from fasthenry_parser import FastHenryParser

parser = FastHenryParser()
parser.parse_string(\"\"\"
.Units mm
.default sigma=5.8e7

N1 x=0 y=0 z=0
N2 x=100 y=0 z=0

E1 N1 N2 w=1 h=1 nwinc=3 nhinc=3

.external N1 N2
.freq fmin=100 fmax=1e6 ndec=5
.end
\"\"\")

result = parser.solve()
print(f"DC: R={result['R'][0]*1e3:.3f} mOhm, L={result['L'][0]*1e9:.1f} nH")
```

## Topology API (Node-Segment)

```python
from peec_matrices import PEECBuilder
from peec_topology import PEECCircuitSolver

builder = PEECBuilder()
n1 = builder.add_node_at(0, 0, 0)
n2 = builder.add_node_at(0.05, 0, 0)
n3 = builder.add_node_at(0.1, 0, 0)
builder.add_connected_segment(n1, n2, 1e-3, 1e-3, sigma=5.8e7)
builder.add_connected_segment(n2, n3, 1e-3, 1e-3, sigma=5.8e7)
builder.add_port(n1, n3)

topo = builder.build_topology()
solver = PEECCircuitSolver(topo)
Z = solver.compute_port_impedance(freq=1e6)
```

## Multi-Filament (Skin/Proximity Effect)

Use `nwinc` and `nhinc` to subdivide conductor cross-sections:

```python
# 5x5 = 25 parallel sub-filaments for skin effect
builder.add_connected_segment(n1, n2, 3e-3, 3e-3, sigma=5.8e7, nwinc=5, nhinc=5)
```

## Magnetic Core Coupling (.magnetic block)

```
.magnetic
  type=box
  center=0,0,0
  size=15,15,10
  divisions=3,3,2
  mu_r=1000
.endmagnetic
```

## Accuracy Parameters

### CRITICAL: Circular Coil Segment Count

| n_seg | Circle Error | Delta_L Error (vs FEM) |
|-------|-------------|----------------------|
| 16 | ~1% near core | ~26% |
| 32 | ~0.3% | ~15% |
| **64** | **<0.1%** | **~9%** |

**Rule**: Use n_seg >= 64 for circular coils when computing coupling with nearby objects.

### Core Mesh Divisions

| Divisions | Elements | Delta_L Error |
|-----------|----------|---------------|
| 2,2,1 | 4 | ~26% |
| **3,3,2** | **18** | **~9%** |
| 5,5,3 | 75 | ~5% |

### Bessel SIBC for Circular Wire

**CRITICAL**: Use modified Bessel functions `iv` (I0, I1), NOT regular `jv` (J0, J1):

```python
from scipy.special import iv  # CORRECT: modified Bessel

k = np.sqrt(1j * omega * mu * sigma)
Z_internal = (k * length) / (2 * np.pi * radius * sigma) * (iv(0, k*radius) / iv(1, k*radius))
```

Using `jv` gives correct R_ac/R_dc but WRONG SIGN on internal inductance.

### Internal Inductance Double-Counting

When computing air inductance with Neumann formula (GMD-based):
- Neumann GMD already includes internal inductance (Li/4)
- Do NOT add SIBC internal impedance on top: `use_sibc=False`
- Only use SIBC when computing AC impedance (frequency-dependent skin effect)
"""

RADIA_NGBEM_PEEC = """
# PEEC with ngbem (NGSolve BEM)

ngsbem provides Galerkin BEM assembly for PEEC impedance extraction.
The key insight is that the PEEC Loop-Star decomposition maps directly
to NGSolve function spaces: `HDivSurface` (Loop) x `SurfaceL2` (Star).

## Architecture

```
Surface Mesh (Netgen OCC)
  |
  +-> NGBEMPEECSolver (ngbem_peec.py)
  |     - L matrix: LaplaceSL on HDivSurface (inductance)
  |     - P matrix: SingleLayerPotential on SurfaceL2 (capacitance)
  |     - M_LS:     div coupling (FEM, not BEM)
  |     - R:        sheet resistance from sigma, thickness
  |     - solve_frequency() -> Z(f) = R + jwL (MQS) or full Loop-Star
  |
  +-> ShieldBEMSIBC (ngbem_eddy.py)
  |     - BEM + SIBC for conducting shields
  |     - compute_impedance_matrix() -> Delta_Z (shield coupling)
  |
  +-> CoupledPEECMMM (ngbem_coupled.py)
        - Image method for ferrite core coupling
        - compute_delta_L() -> Delta_L (freq-independent)
```

## Key Modules

| Module | Class | Purpose |
|--------|-------|---------|
| `ngbem_peec.py` | `NGBEMPEECSolver` | Galerkin PEEC: L, P, M_LS assembly + impedance sweep |
| `ngbem_eddy.py` | `ShieldBEMSIBC` | Loop-only BEM+SIBC for conducting shields |
| `ngbem_eddy.py` | `LoopBasisBuilder` | Div-free loop basis from face-edge topology |
| `ngbem_coupled.py` | `CoupledPEECMMM` | Ferrite core coupling via image method |
| `ngbem_interface.py` | `extract_edge_geometry` | Bridge: ngbem mesh to PEEC topology |

## Quick Start: Plate Impedance

```python
from ngbem_peec import NGBEMPEECSolver, create_plate_mesh
import numpy as np

# Create conductor surface mesh
mesh = create_plate_mesh(0.01, 0.01, maxh=0.003, label="conductor")

# Assemble PEEC matrices (Galerkin BEM)
solver = NGBEMPEECSolver(mesh, conductor_label="conductor",
                          sigma=5.8e7, thickness=35e-6, order=0)
solver.assemble()

# MQS frequency sweep (10 Hz - 1 MHz)
freqs = np.logspace(1, 6, 50)
Z = solver.solve_frequency(freqs, mode='mqs')
L_nH = np.imag(Z) / (2 * np.pi * freqs) * 1e9
```

## CRITICAL: .Trace() Requirement for LaplaceSL on HDivSurface

When assembling BEM operators (LaplaceSL, HelmholtzSL) on HDivSurface,
you MUST use `.Trace()` on both trial and test functions:

```python
# CORRECT - with .Trace()
j_trial, j_test = fes_J.TnT()
V_op = LaplaceSL(j_trial.Trace() * ds(label)) * j_test.Trace() * ds(label)

# WRONG - without .Trace() -> corrupted boundary-edge DOFs
V_op = LaplaceSL(j_trial * ds(label)) * j_test * ds(label)
```

**Bug symptom**: Without `.Trace()`, boundary-edge DOFs (RWG basis functions
with support on only 1 triangle) get corrupted diagonal entries (e.g., -1.1e+11
instead of ~1e-10). This causes wildly wrong inductance values.

**Diagnostic**: Extract dense matrix and check diagonal:
```python
M = extract_dense(V_op.mat, n_J)
diag = np.real(np.diag(M))
print(f"min diag = {diag.min():.3e}")  # Should be positive (~1e-10)
# If any diagonal < 0 or >> 1e-5: missing .Trace()
```

**Note**: `.Trace()` is a purely mathematical operation (tangential trace
projection for H(div) functions). It is NOT related to physical thickness.
Same `.Trace()` requirement applies to HelmholtzSL.

Fixed in NGBEMPEECSolver (2026-02-23).

## Air-Core Coil Inductance (Standalone ngbem)

Direct BEM inductance computation WITHOUT the PEEC framework.
Uses Hodge decomposition to extract the harmonic current mode on a genus-1
surface (ring/frame), then computes L via the L/R ratio formula.

### Single Loop Pattern

```python
import numpy as np
from scipy.linalg import null_space
from ngsolve import Mesh, HDivSurface, SurfaceL2, BilinearForm, ds, BND, TaskManager, InnerProduct
from ngsolve import div as ng_div
from ngsolve.bem import LaplaceSL

MU_0 = 4e-7 * np.pi

# 1. Create ring mesh (circular or rectangular frame)
mesh = create_ring_mesh(R_center, trace_width, maxh)
fes_J  = HDivSurface(mesh, order=0)   # RWG edge-based
fes_L2 = SurfaceL2(mesh, order=0)     # face-based
n_J, n_v, n_f = fes_J.ndof, mesh.nv, fes_L2.ndof

# 2. Divergence matrix D (face x edge)
u_J, q_L2 = fes_J.TrialFunction(), fes_L2.TestFunction()
bf_D = BilinearForm(trialspace=fes_J, testspace=fes_L2)
bf_D += ng_div(u_J.Trace()) * q_L2 * ds
bf_D.Assemble()
D = extract_rect(bf_D.mat, n_f, n_J)

# 3. Incidence matrix C (edge x vertex)
C = np.zeros((n_J, n_v))
for e_idx, edge in enumerate(mesh.edges):
    verts = list(edge.vertices)
    C[e_idx, verts[0].nr] = -1
    C[e_idx, verts[1].nr] = +1

# 4. Mass matrix M_J
u2, v2 = fes_J.TnT()
bf_M = BilinearForm(fes_J)
bf_M += InnerProduct(u2.Trace(), v2.Trace()) * ds
bf_M.Assemble()
M_J = np.real(extract_dense(bf_M.mat, n_J))

# 5. Hodge decomposition: harmonic mode = null([D; C^T @ M_J])
constraint = np.vstack([D, C.T @ M_J])
c_h = null_space(constraint, rcond=1e-10)[:, 0]  # genus-1 -> 1 mode
energy = c_h @ M_J @ c_h

# 6. BEM inductance matrix (LaplaceSL with .Trace()!)
j_trial, j_test = fes_J.TnT()
with TaskManager():
    V_op = LaplaceSL(
        j_trial.Trace() * ds(label)
    ) * j_test.Trace() * ds(label)
V_A = extract_dense(V_op.mat, n_J)
V_A_proj = np.real(c_h @ V_A @ c_h)

# 7. Inductance via L/R ratio (normalization-independent)
R_sheet   = 1.0 / (sigma * thickness)
perimeter = 2 * np.pi * R_center  # or 4*side for rectangle
R_loop    = R_sheet * perimeter / trace_width
LR_ratio  = MU_0 * V_A_proj / (R_sheet * energy)
L = LR_ratio * R_loop
```

### Key Formulas

- **L/R ratio**: `L = mu_0 * V_A_proj / (R_sheet * energy) * R_loop`
  - V_A_proj = c_h^T @ V_A @ c_h (BEM projection)
  - energy = c_h^T @ M_J @ c_h (mass matrix norm)
  - R_sheet = 1/(sigma*t), R_loop = R_sheet * perimeter / trace_width
  - This ratio is independent of c_h normalization

- **Hodge decomposition**: For genus-g surface, null([D; C^T@M_J]) has dim = g.
  Ring/frame (genus-1) has exactly 1 harmonic mode.
  The harmonic mode is both div-free (D@c_h=0) and M_J-orthogonal to gradients (C^T@M_J@c_h=0).

### Multi-Turn Solenoid

For N-turn coils, combine BEM self-inductance with Neumann mutual inductance:
```python
from scipy.special import ellipk, ellipe

def neumann_mutual(R1, R2, d):
    \"\"\"Mutual inductance of coaxial circular loops (Neumann formula).\"\"\"
    k2 = 4*R1*R2 / ((R1+R2)**2 + d**2)
    K, E = ellipk(k2), ellipe(k2)
    return MU_0 * np.sqrt(R1*R2) * ((2/np.sqrt(k2) - np.sqrt(k2))*K - 2*E/np.sqrt(k2))

L_total = N * L_self + sum(2*M[i][j] for i<j)  # Neumann sum
```

### Validated Results

- Circular ring (R=10mm, w=1mm): BEM=48.64 nH, Analytical=48.78 nH (0.3% error)
- Rectangular frame (10mm, w=1mm): BEM~24 nH, FastHenry=21.6 nH, Grover~24 nH
- Computation time: ~420 ms per mesh (no bonus_intorder needed)

See: `examples/peec_integration/ngsbem_peec_demo/ngbem/1_turn_coil.py`
     `examples/peec_integration/ngsbem_peec_demo/compute_L_final.py`

### With Conductor Shield (SIBC, Standalone)

For a coil above a conducting shield plate, use ShieldBEMSIBC:

```python
from ngbem_eddy import ShieldBEMSIBC
from 1_turn_coil import (compute_loop_inductance, create_circular_ring_mesh,
                          discretize_ring_coil, create_shield_plate_mesh)

# 1. BEM air-core inductance
mesh = create_circular_ring_mesh(R, trace_width, maxh)
L_air, info = compute_loop_inductance(mesh, R, trace_width, sigma, thickness)

# 2. Coil filament model + shield plate mesh
topo_dict = discretize_ring_coil(R, N_seg=60, z=0.0)
plate_mesh = create_shield_plate_mesh(30e-3, 2e-3, gap=0.5e-3, maxh=3e-3)

# 3. SIBC solver (also supports mu_r for magnetic conductors)
shield = ShieldBEMSIBC(plate_mesh, sigma=3.7e7, mu_r=1.0)
shield.assemble(intorder=4)

# 4. Frequency sweep: Delta_Z -> L_eff, R_eff
Delta_Z = shield.compute_impedance_matrix(freq, topo_dict)
Delta_Z_total = np.sum(Delta_Z)  # single-turn: all segments in series
L_eff = L_air + np.imag(Delta_Z_total) / omega   # L decreases (Lenz)
R_eff = R_dc + np.real(Delta_Z_total)             # R increases (eddy loss)
```

**Physics:**
- SIBC surface impedance: Zs = (1+j)*sqrt(omega*mu_r*mu_0/(2*sigma))
- Eddy currents in shield oppose incident flux (Lenz's law): L_eff < L_air
- Ohmic loss in shield adds resistance: R_eff > R_dc
- Effect depends on skin depth vs plate thickness

**Limitations:**
- SIBC captures eddy current effects only (frequency-dependent shielding + loss)
- Does NOT capture DC magnetic flux enhancement (mu_r > 1 magnetostatic effect)
- For penetrable magnetic bodies, PMCHWT formulation would be needed
  (not yet available in ngsbem; see arxiv:2408.01321 for low-freq stabilized PMCHWT)

## Shield Coupling (BEM+SIBC)

Shield eddy currents are computed using the EFIE with surface impedance:

    (Zs * M_LL + jw * mu_0 * V_LL) * I_loop = -jw * b_loop

**CRITICAL SIGN CONVENTIONS (verified 2026-02-15):**

1. **V_LL sign**: MUST be **positive** (+jw*mu_0*V_LL).
   A minus sign violates Lenz's law (A_scat would reinforce A_inc).
   Diagnostic: check dot(A_scat, wire_dir) < 0.

2. **Loop basis**: Must use FACE-EDGE divergence matrix (not edge-vertex incidence).
   The LoopBasisBuilder computes null space of div operator
   to ensure div(J) = 0 in RT0 sense.

3. **Faraday sign (Delta_Z)**:
   Delta_Z[i][j] = jw * dot(A_scat_i, dir_i) * len_i
   Physical check: Im(Delta_Z) < 0 (reduced inductance)
                   Re(Delta_Z) > 0 (added resistance)

```python
from ngbem_eddy import ShieldBEMSIBC
from ngbem_interface import extract_edge_geometry

# Create shield mesh (aluminum plate)
shield_mesh = ...  # Netgen OCC Box mesh
shield = ShieldBEMSIBC(shield_mesh, sigma=3.7e7)
shield.assemble(intorder=4)

# Extract PEEC edge geometry for coupling
edge_geom = extract_edge_geometry(conductor_mesh)
topo_dict = {
    'segment_centers': edge_geom['centers'],
    'segment_directions': edge_geom['directions'],
    'segment_lengths': edge_geom['lengths'],
}

# Compute coupling at each frequency
Delta_Z = shield.compute_impedance_matrix(freq, topo_dict)
Z_shielded = Z_air + Delta_Z  # Add to PEEC branch impedance
```

## Ferrite Core Coupling (Image Method)

For planar ferrite cores, the analytical image method scales L_air directly:

```python
from ngbem_coupled import CoupledPEECMMM, compute_delta_L

mu_r = 1000
Delta_L = compute_delta_L(solver.L, mu_r)  # = L_air / (mu_r + 1)
L_total = solver.L + Delta_L * (mu_r - 1)  # = L_air * 2*mu_r/(mu_r+1)
```

**Why analytical?** BEM L_air uses Galerkin RT0 surface integrals.
Mixing with filament-based Delta_L (line integrals) produces basis mismatch.
The image method scales L_air directly, preserving matrix structure.

## Slab Impedance for Thin Conductors

Standard SIBC (Zs = (1+j)/(sigma*delta)) is valid only for delta << thickness.
For finite-thickness conductors:

    Zs_slab = Zs * coth(gamma * t)

where gamma = (1+j)/delta. Limits:
- delta << t: Zs_slab -> Zs (standard SIBC)
- delta >> t: Zs_slab -> 1/(sigma*t) (DC sheet resistance)

Available in Radia PEEC pipeline: lanczos_reduction.py, veriloga_generator.py

## Stabilized EFIE Connection (Weggler) - IMPLEMENTED

PEEC Loop-Star uses the SAME product space as Weggler's stabilized EFIE:

| Stabilized EFIE | PEEC Loop-Star | ngsbem space |
|:---|:---|:---|
| A_kappa (vector SL) | Inductance L | LaplaceSL on HDivSurface |
| V_kappa (scalar SL) | Potential P (V_0) | LaplaceSL on SurfaceL2 |
| Q_kappa (coupling) | BEM Q_0 | LaplaceSL(div, SurfaceL2) |

Key: stabilized EFIE multiplies V by kappa^2 (not divides V by kappa^2):
- Stabilized: cond = O(1) for all kappa (DC to RF)
- Classical:  cond = O(kappa^{-2}) (blows up at low frequency)

### Implementation in ngbem_peec.py (2026-02-22)

- `_build_bem_coupling()`: Assembles Q_0 via LaplaceSL product space
- `_solve_stabilized()`: Full block system with k^2*V_0
- `_solve_full_loop_star()`: Reformulated Schur with precomputed P^{-1}@M_LS
- Validated: full vs stabilized agree within 0.53% L, 0.01% R (5/5 tests PASS)

### Research Findings (Q1-Q3)

- **Q1 (k definition)**: k = omega/c_0 (free-space), NOT k^2 = -jw*mu*sigma
- **Q2 (Laplace vs Helmholtz)**: At k=0.001, ||L_Lap - L_Helm|| = 1.75e-12
  Laplace kernel works perfectly for MQS (consistent with Radia policy)
- **Q3 (Circuit extraction)**: L = mu_0*A_0, P = V_0/eps_0, R external (SIBC)
  MQS regime: k^2*V_k -> 0, system reduces to pure L+R (loop-only)

Reference: https://github.com/Weggler/docu-ngsbem/blob/main/demos/Maxwell_DtN_Stabilized.ipynb

### Product-Space vs Loop-Star (Lucy / Weggler Comparison)

Lucy (Weggler)'s product-space formulation is mathematically equivalent to
Loop-Star but automates the decomposition at the function space level:

| Aspect | Loop-Star (discrete basis) | Product-space (variational) |
|:---|:---|:---|
| Stabilization | Explicit Λ, Σ basis construction + transform | HDivSurface × SurfaceL2 separates naturally |
| κ² scaling | Manual rescaling required | Built into the formulation |
| Implementation cost | Build D, C matrices + null_space | NGSolve FES declaration only |
| Condition number | O(1) | O(1) |
| Multiply connected | Global loop detection required | Same (harmonic mode extraction needed) |

**Key insight**: The product-space approach automates Loop-Star at the function
space level. The manual D, C, M_J construction and null_space computation in
1_turn_coil.py would be replaced by a single FES declaration in Lucy's framework.
However, for genus >= 1 geometries (rings, frames), both approaches require
explicit harmonic mode handling.

### PMCHWT for Penetrable Magnetic Bodies (NOT YET IMPLEMENTED)

SIBC is a surface impedance approximation that captures eddy current effects only.
To accurately model DC permeability enhancement of magnetic bodies via BEM,
the PMCHWT (Poggio-Miller-Chang-Harrington-Wu-Tsai) formulation is required:
- Coupled EFIE + MFIE with both electric (J) and magnetic (M) surface currents
- Low-frequency stabilized version uses quasi-Helmholtz projectors for O(1)
  condition number as κ → 0
- Reference: arxiv:2408.01321 (2024)
  "Low-Frequency Stabilizations of the PMCHWT Equation"
- Not yet available in ngsbem

## Loop-Star Solver Modes (FIXED 2026-02-22)

NGBEMPEECSolver supports three modes via `solve_frequency(freqs, mode=...)`:

| Mode | System Solved | Use Case |
|------|--------------|----------|
| `'mqs'` | R + jwL (loop-only) | **Standard conductor impedance** |
| `'full'` | Reformulated Schur complement | Includes displacement current |
| `'stabilized'` | Weggler's block system | Same as full, better numerics |

### mode='mqs' (Recommended for Conductors)

Loop-only: ignores capacitive (star) unknowns. Correct for good conductors
where displacement current is negligible (sigma >> omega*epsilon).

### mode='full' (Reformulated Schur)

Uses precomputed P^{-1} @ M_LS to avoid the old `P/(jw)` blowup:
```
cap_correction = jw * M_LS^T @ P^{-1} @ M_LS
Schur = (R + jwL) - cap_correction
```
P^{-1} @ M_LS is computed once during assemble(); only the jw factor varies.

### mode='stabilized' (Weggler's BEM)

Full block system with BEM Q_0 coupling (LaplaceSL):
```
[R + jwL,        jw*mu_0*Q_0^T ] [I_loop]   [V]
[jw*mu_0*Q_0,    jw*mu_0*k^2*V_0] [rho   ] = [0]
```
Well-conditioned for all frequencies (O(1) condition number).

### Full/Stabilized vs MQS: Expected Differences

For **single conductors** (no return path), full/stabilized give L values
~3x larger than MQS. This is CORRECT physics:
- Single plate has very low self-capacitance
- Capacitive impedance 1/(jwC) >> jwL adds to total impedance
- Cap/L eigenvalue ratio ~ 470,000x (ill-scaled for single conductor)

For **multi-conductor systems** (with return paths), the difference is smaller
because mutual capacitance is larger and more physically relevant.

**Recommendation**: Use `mode='mqs'` for standard PEEC impedance extraction.
Use `mode='full'` or `mode='stabilized'` when parasitic capacitance matters.

### AVOID: Classical P/(jw) Formulation

The old formulation `Z_SS = P / (1j * omega)` causes O(kappa^{-2})
condition number blow-up at low frequency. This pattern is DEPRECATED.
Use the reformulated Schur complement or stabilized mode instead.

## FEM Cross-Verification Results

PEEC+BEM results verified by independent NGSolve FEM (A-formulation):

| Quantity | FEM | PEEC | Agreement |
|----------|-----|------|-----------|
| L_air | 96.58 nH | 100.69 nH | -4.1% |
| L_core (mu_r=1000) | 102.11 nH | 105.76 nH | -3.5% |
| Delta_L_core | +5.54 nH | +5.07 nH | 9.1% |
| L_shield (varies with freq) | 72.89-89.03 nH | 83.91-96.00 nH | 7-14% |
| Analytical L_air | 97.96 nH | -- | FEM: -1.4%, PEEC: +2.8% |

Shield effect is frequency-dependent (100 Hz - 100 kHz).
See docs/NGBEM_INTEGRATION_DESIGN.md for full frequency sweep results.

## Physical Checklist

1. L_air > 0 (positive inductance)
2. Delta_L_core > 0 (ferrite concentrates flux -> L increases)
3. Delta_L_shield < 0 (Lenz's law: eddy currents oppose flux -> L decreases)
4. R_shield > R_air (Ohmic loss in shield adds resistance)
5. dot(A_scat, wire_dir) < 0 (scattered potential opposes incident)
6. Classical EFIE cond -> infinity as kappa -> 0; stabilized stays O(1)

## FastHenry PEEC vs ngbem PEEC: When to Use Which (2026-02-22)

Verified on 100mm x 10mm x 1mm Cu bus bar (same geometry, Dowell skin effect):

### Performance Comparison

| Metric | FastHenry PEEC | ngbem PEEC | Ratio |
|--------|---------------|-----------|-------|
| Total time | 2.8 ms | 276 ms | **FastHenry 98x faster** |
| DOFs | 1 segment | 53 loop | 53x fewer |
| Assembly | 2.1 ms | 262 ms | 126x |
| Freq sweep (60 pts) | 0.7 ms | 13.6 ms | 19x |

### Dowell F_R Agreement (Skin Effect)

Both approaches correctly apply Dowell formula (F_R ratio within ~5-10%):
- 100 kHz: ngbem=2.14, FastHenry=2.25, analytical=2.36
- 1 MHz: ngbem=7.35, FastHenry=7.42, analytical=7.57

### Key Differences

| Aspect | FastHenry PEEC | ngbem PEEC |
|--------|---------------|-----------|
| Model type | 1D filament (w x h cross-section) | 2D surface mesh (triangles, RT0) |
| L vs frequency | Constant (single filament, no redistribution) | Decreases (captures current redistribution) |
| DC resistance | Exact: R = rho*L/A | Higher (current distributed across 2D mesh) |
| Skin effect | Dowell/Bessel formula OR nwinc/nhinc | BEM naturally + Dowell optional |
| Proximity effect | Via nwinc/nhinc multi-filament | Automatic (mesh-based) |
| Complex geometry | Straight segments only | Arbitrary 2D conductor shapes |
| Circuit extraction | Direct L,R,C output | Requires post-processing |

### Selection Guide

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Bus bars, straight wires | **FastHenry** | 98x faster, same accuracy |
| Circular/helical coils | **FastHenry** | Polygon approximation sufficient |
| PCB traces (straight) | **FastHenry** | Fast, multi-filament for proximity |
| L-shaped / T-shaped conductors | **ngbem** | 2D current redistribution matters |
| Spiral inductors (2D) | **ngbem** | Complex geometry |
| Quick estimation | **FastHenry** | Always start here |
| Precision analysis | **ngbem** | After FastHenry confirms baseline |

### Practical Workflow

1. **First pass**: FastHenry for fast L,R estimation (ms-scale)
2. **If needed**: ngbem for precision (current redistribution, complex geometry)
3. **Dowell/Bessel**: Both support Zs_func callback for skin effect
4. **Shield/core coupling**: Both integrate with ShieldBEMSIBC and CoupledPEECSolver
"""

RADIA_EFIE_PRECONDITIONER = """
# EFIE Calderon Preconditioner (Andriulli / Schoeberl)

Calderon-type preconditioner for the Electric Field Integral Equation (EFIE),
based on preconditioning the single layer (SL) operator by the rotated SL
within the dual sequence. Implemented by Joachim Schoeberl in ngbem.

Reference: S.B. Adrian, A. Dély, D. Consoli, A. Merlini, F.P. Andriulli,
"Electromagnetic Integral Equations: Insights in Conditioning and Preconditioning",
IEEE Open Journal of Antennas and Propagation, Vol.2, pp.1143-1174, 2021.
DOI: 10.1109/OJAP.2021.3121097

## Problem: EFIE Conditioning

The standard EFIE discretization on HDivSurface produces an ill-conditioned system:

    lhs = (j*kappa) * V1 + 1/(j*kappa) * V2

where V1 = HelmholtzSL on HDivSurface, V2 = HelmholtzSL on div(HDivSurface).
Without preconditioning, GMRES converges slowly or stagnates.

## Preconditioner Formula

The preconditioner applies the rotated SL operator:

    pre = M^{-1} @ (kappa * V_rot - 1/kappa * nabla_s @ M_H1^{-1} @ V_pot @ M_H1^{-1} @ nabla_s^T) @ M^{-1}

where:
- M^{-1}: HDivSurface mass matrix inverse (sparsecholesky)
- V_rot: HelmholtzSL applied to n x u (rotated trial/test functions)
- V_pot: HelmholtzSL on scalar H1 space (potential part)
- M_H1^{-1}: H1 mass matrix inverse (sparsecholesky)
- nabla_s: Surface curl operator (Cross(grad(upot).Trace(), n))

## Spaces Required

| Space | Order | Purpose |
|-------|-------|---------|
| HDivSurface | p (e.g. 3) | EFIE unknowns (surface current) |
| H1 | p+1 (e.g. 4) | Potential part of preconditioner |

Both spaces must be complex=True for electromagnetic problems.

## Complete Working Example (from Schoeberl's EMpre.ipynb)

```python
from ngsolve import *
from netgen.occ import *
from ngsolve.bem import *
from time import time

# --- Mesh ---
face = Glue(Sphere((0,0,0),1).faces)
mesh = Mesh(OCCGeometry(face).GenerateMesh(maxh=0.2)).Curve(4)

# --- EFIE setup ---
kappa = 3*pi
d = CF((0,-kappa,0))
E_inc = exp(1j*d*CF((x,y,z))) * CF((1,0,0))

fes = HDivSurface(mesh, order=3, complex=True)
u, v = fes.TnT()

fespot = H1(mesh, order=4, complex=True)
upot, vpot = fespot.TnT()

# --- EFIE operator assembly ---
with TaskManager():
    V1 = HelmholtzSL(u.Trace()*ds(bonus_intorder=4), kappa) \\
         * v.Trace()*ds(bonus_intorder=4)
    V2 = HelmholtzSL(div(u.Trace())*ds(bonus_intorder=4), kappa) \\
         * div(v.Trace())*ds(bonus_intorder=4)

lhs = (1j*kappa) * V1.mat + 1/(1j*kappa) * V2.mat
rhs = LinearForm(E_inc*v.Trace()*ds(bonus_intorder=3)).Assemble()

# --- Preconditioner assembly ---
invMHd = BilinearForm(u.Trace()*v.Trace()*ds).Assemble() \\
         .mat.Inverse(inverse="sparsecholesky")
n = specialcf.normal(3)

with TaskManager():
    Vrot = HelmholtzSL(Cross(u.Trace(),n)*ds(bonus_intorder=2), kappa) \\
           * Cross(v.Trace(),n)*ds(bonus_intorder=2)
    Vpot = HelmholtzSL(upot*ds(bonus_intorder=2), kappa) \\
           * vpot*ds(bonus_intorder=2)

surfcurl = BilinearForm(Cross(grad(upot).Trace(), n) \\
           * v.Trace()*ds).Assemble().mat
invMH1 = BilinearForm(upot*vpot*ds).Assemble() \\
         .mat.Inverse(inverse="sparsecholesky")

pre = invMHd @ (kappa*Vrot.mat \\
      - 1/kappa*surfcurl@invMH1@Vpot.mat@invMH1@surfcurl.T) @ invMHd

# --- Solve with GMRES ---
gfj = GridFunction(fes)
with TaskManager():
    gfj.vec[:] = solvers.GMRes(A=lhs, b=rhs.vec, pre=pre,
                                maxsteps=500, tol=1e-8)
```

## Performance (Sphere, maxh=0.2, order=3, kappa=3*pi)

| Metric | Value |
|--------|-------|
| HDivSurface ndof | 10,108 |
| H1 ndof | 5,778 |
| EFIE assembly | 32.3 s |
| Preconditioner assembly | 15.5 s |
| GMRES iterations | **26** |
| GMRES time | 69.1 s |
| Final residual | 8.2e-9 |

## Key Points

1. **HDivSurface only**: Works with surface H(div) discretization (not HCurl)
2. **Small kappa regime**: Particularly effective for low-frequency / MQS
3. **.Trace() required**: All BEM operators on HDivSurface need .Trace()
4. **bonus_intorder**: Use 4 for EFIE operators, 2-3 for preconditioner
5. **Operator composition**: NGSolve's @ operator chains BEM + sparse operators
6. **Two BEM assemblies**: One for EFIE (V1, V2), one for preconditioner (Vrot, Vpot)

## Connection to PEEC / Low-Frequency Stabilization

This preconditioner addresses the same low-frequency ill-conditioning as
Weggler's stabilized EFIE (see ngbem_peec topic). Both target the O(kappa^{-2})
condition number blow-up:

| Approach | Mechanism | Use Case |
|----------|-----------|----------|
| Weggler stabilized EFIE | Product-space reformulation | PEEC impedance extraction |
| Calderon preconditioner | Operator preconditioning via rotated SL | Full-wave EM scattering |

For pure MQS (kappa -> 0), both achieve O(1) condition number.
The Calderon preconditioner is more general (works for arbitrary kappa)
while Weggler's approach integrates directly with PEEC circuit extraction.

## Source

EMpre.ipynb by Joachim Schoeberl (2026-02). Shared for ngbem integration.
"""

RADIA_FEM_VERIFICATION = """
# NGSolve FEM Verification Reference

NGSolve FEM was used to verify PEEC+BEM results for a circular coil with
ferrite core and aluminum shield. Full results in `docs/NGBEM_INTEGRATION_DESIGN.md`.

## Summary: ALL 6 CHECKS PASS

| Check | Result |
|-------|--------|
| L_air vs analytical | -1.4% (PASS, <5%) |
| L_air FEM vs PEEC | -4.1% (PASS, <5%) |
| Delta_L_core > 0 | +5.54 nH (PASS) |
| Delta_L_core FEM vs PEEC | 9.1% (PASS, <15%) |
| Shield decreases L | All frequencies (PASS) |
| Shield DeltaL trend | Matches (PASS) |

## Key FEM Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| FEM order | 2 | HCurl, nograds=True |
| air_r | 120 mm (static), 60 mm (eddy) | Sphere with Dirichlet BC |
| maxh | 8 mm (static), 4 mm (eddy) | Air mesh |
| core.faces.maxh | 2 mm | Local refinement only |
| Solver | PARDISO | NGSolve interface to Intel MKL |

## PARDISO (NGSolve Feature)

PARDISO is Intel MKL's multi-threaded direct sparse solver. It is accessed
through NGSolve's inverse interface, NOT implemented in Radia.

```python
# NGSolve usage:
gfA.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="pardiso") * f.vec
```

Speedup vs UMFPACK: 3.9-7.7x (multi-threaded vs single-threaded).
"""

RADIA_SCALAR_POTENTIAL = """
# Phi-Reduced Scalar Potential (Radia + NGSolve)

## Method: Simkin-Trowbridge (1979)

The phi-reduced formulation splits the magnetic field:

    H = H_s - grad(phi)

where H_s is the source field (permanent magnets or coils) computed by Radia,
and phi is the correction potential solved by NGSolve FEM to account for iron.

This is ideal when:
- The source field (magnets, coils) is easy to compute analytically (Radia)
- Iron regions need FEM for their nonlinear/complex geometry response
- Open boundary is needed (Radia handles it naturally)

## ScalarPotentialSolver API

```python
from radia.scalar_potential_solver import ScalarPotentialSolver

solver = ScalarPotentialSolver(mesh, iron_domains='iron', mu_r=1000, order=2)

# Source from Radia object (voxel interpolation)
solver.set_source_from_radia(radia_obj, resolution=31)

# Or from callback
solver.set_source_from_callback(lambda x,y,z: (Hx, Hy, Hz), resolution=31)

# Or from CoefficientFunction directly
solver.set_source_cf(H_source_cf)

# Solve
solver.solve(method='auto')  # 'single' if mu_r<5000, 'two' otherwise

# Results
B_cf = solver.get_B()        # CoefficientFunction (Tesla)
H_cf = solver.get_H()        # CoefficientFunction (A/m)
B_hdiv = solver.project_to_hdiv()  # HDiv GridFunction (div(B)=0)
```

## Coil Modeling via Equivalent Magnetization

A solenoid with N turns, current I, height h produces the same external
field as a uniformly magnetized body with M_z = N*I/h (A/m).

For a hollow rectangular coil (bore = inner hole, outer = winding OD):
```python
M_z = N * I / h  # A/m
a_in, a_out = bore/2, outer/2

# 4 wall blocks forming the hollow rectangle
left  = rad.ObjRecMag([-(a_in+a_out)/2, 0, 0], [a_out-a_in, outer, h], [0,0,M_z])
right = rad.ObjRecMag([ (a_in+a_out)/2, 0, 0], [a_out-a_in, outer, h], [0,0,M_z])
front = rad.ObjRecMag([0,  (a_in+a_out)/2, 0], [bore, a_out-a_in, h], [0,0,M_z])
back  = rad.ObjRecMag([0, -(a_in+a_out)/2, 0], [bore, a_out-a_in, h], [0,0,M_z])
coil = rad.ObjCnt([left, right, front, back])
```

## Solver Method Selection

| mu_r Range | Method | Why |
|------------|--------|-----|
| < 5000 | `single` (reduced potential) | Simple, fast, adequate accuracy |
| >= 5000 | `two` (Simkin-Trowbridge) | Avoids cancellation in high-mu iron |

## Nonlinear Material (Newton + SymbolicEnergy)

For nonlinear B-H curves, use NGSolve's SymbolicEnergy with Newton iteration
and energy-based line search. This is MUCH better than Picard iteration
(fixed-point mu update): Newton gives quadratic convergence vs linear.

**Key difference from A-formulation**: In scalar potential, H is the primary
variable (H = H_s - grad(phi)). The energy density uses B(H), not H(B).

```python
from ngsolve import BSpline
import pandas as pd

# Load B-H data (column 0 = H in A/m, column 1 = B in Tesla)
df = pd.read_csv('BH.txt', sep='\\t')
H_data = list(df.iloc[:, 0])
B_data = list(df.iloc[:, 1])

# B as function of H (for scalar potential formulation)
bh_direct = BSpline(2, [0] + H_data, B_data)

# Energy density: w(H) = integral_0^H B(H') dH'
w_H = bh_direct.Integrate()

# Compare with A-formulation (where H(B) is used):
# bh_curve = BSpline(2, [0] + B_data, H_data)  # H(B)
# energy_dens = bh_curve.Integrate()             # w*(B) = integral H(B')dB'
```

### Formulation: Energy Minimization

The total magnetic energy functional for the Simkin formulation:

```
E(phi) = integral w(|H_s - grad(phi)|) dx  [iron, nonlinear]
       + integral (mu_0/2)|H_s - grad(phi)|^2 dx  [air, linear]
       + integral (mu_0/2)*kelvin_weight*|H_s - grad(phi)|^2 dx  [kelvin]
```

Note: H_s (source field from Radia coil) is embedded in the energy.
No separate LinearForm needed.

```python
from radia.scalar_potential_solver import ScalarPotentialSolver
from ngsolve import *

mu0 = 4e-7 * 3.14159265

solver = ScalarPotentialSolver(
    mesh, iron_domains='iron', order=2,
    kelvin_region='kelvin', kelvin_radius=AIR_R,
    kelvin_center=SPHERE_CENTER)
solver.set_source_from_radia(coil, resolution=51)

# Build SymbolicEnergy form
H_s = solver._H_source_cf  # VoxelCoefficient from Radia
fes = H1(mesh, order=2, dirichlet='outer')
phi, v = fes.TnT()

H_trial = H_s - grad(phi)
H2 = InnerProduct(H_trial, H_trial)

a = BilinearForm(fes, symmetric=True)
# Air: linear energy
a += SymbolicEnergy(mu0/2 * H2, definedon=mesh.Materials("air"))
# Iron: nonlinear energy from B-H curve
a += SymbolicEnergy(w_H(sqrt(H2 + 1e-12)),
                    definedon=mesh.Materials("iron"))
# Kelvin: linear with weight
if solver._kelvin_region:
    R = solver._kelvin_radius
    cx, cy, cz = solver._kelvin_center
    r_sq = (x-cx)**2 + (y-cy)**2 + (z-cz)**2 + 1e-30
    kelvin_w = R**2 / r_sq
    a += SymbolicEnergy(mu0/2 * kelvin_w * H2,
                        definedon=mesh.Materials("kelvin"))

# Regularization (optional, small)
a += SymbolicBFI(1e-8 * phi * v)

c = Preconditioner(a, type="bddc", inverse="sparsecholesky")
```

### Newton + Energy Line Search

```python
sol = GridFunction(fes)
sol.vec[:] = 0

au = sol.vec.CreateVector()
r = sol.vec.CreateVector()
w = sol.vec.CreateVector()
sol_new = sol.vec.CreateVector()

# No source LinearForm needed (H_s embedded in energy)
with TaskManager():
    for it in range(50):
        E0 = a.Energy(sol.vec)
        a.AssembleLinearization(sol.vec)
        a.Apply(sol.vec, au)
        r.data = -au  # residual = 0 - au (no source term)

        inv = CGSolver(mat=a.mat, pre=c.mat)
        w.data = inv * r

        err = InnerProduct(w, r)
        print(f"Newton {it}: err = {err:.2e}")
        if abs(err) < 1e-4:
            break

        # Energy line search
        sol_new.data = sol.vec + w
        E = a.Energy(sol_new)
        tau = 1
        while E > E0:
            tau *= 0.5
            sol_new.data = sol.vec + tau * w
            E = a.Energy(sol_new)

        sol.vec.data = sol_new

# Post-process
H_cf = H_s - grad(sol)
B_cf = mu0 * H_cf  # air approximation; use B(H) for iron
```

### Comparison: Newton vs Picard

| Feature | Newton + SymbolicEnergy | Picard (mu update) |
|---------|------------------------|--------------------|
| Convergence | Quadratic (~5-10 iter) | Linear (~20-50 iter) |
| Line search | Energy-based (guaranteed) | Under-relaxation (manual) |
| Jacobian | Exact (auto-differentiated) | Approximate (secant slope) |
| Remanence | Via energy functional | Needs polarization method |
| Implementation | SymbolicEnergy + BSpline | Manual mu_gf update loop |

**IMPORTANT**: For the scalar potential formulation, use `B(H)` BSpline
(not `H(B)`) because H is the primary variable. For the A-formulation,
use `H(B)` BSpline because B = curl(A) is the primary variable.

### Multi-Level Current Sweep

For sweeping multiple current levels (1000 AT to 20000 AT), reuse the
converged solution as initial guess for the next level:

```python
for AT in range(1000, 21000, 1000):
    coil = build_radia_coil(AT)
    solver.set_source_from_radia(coil, resolution=51)
    # ... rebuild a with new H_s ...
    # sol.vec keeps previous converged state -> fast convergence
    # Newton iteration (typically 3-5 iterations after first level)
```

## Examples

- `examples/NGSolve_Integration/demo_ctype_simkin.py` - Linear Simkin + Kelvin
- `examples/NGSolve_Integration/demo_nonlinear_simkin.py` - B-H curve Picard
- `examples/NGSolve_Integration/demo_hysteresis_simkin.py` - Energy hysteresis

## Reference

J. Simkin and C. W. Trowbridge, "On the use of the total scalar potential
in the numerical solution of field problems in electromagnetics,"
Int. J. Numer. Methods Eng., vol. 14, pp. 423-440, 1979.
"""

RADIA_PLAY_MODELS = """
# Play Models: Typical MMM/MSC Usage Patterns

Radia uses two integral methods depending on element type:

| Method | Elements | DOF/elem | Description |
|--------|----------|----------|-------------|
| **MMM** | Tetrahedron (4 vtx) | 3 (Mx,My,Mz) | Volume magnetization |
| **MSC** | Hexahedron (8 vtx) | 6 (sigma/face) | Surface charge on faces |
| **MSC** | Wedge (6 vtx) | 5 (sigma/face) | Transition elements |
| **MMM** | ObjRecMag (center+dims) | 3 | Optimized rectangular block |

Mixed meshes (hex+tet+wedge) are fully supported by all solvers.

---

## Pattern A: Permanent Magnet Only (No Solve)

Fixed magnetization -- no iterative solve needed.  Fastest pattern.

```python
import radia as rad
rad.UtiDelAll()

# Rectangular PM: 20x20x10 mm, Br=1.2T in Z
# M = Br / mu_0 = 1.2 / (4*pi*1e-7) = 954930 A/m
mag = rad.ObjRecMag([0, 0, 0], [0.02, 0.02, 0.01], [0, 0, 954930])

# Or use ObjHexahedron with 8 vertices for arbitrary shapes
s = 0.01  # half-size in meters
verts = [[-s,-s,-s],[s,-s,-s],[s,s,-s],[-s,s,-s],
         [-s,-s,s],[s,-s,s],[s,s,s],[-s,s,s]]
mag2 = rad.ObjHexahedron(verts, [0, 0, 954930])

B = rad.Fld(mag, 'b', [0, 0, 0.03])  # No Solve() needed!
rad.UtiDelAll()
```

**Example**: `examples/simple_problems/cubic_polyhedron_magnet.py`

---

## Pattern B: PM + Soft Iron (Linear)

Iron acquires induced M from PM stray field.  Requires Solve().

```python
import radia as rad
import numpy as np
rad.UtiDelAll()

# Permanent magnet
pm = rad.ObjRecMag([0, 0, 0], [0.02, 0.02, 0.01], [0, 0, 954930])

# Iron pole piece (zero initial M)
iron = rad.ObjRecMag([0, 0, 0.015], [0.03, 0.03, 0.01], [0, 0, 0])
mat = rad.MatLin(1000)  # mu_r = 1000
rad.MatApl(iron, mat)

assembly = rad.ObjCnt([pm, iron])
result = rad.Solve(assembly, 0.0001, 1000, 0)  # LU solver
print(f"Converged: max|dM|={result[3]:.2e}")

B = rad.Fld(assembly, 'b', [0, 0, 0.03])
rad.UtiDelAll()
```

**Example**: `examples/c_type_electromagnet/mu=1000/full/verify_elf_radia.py`

---

## Pattern C: Iron in Background Field

Soft iron in an externally applied field.  Classic magnetization problem.

```python
import radia as rad
import numpy as np
rad.UtiDelAll()

MU_0 = 4 * np.pi * 1e-7

# 3x3x3 hex mesh for a 20mm iron cube
n = 3; dx = 0.02 / n; offset = 0.01
objs = []
base = [[0,0,0],[1,0,0],[1,1,0],[0,1,0],
        [0,0,1],[1,0,1],[1,1,1],[0,1,1]]
for iz in range(n):
    for iy in range(n):
        for ix in range(n):
            x0, y0, z0 = ix*dx - offset, iy*dx - offset, iz*dx - offset
            v = [[c[0]*dx+x0, c[1]*dx+y0, c[2]*dx+z0] for c in base]
            objs.append(rad.ObjHexahedron(v, [0,0,0]))

iron = rad.ObjCnt(objs)
rad.MatApl(iron, rad.MatLin(1000))

# IMPORTANT: ObjBckg requires a CALLABLE, not a list!
bkg = rad.ObjBckg(lambda p: [0, 0, MU_0 * 200000])  # ~0.25 T
grp = rad.ObjCnt([iron, bkg])

result = rad.Solve(grp, 0.001, 100, 0)  # 27 hex, LU is fine
B = rad.Fld(grp, 'b', [0, 0, 0.02])
rad.UtiDelAll()
```

**Element count**: 27 hex = 27 * 6 = 162 DOF (MSC)
**Example**: `examples/cube_uniform_field/test_objm_minimal.py`

---

## Pattern D: Nonlinear Iron (B-H Curve)

Saturable iron with tabulated or functional B-H data.

```python
import radia as rad
rad.UtiDelAll()

# Tabulated B-H curve: [[H (A/m), B (T)], ...]
BH = [[0,0], [100,0.1], [500,0.8], [1000,1.2],
      [5000,1.6], [20000,1.9], [50000,2.0]]
mat_nl = rad.MatSatIsoTab(BH)

# Or functional form: MatSatIsoFrm
# mat_nl = rad.MatSatIsoFrm([ksi1, ms1], [ksi2, ms2], [ksi3, ms3])

iron = rad.ObjRecMag([0, 0, 0], [0.02, 0.02, 0.02], [0, 0, 0])
rad.MatApl(iron, mat_nl)

bkg = rad.ObjBckg(lambda p: [0, 0, 0.5])  # 0.5 T
grp = rad.ObjCnt([iron, bkg])

# Nonlinear: may need more iterations + under-relaxation
rad.SolverConfig(relax_param=0.3)  # 30% damping
result = rad.Solve(grp, 0.0001, 500, 0)
rad.SolverConfig(relax_param=0.0)  # reset
rad.UtiDelAll()
```

**Example**: `examples/background_fields/sphere_in_quadrupole.py`

---

## Pattern E: Mixed Element Types (Hex + Tet)

Use netgen_mesh_to_radia() or gmsh_to_radia() for complex geometries.

```python
import radia as rad
from radia.netgen_mesh_import import netgen_mesh_to_radia

rad.UtiDelAll()

# Import NGSolve mesh -> Radia (auto-creates hex/tet/wedge elements)
container = netgen_mesh_to_radia(
    mesh,
    material={'magnetization': [0, 0, 0]},  # or callable per element
    units='m'
)

# Apply material
rad.MatApl(container, rad.MatLin(1000))

bkg = rad.ObjBckg(lambda p: [0, 0, 0.1])
grp = rad.ObjCnt([container, bkg])
result = rad.Solve(grp, 0.001, 100, 1)  # BiCGSTAB for medium size
rad.UtiDelAll()
```

**DOF**: Mixed -- each hex has 6 DOF (MSC), each tet has 3 DOF (MMM).
**Example**: `examples/NGSolve_Integration/mesh_magnetization_import/`

---

## Pattern F: Large-Scale with HACApK

For N > 2000 elements, use H-matrix acceleration (method=2).

```python
import radia as rad
rad.UtiDelAll()

# ... create large hex mesh (e.g., 10x10x10 = 1000 elements) ...

rad.MatApl(iron, rad.MatLin(1000))
bkg = rad.ObjBckg(lambda p: [0, 0, 0.1])
grp = rad.ObjCnt([iron, bkg])

# Configure HACApK parameters BEFORE Solve
rad.SolverConfig(hacapk_eps=1e-4, hacapk_leaf=10, hacapk_eta=2.0)

result = rad.Solve(grp, 0.001, 100, 2)  # method=2 = HACApK

# Batch field evaluation (unified Fld with batch points)
import numpy as np
pts = np.array([[x, 0, 0] for x in np.linspace(-0.1, 0.1, 100)])
B = np.asarray(rad.Fld(grp, 'b', pts))  # shape (100, 3)
rad.UtiDelAll()
```

**Solver selection summary**:
- N < 500: method=0 (LU) -- direct, guaranteed
- 500 < N < 2000: method=1 (BiCGSTAB) -- fastest general
- N > 2000: method=2 (HACApK) -- O(N log N) memory

**Example**: `examples/cube_uniform_field/hexahedron/benchmark_hex.py`
"""


RADIA_HYSTERESIS = """
# Magnetic Hysteresis: B-input Play Model + Energy-Based Formulation

Radia supports **vector magnetic hysteresis** via an energy-based formulation
(Francois-Lavet / Egger et al.) that is thermodynamically consistent and
computationally efficient. The B-input Play model data (measured B-H loops,
JMAG .hys files, MATLAB .mat files) is converted to energy-based parameters
for the C++ solver.

---

## Overview: Why Energy-Based, Not Direct Play?

| Feature | B-input Play (Matsuo) | Energy-based (Egger) |
|---------|----------------------|---------------------|
| Thermodynamic consistency | Approximate | **Exact** |
| Iron loss | Loop area (approximate) | **Local energy dissipation** |
| Inverse operator (H -> B) | fminsearch O(100K) | **Schur complement O(K)** |
| Congruency | **H-axis congruent** (see below) | **Structurally guaranteed** |
| Vector extension | 2D -> 3D natural | **Arbitrary dimension** |

### Congruency Direction (合同性の方向)

B-input Play model operates in **B-space** (thresholds eta_k in B).
For minor loops with the same B-amplitude at different DC bias:
- The Play operator state changes are identical (same delta-B -> same delta-p_k)
- Therefore the **H output is congruent** (same shape regardless of DC bias)
- This is **H-axis congruency** (H軸方向の合同性)

| Model | Input | Output | Congruency |
|-------|-------|--------|------------|
| H-input Play | H | B | Not congruent (non-physical) |
| **B-input Play** | **B** | **H** | **H-axis congruent** |
| Energy-based | H <-> B | both | Structurally guaranteed |

Radia's solver computes H, then needs B = f(H). The B-input Play model requires
solving an inverse problem (B -> H is the natural direction). Egger's Schur
complement trick makes the inverse operator O(K) -- same cost as the forward
operator.

---

## Data Pipeline

```
Measured B-H loops
  |
  v
.hys file (JMAG)  or  .mat file (MATLAB/Potter-Schmulian)
  |
  v
hysteresis_io.load_hys() / load_mat()    -> list of {B, H, Bmax} loops
  |
  v
hysteresis_io.build_shape_functions()     -> eta (thresholds), f_k (shape funcs)
  |
  v
hysteresis_io.convert_play_to_energy()    -> K, As, Js, chi
  |
  v
rad.MatEnergyHysteresis(K, As, Js, chi, eps)   -> material handle
  |
  v
rad.MatApl(iron_element, mat_handle)
rad.Solve(container, tol, maxiter, method)
```

---

## API Reference

### rad.MatEnergyHysteresis(K, As, Js, chi, eps=1e-8)

Create an energy-based vector hysteresis material.

**Parameters:**

| Parameter | Type | Unit | Description |
|-----------|------|------|-------------|
| K | int | - | Number of partial polarizations (play operators) |
| As | array(K) | A/m | Saturation slope A_{s,k} for each partial polarization |
| Js | array(K) | T | Saturation polarization J_{s,k} for each partial polarization |
| chi | array(K) | A/m | Pinning strength chi_k (= Play threshold eta_k) |
| eps | float | - | Regularization parameter (default 1e-8) |

**Returns:** Material handle (int)

**Internal energy density per partial polarization:**
```
U_k(J) = -(2 * A_{s,k} * J_{s,k}) / pi * log(cos(pi/2 * J / J_{s,k}))
```

### rad.MatMvsH(mat, component, H)

Evaluate magnetization M at given H field (updates internal hysteresis state).

```python
M = rad.MatMvsH(mat_handle, 'm', [Hx, Hy, Hz])
# Returns [Mx, My, Mz] in A/m
```

---

## Usage Patterns

### Pattern 1: Direct Parameter Specification

For known energy-based parameters (e.g., from literature or fitting):

```python
import radia as rad
import numpy as np

rad.UtiDelAll()

K = 10
As = np.full(K, 5000.0)       # Saturation slope [A/m]
Js = np.full(K, 0.2)          # Saturation polarization [T]
chi = np.linspace(0, 300, K)  # Pinning strengths [A/m]
eps = 1e-8

mat = rad.MatEnergyHysteresis(K, As, Js, chi, eps)

# Apply to iron element
iron = rad.ObjRecMag([0, 0, 0], [0.01, 0.01, 0.01], [0, 0, 0])
rad.MatApl(iron, mat)

# Apply background field and solve
bkg = rad.ObjBckg(lambda p: [0, 0, 0.1])  # 0.1 T
container = rad.ObjCnt([iron, bkg])
result = rad.Solve(container, 0.001, 100, 1)

B = rad.Fld(container, 'b', [0.02, 0, 0])
rad.UtiDelAll()
```

### Pattern 2: From JMAG .hys File (One-Step)

```python
import radia as rad
from radia.hysteresis_io import hys_to_radia

rad.UtiDelAll()

# One-step: .hys -> energy-based parameters
params = hys_to_radia('material.hys', K=20, eps=1e-8)
# params = {'K': 20, 'As': array, 'Js': array, 'chi': array, 'eps': 1e-8}

mat = rad.MatEnergyHysteresis(
    params['K'], params['As'], params['Js'], params['chi'], params['eps']
)

iron = rad.ObjRecMag([0, 0, 0], [0.01, 0.01, 0.01], [0, 0, 0])
rad.MatApl(iron, mat)
# ... solve and evaluate fields ...
rad.UtiDelAll()
```

### Pattern 3: From MATLAB .mat File (Potter-Schmulian Format)

```python
from radia.hysteresis_io import mat_to_radia

params = mat_to_radia('B_input.mat', eps=1e-8)
mat = rad.MatEnergyHysteresis(
    params['K'], params['As'], params['Js'], params['chi'], params['eps']
)
```

### Pattern 4: Step-by-Step (Custom Processing)

```python
from radia.hysteresis_io import load_hys, build_shape_functions, convert_play_to_energy

# Step 1: Load B-H loop data
loops = load_hys('material.hys')
# loops = [{'B': array, 'H': array, 'Bmax': float}, ...]

# Step 2: Build Play shape functions
eta, f_k_tables, Bplay = build_shape_functions(loops)
# eta = thresholds in B-space
# f_k_tables = [(r_values, f_values), ...] per operator

# Step 3: Convert to energy-based parameters
energy_params = convert_play_to_energy(eta, f_k_tables)
# energy_params = {'K': int, 'As': array, 'Js': array, 'chi': array}

# Step 4: Create Radia material
mat = rad.MatEnergyHysteresis(
    energy_params['K'], energy_params['As'],
    energy_params['Js'], energy_params['chi'], 1e-8
)
```

### Pattern 5: B-H Loop Generation (Material Characterization)

Generate a B-H hysteresis loop to verify material behavior:

```python
import radia as rad
import numpy as np

MU_0 = 4e-7 * np.pi

rad.UtiDelAll()

K = 10
As = np.full(K, 5000.0)
Js = np.full(K, 0.2)
chi = np.linspace(0, 300, K)
mat = rad.MatEnergyHysteresis(K, As, Js, chi, 1e-8)

# Drive with sinusoidal H
Hmax = 1000.0
n_steps = 200
t = np.linspace(0, 2 * np.pi, n_steps)
H_drive = Hmax * np.sin(t)

B_values = np.zeros(n_steps)
for i, H_val in enumerate(H_drive):
    M = rad.MatMvsH(mat, 'm', [H_val, 0, 0])
    B_values[i] = MU_0 * (H_val + M[0])

# B_values vs H_drive shows hysteresis loop
# Ascending branch != descending branch (remanence, coercivity visible)
```

---

## hysteresis_io Module Reference

Location: `src/radia/hysteresis_io.py`

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `load_hys(filepath)` | .hys file path | list of {B, H, Bmax} | JMAG .hys reader |
| `load_mat(filepath)` | .mat file path | loops, dB, BMax | MATLAB .mat reader (Potter-Schmulian) |
| `build_shape_functions(loops, dB)` | B-H loops | eta, f_k_tables, Bplay | ShapeFunction.m port |
| `play_hysteron(f_k, Bx, By, eta, px, py)` | shape funcs + B | Hx, Hy, px, py | PlayHysteron.m port (verification) |
| `convert_play_to_energy(eta, f_k_tables)` | Play params | {K, As, Js, chi} | Play -> energy conversion |
| `hys_to_radia(filepath, K, eps)` | .hys path | {K, As, Js, chi, eps} | One-step .hys -> Radia |
| `mat_to_radia(filepath, eps)` | .mat path | {K, As, Js, chi, eps} | One-step .mat -> Radia |

### .hys File Format (JMAG)

```
Jiles Atherton                    <- model type (ignored)
0  200  5                         <- 0  nx(points/loop)  ny(num loops)
1  200  0                         <- flags (ignored)
tesla;A/m                         <- units: "tesla;A/m" or "A/m;tesla"
1.200000  100.000000              <- B  H  (or H  B depending on units)
1.195000  95.000000
...                               <- nx * ny rows
```

### .mat File Format (Potter-Schmulian)

MATLAB .mat file with variables:
- `BH`: struct array, each with `.B` and `.H` fields (descending branch)
- `dB`: B step size (scalar)
- `BMax`: array of Bmax values per loop

---

## Mathematical Background

### Energy-Based Model (Francois-Lavet / Egger)

**Forward operator** (H -> B):
```
B = mu_0 * H + sum_k J_k
J_k = argmin_J [ U_k(J) - <H, J> + chi_k * |J - J_{k,prev}|_eps ]
```
Each J_k solved independently via Newton (2nd order convergence, 3-5 iterations).

**Inverse operator** (B -> H) -- used by Radia solver:
```
H = nu_0 * (B - sum_k J_k)
{J_k} = argmin [ (nu_0/2)|B - sum_k J_k|^2 + sum_k [U_k(J_k) + chi_k|J_k - J_{k,prev}|_eps] ]
```
Schur complement trick reduces coupled K-body problem to O(K).

### Relationship: Play Model <-> Energy Model

- Play threshold eta_k corresponds to pinning strength chi_k
- Shape function f_k(|p|) corresponds to energy derivative U_k'(J)
- Shape functions from `build_shape_functions()` are integrated to obtain U_k

### Parameter Guidelines

| Parameter | Typical Range | Notes |
|-----------|--------------|-------|
| K | 5 - 50 | More = finer hysteresis resolution. K=10-20 typical |
| As | 1000 - 50000 A/m | Controls initial susceptibility |
| Js | 0.05 - 2.0 T | Saturation per partial polarization. sum(Js) ~ total Js |
| chi | 0 - 1000 A/m | chi[0]=0 (reversible), increasing for irreversible |
| eps | 1e-8 - 1e-6 | Regularization. Smaller = sharper corners |

---

## Common Mistakes

1. **Confusing M and J**: `M` is in A/m, `J = mu_0 * M` is in Tesla. Radia uses M (A/m).
2. **Forgetting state is cumulative**: `MatMvsH()` updates internal hysteresis state.
   Each call advances the magnetization history. Call order matters.
3. **Using MatLin for hysteretic materials**: `MatLin(mu_r)` is for linear (non-hysteretic)
   soft iron. Use `MatEnergyHysteresis()` for hysteresis.
4. **Wrong K value**: Too few operators (K<5) gives poor loop shape. Too many (K>50)
   adds cost with diminishing returns. K=10-20 is the sweet spot.

---

## Verification

Script: `examples/hysteresis/verify_cpp_hysteresis.py`

Tests:
1. Forward operator sanity (B output range, chi effective, direction alignment)
2. B-H loop generation (ascending != descending, hysteresis width > 0.001 T)
3. Solver integration (MatApl + Solve on ObjRecMag in background field)
4. Performance (K=50 evaluation timing)

---

## Applications

### Magnetization Analysis (着磁解析)

The energy-based hysteresis model enables **magnetization process simulation**:

```python
import radia as rad
import numpy as np

rad.UtiDelAll()

# 1. Create unmagnetized PM element with hysteresis material
pm = rad.ObjRecMag([0, 0, 0], [0.02, 0.02, 0.01], [0, 0, 0])  # M=0 initially
mat = rad.MatEnergyHysteresis(K, As, Js, chi, eps)
rad.MatApl(pm, mat)

# 2. Apply strong magnetizing field (着磁パルス)
bkg = rad.ObjBckg(lambda p: [0, 0, 2.0])  # 2T magnetizing field
container = rad.ObjCnt([pm, bkg])
rad.Solve(container, 0.001, 100, 1)  # J_k states updated

# 3. Remove magnetizing field -> residual magnetization remains
# (requires re-creating container with zero background)
# The hysteresis material retains memory via pinning (chi_k > 0)
```

**Key insight**: With `MatLin(mu_r)`, removing the external field returns M to zero.
With `MatEnergyHysteresis`, **residual magnetization persists** due to pinning --
this is exactly the physics of magnetization.

**Use cases**:
- Multi-pole magnetization pattern analysis (着磁パターン)
- Incomplete magnetization in weak-field regions (不完全着磁)
- Demagnetization under reverse field or high temperature (減磁解析)
- Iron loss from hysteresis loop area (鉄損計算)

---

## Future: Magnetic Aftereffect (磁気余効)

The Sugahara laboratory (Kindai University) plans to extend the energy-based
hysteresis model to include **magnetic aftereffect** (magnetic viscosity).

Magnetic aftereffect is the time-dependent relaxation of magnetization after
a change in applied field -- distinct from eddy current effects. It originates
from thermal activation over pinning energy barriers.

**Physics**: After a field change, M(t) relaxes logarithmically:
```
M(t) = M_0 + S * ln(t / t_0)
```
where S is the magnetic viscosity coefficient.

**Energy-based formulation**: The pinning potential U_k naturally provides
the energy barrier landscape. Thermal activation (Arrhenius-type rate) over
these barriers gives time-dependent J_k evolution:
```
dJ_k/dt ~ exp(-Delta_U_k / (k_B * T))
```

This will enable:
- Post-magnetization relaxation analysis (着磁後の緩和)
- Long-term stability prediction of permanent magnets (経年減磁予測)
- Temperature-dependent demagnetization modeling (温度減磁)

**Status**: Planned. Not yet implemented.

---

## References

- Egger et al., "Efficient inverse operator for energy-based vector hysteresis",
  IEEE Trans. Magn. (MAGCON-25-07-0171)
- Francois-Lavet et al., "An energy-based variational model of ferromagnetic
  hysteresis for finite element computations", J. Comp. Appl. Math., 2013
- Matsuo, "Magnetization process and B-input play model", IEEE Trans. Magn., 2011
"""


RADIA_BUILD_AND_RELEASE = """
# Build, Release, and PyPI Publishing

## Build Pipeline

```
Build.ps1 (MSVC + MKL + NGSolve)
  |-> _radia_pybind.pyd (main C++ extension, required)
  |-> peec_matrices.pyd  (PEEC matrix assembly, optional)
  |-> cln_core.pyd       (Lanczos MOR, optional)
  |-> mmm_core.pyd       (MMM solver, optional)
  +-> All copied to src/radia/
```

### Prerequisites

- **Visual Studio 2022** (MSVC compiler)
- **Intel oneAPI Base Toolkit** (MKL only, NOT the Intel compiler)
- **NGSolve** (source build at S:\\NGSolve\\01_GitHub\\install_ngsolve)
- **Python 3.12** with pybind11

### Build Commands

```powershell
# Standard build
powershell -ExecutionPolicy Bypass -File Build.ps1

# Clean rebuild
powershell -ExecutionPolicy Bypass -File Build.ps1 -Rebuild

# Build + run tests
powershell -ExecutionPolicy Bypass -File Build.ps1 -Test

# Verbose output
powershell -ExecutionPolicy Bypass -File Build.ps1 -Verbose
```

### NGSolve for CI Runner

The self-hosted CI runner (NETWORK SERVICE account) cannot access S: drive.
NGSolve must be copied to C:\\NGSolve locally:

```powershell
# Run as Administrator when NGSolve is rebuilt:
robocopy S:\\NGSolve\\01_GitHub\\install_ngsolve C:\\NGSolve /MIR
```

## CI/CD Pipeline (GitHub Actions)

```
git push (main or v* tag)
  |
  v
CI (build-test.yml)
  |-> Verify NGSolve at C:\\NGSolve
  |-> Build.ps1 -Verbose (MSVC + MKL)
  |-> Verify _radia_pybind.pyd exists
  |-> pytest -m basic (quick tests)
  |-> Build_Wheel.ps1 -DryRun (build wheel, verify, no upload)
  |-> Upload artifacts: radia-pyd, radia-wheel, test-results
  |
  v
Release (release.yml) -- triggered by CI success
  |
  +-> [main branch] upload-binaries
  |     Upload .pyd to GitHub Releases (tag: binaries)
  |
  +-> [v* tag only] publish-pypi
        Download wheel artifact
        Publish to PyPI via OIDC Trusted Publishers
        (pypa/gh-action-pypi-publish, no token needed)
```

### PyPI Publishing is AUTOMATIC

When you push a version tag (e.g., `v2.5.0`), the pipeline:
1. CI builds and tests
2. If CI passes, Release workflow publishes wheel to PyPI
3. Uses OIDC Trusted Publishers (no API token stored)

## Release Checklist

### 1. Prepare Release

```python
# 1. Bump version in TWO files (must match):
#    - pyproject.toml: version = "X.Y.Z"
#    - src/radia/__init__.py: __version__ = "X.Y.Z"

# 2. Update CHANGELOG.md

# 3. Build locally and verify
powershell -ExecutionPolicy Bypass -File Build.ps1 -Rebuild -Test
```

### 2. Verify Wheel

```python
import zipfile
whl = zipfile.ZipFile('dist/radia-X.Y.Z-cp312-cp312-win_amd64.whl')
for info in whl.infolist():
    if info.filename.endswith('.pyd'):
        print(f'{info.filename}: {info.file_size} bytes')
# Must contain radia/_radia_pybind.pyd (> 2 MB)
# Must NOT contain any .dll files (MKL policy)
```

### 3. Tag and Push

```bash
git add pyproject.toml src/radia/__init__.py CHANGELOG.md
git commit -m "Release vX.Y.Z: description"
git tag vX.Y.Z
git push origin main vX.Y.Z
```

### 4. Monitor

```bash
gh run list --limit 5        # Check CI status
gh run watch <run-id>         # Watch build
pip install radia==X.Y.Z     # Verify after publish
```

## Wheel Build Details (Build_Wheel.ps1)

1. Clean dist/ and build/ directories
2. `python -m build --wheel`
3. **Remove any bundled DLLs** (MKL policy enforcement)
4. Repack wheel with correct platform tag: `cp312-cp312-win_amd64`
5. `twine check` for metadata validation

**MKL DLL Policy**: Wheel MUST NOT bundle Intel MKL DLLs.
Users install MKL via pip dependency: `mkl>=2024.2.0`.
DLLs go to `{sys.prefix}/Library/bin/`, loaded by `__init__.py`.

## Policy Lint (policy-lint.yml)

Runs on every push. Checks:
1. No `FldUnits()` calls (removed API)
2. No binary files tracked in git
3. No Helmholtz kernel in C++ core (Laplace-only)
4. No `CblasColMajor` (row-major policy)
5. No generated files at repo root
6. No legacy import paths
7. Every example directory has README.md

## Package Structure

```
src/radia/
  __init__.py           # DLL path setup + re-export
  _radia_pybind.pyd     # Main C++ extension (required)
  peec_matrices.pyd     # PEEC matrix assembly (optional)
  cln_core.pyd          # CLN transient solver (optional)
  mmm_core.pyd          # MMM solver (optional)
  *.py                  # Python utility modules
  # NO .dll files (MKL loaded from pip install location)
```

## Troubleshooting

- **CI fails "NGSolve not found"**: Run `robocopy` to sync C:\\NGSolve
- **Wheel too large**: Check for accidentally bundled .dll files
- **Import fails on user machine**: Ensure `pip install mkl` was installed
- **PyPI publish fails**: Check OIDC Trusted Publishers config on PyPI
- **Binary upload fails**: Ensure `binaries` release exists on GitHub
"""


def get_radia_documentation(topic: str = "all") -> str:
    """Return Radia usage documentation by topic."""
    topics = {
        "overview": RADIA_OVERVIEW,
        "geometry": RADIA_GEOMETRY,
        "materials": RADIA_MATERIALS,
        "solving": RADIA_SOLVING,
        "parallelization": RADIA_PARALLELIZATION,
        "fields": RADIA_FIELDS,
        "mesh_import": RADIA_MESH_IMPORT,
        "best_practices": RADIA_BEST_PRACTICES,
        "peec": RADIA_PEEC,
        "ngbem_peec": RADIA_NGBEM_PEEC,
        "efie_preconditioner": RADIA_EFIE_PRECONDITIONER,
        "fem_verification": RADIA_FEM_VERIFICATION,
        "scalar_potential": RADIA_SCALAR_POTENTIAL,
        "play_models": RADIA_PLAY_MODELS,
        "hysteresis": RADIA_HYSTERESIS,
        "build_and_release": RADIA_BUILD_AND_RELEASE,
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
