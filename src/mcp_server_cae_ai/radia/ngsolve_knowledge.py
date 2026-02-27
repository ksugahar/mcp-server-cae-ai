"""
NGSolve usage knowledge base for the Radia MCP server.

Covers: finite element spaces, Maxwell/magnetostatics, solvers,
preconditioners, BEM, mesh generation, nonlinear solving,
electromagnetic formulations (A, Omega, A-Phi, T-Omega),
Kelvin transformation, and common pitfalls gathered from
official docs, community forums, and the EMPY_Analysis project.

Sources:
  - https://docu.ngsolve.org/latest/i-tutorials/
  - https://ngsolve.org/documentation.html (NGS24, Treasure Trove, iFEM)
  - https://forum.ngsolve.org/
  - https://weggler.github.io/ngbem/intro.html
  - S:\\NGSolve\\EMPY\\EMPY_Analysis (K. Sugahara's EM formulations)
"""

NGSOLVE_OVERVIEW = """
# NGSolve Overview

NGSolve is a high-performance finite element library with Python bindings.
Key features relevant to electromagnetic simulation:

## Installation

```bash
pip install ngsolve==6.2.2405   # CRITICAL: use this version for Radia
# Version 6.2.2406+ has Periodic BC regression (Identify() lost in Glue())
# See: https://forum.ngsolve.org/t/3805
```

## Basic Workflow

```python
from ngsolve import *
from netgen.occ import *

# 1. Geometry (OCC or CSG)
box = Box(Pnt(0,0,0), Pnt(1,1,1))
box.faces.name = "outer"

# 2. Mesh
mesh = Mesh(OCCGeometry(box).GenerateMesh(maxh=0.3))

# 3. Finite element space
fes = H1(mesh, order=2, dirichlet="outer")
u, v = fes.TnT()

# 4. Bilinear + linear forms
a = BilinearForm(fes)
a += grad(u)*grad(v)*dx

f = LinearForm(fes)
f += 1*v*dx

# 5. Assemble & solve
a.Assemble()
f.Assemble()
gfu = GridFunction(fes)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="sparsecholesky") * f.vec
```

## Available Direct Solvers

| Solver | Flag | Notes |
|--------|------|-------|
| UMFPACK | `inverse="umfpack"` | Default, single-threaded, robust |
| PARDISO | `inverse="pardiso"` | Multi-threaded (MKL), 4-8x faster |
| Sparse Cholesky | `inverse="sparsecholesky"` | SPD matrices only |
| MUMPS | `inverse="mumps"` | Distributed memory (MPI) |

**Tip**: For production runs, always use PARDISO if available:
```python
gfu.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="pardiso") * f.vec
```
"""

NGSOLVE_FE_SPACES = """
# Finite Element Spaces in NGSolve

## De Rham Complex

NGSolve implements the exact de Rham sequence:

```
H1 --grad--> HCurl --curl--> HDiv --div--> L2
```

Each space has continuous and discontinuous variants.

## Space Summary

| Space | Continuity | DOF Location | Canonical Derivative | EM Use |
|-------|-----------|-------------|---------------------|--------|
| `H1` | Point values | Vertices + edges + faces | `grad` | Scalar potential |
| `HCurl` | Tangential | Edges + faces + cells | `curl` | Vector potential A |
| `HDiv` | Normal | Faces + cells | `div` | Magnetic flux B |
| `L2` | None | Cells | - | DG, source terms |
| `HDivSurface` | Normal (surface) | Surface edges | `div` | BEM currents (RT0/RWG) |
| `SurfaceL2` | None (surface) | Surface faces | - | BEM charges |

## HCurl Space (Nedelec Elements)

Used for vector potential A, electric field E.

```python
fes = HCurl(mesh, order=2, dirichlet="outer")
u, v = fes.TnT()

# Curl-curl bilinear form
a = BilinearForm(fes)
a += curl(u)*curl(v)*dx
```

### CRITICAL: nograds Parameter

For magnetostatics (curl-curl only), use `nograds=True` to remove gradient
basis functions and eliminate gauge freedom:

```python
# Magnetostatics: MUST use nograds=True
fes = HCurl(mesh, order=3, dirichlet="outer", nograds=True)

# Time-harmonic Maxwell: do NOT use nograds
fes = HCurl(mesh, order=3, dirichlet="outer", complex=True)
```

**Why**: Without `nograds=True`, the curl-curl matrix is singular (null space =
gradient fields). The regularization term `1e-8*u*v*dx` alone may not suffice.

## HDiv Space (Raviart-Thomas / BDM)

Used for magnetic flux density B.

```python
# BDM (default)
fes = HDiv(mesh, order=2)

# Raviart-Thomas
fes = HDiv(mesh, order=2, RT=True)
```

## HDivSurface (Surface H(div))

Surface version of HDiv for BEM. Corresponds to RWG (Rao-Wilton-Glisson) or
RT0 basis functions on surface triangles.

```python
fes_J = HDivSurface(mesh, order=0)  # RWG edge-based

# CRITICAL: Use .Trace() for BEM operators
j_trial, j_test = fes_J.TnT()
V_op = LaplaceSL(j_trial.Trace() * ds("conductor")) * j_test.Trace() * ds("conductor")
```

## SurfaceL2

Face-based L2 space on surfaces. Used for charge density in PEEC.

```python
fes_L2 = SurfaceL2(mesh, order=0, dual_mapping=True,
                    definedon=mesh.Boundaries("conductor"))
```

**dual_mapping=True**: Correct L2 discretization for dual space in BEM.

## Compound (Product) Spaces

```python
fes = fesH1 * fesL2    # Product space
u, dudn = fes.TrialFunction()
v, dvdn = fes.TestFunction()
```

## DOF Access

```python
# Get DOFs for a mesh entity
edge_dofs = fes.GetDofNrs(NodeId(EDGE, 10))
face_dofs = fes.GetDofNrs(NodeId(FACE, 10))

# Available operators
gf.Operators()  # List available operators for GridFunction
```
"""

NGSOLVE_MAXWELL = """
# Maxwell Equations & Magnetostatics in NGSolve

## Magnetostatics (A-Formulation)

Solves: curl(nu * curl(A)) = J, where nu = 1/(mu_0 * mu_r).

```python
from ngsolve import *
from netgen.occ import *

MU_0 = 4e-7 * 3.14159265358979

# Geometry
core = Box(Pnt(-0.02,-0.02,-0.02), Pnt(0.02,0.02,0.02))
core.solids.name = "core"
core.faces.maxh = 2e-3   # Local mesh refinement on core surface

air = Sphere(Pnt(0,0,0), 0.12) - core
air.solids.name = "air"
geo = Glue([core, air])
geo.faces.name = "outer"

mesh = Mesh(OCCGeometry(geo).GenerateMesh(maxh=8e-3))

# Material properties
mu_r = mesh.MaterialCF({"core": 1000}, default=1)
nu = 1 / (MU_0 * mu_r)

# HCurl space with nograds=True (magnetostatics!)
fes = HCurl(mesh, order=2, dirichlet="outer", nograds=True)
u, v = fes.TnT()

# Bilinear form with regularization
a = BilinearForm(fes)
a += nu * curl(u) * curl(v) * dx
a += 1e-8 * nu * u * v * dx   # Regularization for well-posedness

# BDDC preconditioner (register BEFORE assembly)
c = Preconditioner(a, "bddc")

# Source term (magnetization or current density)
J_src = mesh.MaterialCF({"core": (0, 0, 1e6)}, default=(0,0,0))
f = LinearForm(fes)
f += J_src * v * dx

with TaskManager():
    a.Assemble()
    f.Assemble()

# Solve with preconditioned CG
gfu = GridFunction(fes)
with TaskManager():
    solvers.CG(sol=gfu.vec, rhs=f.vec, mat=a.mat,
               pre=c.mat, maxsteps=500, printrates=True, tol=1e-10)

# B = curl(A)
B = curl(gfu)
```

## Permanent Magnet Source

```python
# Magnetization as source term: RHS = integral(M * curl(v))
mag = mesh.MaterialCF({"magnet": (1, 0, 0)}, default=(0,0,0))
M_A_per_m = 954930  # Br=1.2T -> M = Br/mu_0

f = LinearForm(fes)
f += M_A_per_m * mag * curl(v) * dx("magnet")
```

## Time-Harmonic Maxwell

```python
# Complex HCurl space (no nograds!)
fes = HCurl(mesh, order=2, dirichlet="outer", complex=True)
u, v = fes.TnT()

omega = 2 * 3.14159 * 1e6  # 1 MHz
sigma = 5.8e7  # Cu conductivity

# curl-curl + j*omega*sigma mass
a = BilinearForm(fes)
a += 1/MU_0 * curl(u) * curl(v) * dx
a += 1j * omega * sigma * u * v * dx("conductor")
a.Assemble()

# Solve with PARDISO (complex direct)
gfu = GridFunction(fes)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="pardiso") * f.vec
```

## Nonlinear B-H Curve (Newton Method)

```python
# Define nonlinear nu(|B|^2)
from ngsolve import Norm, sqrt

# Example: simple tanh model
B_sat = 2.0  # Tesla
nu_0 = 1 / MU_0
nu_r_max = 1000

def nu_nonlinear(B2):
    # nu = 1/(mu_0 * mu_r(B))
    # Simple model: mu_r decreases with B
    return nu_0 * (1 + (nu_r_max - 1) / (1 + B2 / B_sat**2))

# In bilinear form:
a = BilinearForm(fes)
a += nu_nonlinear(InnerProduct(curl(u), curl(u))) * curl(u) * curl(v) * dx

# Newton iteration
gfu = GridFunction(fes)
for it in range(20):
    a.Apply(gfu.vec, res)
    a.AssembleLinearization(gfu.vec)
    inv = a.mat.Inverse(fes.FreeDofs(), inverse="pardiso")
    du = inv * res
    gfu.vec.data -= du
    err = sqrt(abs(InnerProduct(du, res)))
    print(f"Newton iter {it}: err = {err:.2e}")
    if err < 1e-10:
        break
```

## Local Mesh Refinement (OCC)

```python
# Refine only on specific faces (much cheaper than global refinement)
core.faces.maxh = 2e-3        # Fine mesh on core surface
air.faces.maxh = 8e-3         # Coarser air boundary

# This adds only ~6% more elements vs global refinement
```
"""

NGSOLVE_SOLVERS = """
# Solver Selection in NGSolve

## Direct Solvers

```python
# UMFPACK (default, single-threaded)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="umfpack") * f.vec

# PARDISO (multi-threaded, MKL, 4-8x faster)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="pardiso") * f.vec

# Sparse Cholesky (SPD only, efficient)
gfu.vec.data = a.mat.Inverse(fes.FreeDofs(), inverse="sparsecholesky") * f.vec
```

### PARDISO vs UMFPACK

| Feature | PARDISO | UMFPACK |
|---------|---------|---------|
| Threading | Multi-threaded (MKL) | Single-threaded |
| Speed | 4-8x faster | Baseline |
| Complex | Yes | Yes |
| Availability | Requires MKL | Always available |
| Stability | Excellent | Excellent |

**Rule**: Use PARDISO for production, UMFPACK for debugging.

## Iterative Solvers

### CG (Conjugate Gradient) - SPD systems

```python
pre = Preconditioner(a, "bddc")
a.Assemble()

solvers.CG(mat=a.mat, rhs=f.vec, sol=gfu.vec,
           pre=pre.mat, maxsteps=500, tol=1e-10, printrates=True)
```

### GMRes - Non-symmetric / indefinite systems

```python
from ngsolve.solvers import GMRes

result = GMRes(A=system_mat, b=rhs_vec, pre=pre_mat,
               tol=1e-6, maxsteps=200, printrates=True)
```

### MinRes - Symmetric indefinite

```python
solvers.MinRes(mat=a.mat, rhs=f.vec, sol=gfu.vec,
               pre=pre.mat, maxsteps=500, tol=1e-10)
```

## Solver Selection Guide

| System Type | Direct | Iterative |
|-------------|--------|-----------|
| SPD (Poisson, curl-curl) | sparsecholesky/pardiso | CG + BDDC |
| Symmetric indefinite (saddle point) | pardiso/umfpack | MinRes + block precond |
| Non-symmetric (Navier-Stokes) | pardiso/umfpack | GMRes |
| Complex symmetric (eddy current) | pardiso | CG + BDDC (complex) |
| BEM dense | N/A | GMRes + Calderon precond |
| Small (<10K DOF) | pardiso | Not needed |
| Large (>100K DOF) | May run out of memory | BDDC + AMG |

## Eigenvalue Problems

```python
# Generalized eigenvalue: a*u = lambda*m*u
a = BilinearForm(fes)
a += curl(u)*curl(v)*dx
a.Assemble()

m = BilinearForm(fes)
m += u*v*dx
m.Assemble()

# PINVIT (preconditioned inverse iteration)
pre = Preconditioner(a, "bddc")
evals, evecs = solvers.PINVIT(a.mat, m.mat, pre.mat,
                               num=10, maxit=50, printrates=True)
```
"""

NGSOLVE_PRECONDITIONERS = """
# Preconditioners in NGSolve

## Available Preconditioners

| Type | Name | Best For |
|------|------|----------|
| Jacobi | `"local"` | Quick testing, simple problems |
| Block Jacobi | `"local"` + condense | Higher-order H1 |
| Multigrid | `"multigrid"` | h-refined H1, optimal complexity |
| AMG | `"h1amg"` | Large H1 problems, automatic hierarchy |
| BDDC | `"bddc"` | General purpose, parallel, curl-curl |
| Direct | `"direct"` | Coarse level, small problems |

## BDDC Preconditioner (Recommended for EM)

```python
# CRITICAL: Register BEFORE assembly!
c = Preconditioner(a, "bddc")
a.Assemble()

# Use with CG
solvers.CG(mat=a.mat, rhs=f.vec, sol=gfu.vec,
           pre=c.mat, maxsteps=500, tol=1e-10)
```

### BDDC Parameters

```python
# Static condensation for better conditioning
a = BilinearForm(fes, eliminate_internal=True)

# AMG coarse solver for large problems
c = Preconditioner(a, "bddc", coarsetype="h1amg")

# Control wirebasket DOFs
fes = H1(mesh, order=5, wb_withedges=False)  # Only vertex wirebasket
```

### BDDC DOF Classification

| Type | Role |
|------|------|
| LOCAL_DOF | Condensable (interior) |
| WIREBASKET_DOF | Conforming (vertices, first edge DOF) |
| INTERFACE_DOF | Non-conforming (remaining edge/face DOFs) |

### Custom DOF Classification

```python
for ed in mesh.edges:
    dofs = fes.GetDofNrs(ed)
    for d in dofs:
        fes.SetCouplingType(d, COUPLING_TYPE.INTERFACE_DOF)
    # First edge DOF = wirebasket
    fes.SetCouplingType(dofs[0], COUPLING_TYPE.WIREBASKET_DOF)
```

## FEM-BEM Preconditioner

For coupled FEM-BEM systems (indefinite):

```python
# Block diagonal preconditioner
bfpre = BilinearForm(grad(u)*grad(v)*dx + 1e-10*u*v*dx +
                     dudn*dvdn*ds("outer")).Assemble()
pre = bfpre.mat.Inverse(freedofs=fes.FreeDofs(), inverse="sparsecholesky")

# Solve with GMRes (indefinite system)
GMRes(A=system, b=rhs, pre=pre, tol=1e-6, maxsteps=200)
```
"""

NGSOLVE_BEM = """
# Boundary Element Method in NGSolve (ngbem)

## Overview

ngbem provides Galerkin BEM operators integrated with NGSolve function spaces.

```python
from ngsolve.bem import LaplaceSL, LaplaceDL, HelmholtzSL, HelmholtzDL
```

## Available BEM Operators

| Operator | Function | Kernel |
|----------|----------|--------|
| Single Layer (V) | `LaplaceSL` / `HelmholtzSL` | G(r) or G_k(r) |
| Double Layer (K) | `LaplaceDL` / `HelmholtzDL` | dG/dn |
| Hypersingular (D) | Via curl of SL | d^2G/dn^2 |

## Basic BEM Assembly

```python
from ngsolve import *
from ngsolve.bem import LaplaceSL

mesh = Mesh(...)
fes = SurfaceL2(mesh, order=0, definedon=mesh.Boundaries("surf"))
u, v = fes.TnT()

with TaskManager():
    V = LaplaceSL(u*ds("surf")) * v*ds("surf")

# Extract dense matrix
V_mat = V.mat
```

## CRITICAL: .Trace() for HDivSurface BEM

When using LaplaceSL/HelmholtzSL with HDivSurface, you MUST use .Trace():

```python
fes_J = HDivSurface(mesh, order=0)
j_trial, j_test = fes_J.TnT()

# CORRECT - with .Trace()
V_op = LaplaceSL(j_trial.Trace() * ds("conductor")) * j_test.Trace() * ds("conductor")

# WRONG - without .Trace() -> corrupted boundary-edge DOFs
V_op = LaplaceSL(j_trial * ds("conductor")) * j_test * ds("conductor")
```

**Bug symptom**: Without `.Trace()`, boundary-edge DOFs get corrupted diagonal
entries (e.g., -1.1e+11 instead of ~1e-10), causing wildly wrong results.

**Diagnostic**: Check diagonal of assembled matrix:
```python
M = np.array(V_op.mat.IsComplex() and V_op.mat or V_op.mat)
diag = np.real(np.diag(M))
print(f"min diag = {diag.min():.3e}")  # Must be positive
```

## bonus_intorder Parameter

Controls extra quadrature points for near-singular integrals:

```python
# Standard: no bonus
V = LaplaceSL(u*ds("surf")) * v*ds("surf")

# With bonus integration order (more accurate, slower)
V = LaplaceSL(u*ds("surf", bonus_intorder=4)) * v*ds("surf", bonus_intorder=4)
```

| bonus_intorder | Use Case |
|---------------|----------|
| 0 (default) | Far interactions, quick tests |
| 2-3 | Preconditioner assembly |
| 4 | EFIE operator assembly |
| 6+ | High accuracy validation |

## FEM-BEM Coupling Pattern

```python
from ngsolve.bem import LaplaceSL, LaplaceDL

# Interior FEM space
fesH1 = H1(mesh, order=4, dirichlet="top|bottom")

# Boundary BEM space
fesL2 = SurfaceL2(mesh, order=3, dual_mapping=True,
                  definedon=mesh.Boundaries("coupling"))

# Product space
fes = fesH1 * fesL2
u, dudn = fes.TrialFunction()
v, dvdn = fes.TestFunction()

# FEM part
a_fem = BilinearForm(grad(u)*grad(v)*dx).Assemble()

# BEM operators
n = specialcf.normal(3)
with TaskManager():
    V = LaplaceSL(dudn*ds("coupling")) * dvdn*ds("coupling")
    K = LaplaceDL(u*ds("coupling")) * dvdn*ds("coupling")
    D = LaplaceSL(Cross(grad(u).Trace(),n)*ds("coupling")) * \\
        Cross(grad(v).Trace(),n)*ds("coupling")

# Mass matrix for coupling
M = BilinearForm(u*dvdn*ds("coupling")).Assemble()

# Combined system (symmetric indefinite)
system = a_fem.mat + D.mat - (0.5*M.mat + K.mat).T - \\
         (0.5*M.mat + K.mat) - V.mat
```

## Extracting Dense BEM Matrix

```python
import numpy as np

def extract_dense(mat, n):
    \"\"\"Extract dense numpy matrix from NGSolve operator.\"\"\"
    M = np.zeros((n, n), dtype=complex)
    for i in range(n):
        ei = mat.CreateColVector()
        ei[:] = 0
        ei[i] = 1
        col = mat * ei
        for j in range(n):
            M[j, i] = col[j]
    return M
```

## EFIE Calderon Preconditioner (Schoeberl)

For EFIE with HelmholtzSL on HDivSurface, Calderon preconditioning reduces
GMRES iterations from O(N) to O(1):

```python
# EFIE operators
V1 = HelmholtzSL(u.Trace()*ds(bonus_intorder=4), kappa) * v.Trace()*ds(bonus_intorder=4)
V2 = HelmholtzSL(div(u.Trace())*ds(bonus_intorder=4), kappa) * div(v.Trace())*ds(bonus_intorder=4)

lhs = 1j*kappa * V1.mat + 1/(1j*kappa) * V2.mat

# Preconditioner: rotated SL + potential correction
invM = BilinearForm(u.Trace()*v.Trace()*ds).Assemble().mat.Inverse(inverse="sparsecholesky")
n = specialcf.normal(3)
Vrot = HelmholtzSL(Cross(u.Trace(),n)*ds, kappa) * Cross(v.Trace(),n)*ds
Vpot = HelmholtzSL(upot*ds, kappa) * vpot*ds
surfcurl = BilinearForm(Cross(grad(upot).Trace(),n) * v.Trace()*ds).Assemble().mat
invMH1 = BilinearForm(upot*vpot*ds).Assemble().mat.Inverse(inverse="sparsecholesky")

pre = invM @ (kappa*Vrot.mat - 1/kappa*surfcurl@invMH1@Vpot.mat@invMH1@surfcurl.T) @ invM

# Solve with GMRES
gfj.vec[:] = solvers.GMRes(A=lhs, b=rhs.vec, pre=pre, maxsteps=500, tol=1e-8)
```
"""

NGSOLVE_MESH = """
# Mesh Generation in NGSolve (Netgen + OCC)

## OCC Geometry (Recommended)

```python
from netgen.occ import *

# Basic shapes
box = Box(Pnt(0,0,0), Pnt(1,1,1))
sphere = Sphere(Pnt(0,0,0), 1.0)
cylinder = Cylinder(Pnt(0,0,0), Z, r=0.5, h=2.0)

# Boolean operations
result = box - sphere          # Difference
result = box * sphere          # Intersection
result = Glue([box, sphere])   # Non-overlapping union

# Face naming (for boundary conditions)
box.faces.name = "outer"
box.faces.Min(Z).name = "bottom"
box.faces.Max(Z).name = "top"

# Local mesh size
box.faces.maxh = 0.1           # All faces
box.faces.Min(Z).maxh = 0.02   # Only bottom face
box.solids.maxh = 0.05         # Volume constraint

# Generate mesh
mesh = Mesh(OCCGeometry(box).GenerateMesh(maxh=0.3))
```

## 2D Mesh Generation

```python
from netgen.occ import *

# CRITICAL: specify dim=2 for 2D!
rect = Rectangle(3, 5).Face()
mesh = Mesh(OCCGeometry(rect, dim=2).GenerateMesh(maxh=1))

# Without dim=2, you get a 3D mesh of a surface -> wrong!
```

## STEP Import

```python
from netgen.occ import OCCGeometry

geo = OCCGeometry("model.step")
mesh = Mesh(geo.GenerateMesh(maxh=0.5))
```

## Structured Meshes

```python
from ngsolve import *

# 2D structured
mesh = MakeStructured2DMesh(nx=10, ny=10,
                             mapping=lambda x,y: (x, y))

# 3D structured
mesh = MakeStructured3DMesh(nx=5, ny=5, nz=5,
                             mapping=lambda x,y,z: (x, y, z))
```

## Surface Mesh for BEM

```python
from netgen.occ import *

# Surface-only mesh (no volume)
face = Glue(Sphere(Pnt(0,0,0), 1).faces)
mesh = Mesh(OCCGeometry(face).GenerateMesh(maxh=0.2))
mesh.Curve(3)  # Curved elements for accuracy

# Ring mesh for BEM inductance
torus = Torus(R=0.01, r=0.001)   # Not always available
# Alternative: Revolution of circle
from netgen.occ import *
circle = Circle(Pnt(R, 0, 0), r).Face()
ring = circle.Revolve(Axis(Pnt(0,0,0), Z), 360)
ring_mesh = Mesh(OCCGeometry(Glue(ring.faces)).GenerateMesh(maxh=maxh))
```

## Mesh Refinement

```python
# Global h-refinement
mesh.Refine()

# HP refinement (geometric grading toward edges/corners)
mesh.RefineHP(levels=2)

# Curved elements (higher-order geometry approximation)
mesh.Curve(order=3)

# Adaptive refinement based on error estimator
for l in range(max_levels):
    # ... solve ...
    # ... compute error estimator ...
    mesh.Refine()
```

## Mesh Information

```python
print(f"Elements: {mesh.ne}")
print(f"Vertices: {mesh.nv}")
print(f"Edges: {len(list(mesh.edges))}")
print(f"Faces: {len(list(mesh.faces))}")
print(f"Boundary regions: {mesh.GetBoundaries()}")
print(f"Material regions: {mesh.GetMaterials()}")
```
"""

NGSOLVE_NONLINEAR = """
# Nonlinear Problem Solving in NGSolve

## Newton's Method (Built-in)

```python
from ngsolve.solvers import Newton

# Define nonlinear form
a = BilinearForm(fes)
a += nu(InnerProduct(curl(u),curl(u))) * curl(u) * curl(v) * dx

# Built-in Newton solver
Newton(a, gfu, printing=True, maxerr=1e-10, maxit=20, dampfactor=1.0)
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `maxerr` | 1e-10 | Convergence tolerance |
| `maxit` | 20 | Maximum iterations |
| `dampfactor` | 1.0 | Damping (0<d<=1, use <1 for difficult problems) |
| `printing` | False | Print convergence info |

## Manual Newton Implementation

```python
def newton_solve(gfu, a, fes, tol=1e-10, maxiter=20, damping=1.0):
    res = gfu.vec.CreateVector()
    du = gfu.vec.CreateVector()

    for it in range(maxiter):
        a.Apply(gfu.vec, res)
        a.AssembleLinearization(gfu.vec)

        inv = a.mat.Inverse(fes.FreeDofs(), inverse="pardiso")
        du.data = inv * res

        gfu.vec.data -= damping * du

        err = sqrt(abs(InnerProduct(du, res)))
        print(f"Newton {it}: err = {err:.2e}")
        if err < tol:
            return it + 1

    raise RuntimeError(f"Newton did not converge after {maxiter} iterations")
```

## Key Technical Points

1. **`a.Apply(vec, res)`**: Evaluates the nonlinear form at `vec`, stores result in `res`
2. **`a.AssembleLinearization(vec)`**: Assembles the Jacobian at `vec` via symbolic differentiation
3. **Symbolic differentiation**: NGSolve automatically differentiates nonlinear CoefficientFunctions
4. **Damping**: Use `dampfactor < 1.0` for strong nonlinearities (e.g., 0.5 for first few iterations)
5. **Convergence**: Well-posed problems show quadratic convergence (error squares each iteration)

## Nonlinear Material Example (B-H Curve)

```python
# Piecewise linear interpolation of B-H curve
BH_points = [(0, 0), (100, 0.5), (500, 1.0), (1000, 1.5), (10000, 2.0)]
# ... (implement interpolation as CoefficientFunction)

# Or use tanh model:
from ngsolve import atan, sqrt

def nu_BH(B_squared):
    \"\"\"Reluctivity nu = 1/(mu_0 * mu_r(|B|)).\"\"\"
    mu_0 = 4e-7 * 3.14159
    B_mag = sqrt(B_squared + 1e-20)  # Avoid division by zero
    M_sat = 1.6e6  # A/m, saturation magnetization
    chi = M_sat / (B_mag / mu_0 + 1e-10)  # Susceptibility
    mu_r = 1 + chi
    return 1 / (mu_0 * mu_r)
```
"""

NGSOLVE_PITFALLS = """
# Common Pitfalls in NGSolve

## 1. Assignment Operator (CRITICAL)

```python
# WRONG - creates symbolic expression, NOT evaluated!
y = 2 * x_vec

# CORRECT - evaluates and stores result
y.data = 2 * x_vec

# WRONG - nested operations need temporaries
result.data = mat * (u1 + u2)  # FAILS

# CORRECT - separate steps
temp.data = u1 + u2
result.data = mat * temp
```

**Rule**: Always use `.data =` to write to existing vectors.

## 2. Overwriting x, y, z Coordinate Variables

```python
# WRONG - destroys x as coordinate!
for x in range(10):
    pass
# Now x is 9, not the coordinate CoefficientFunction

# CORRECT - use different variable name
for xi in range(10):
    pass
# x, y, z still work as coordinates
```

## 3. Missing dim=2 for 2D OCC Geometry

```python
# WRONG - produces 3D surface mesh
mesh = Mesh(OCCGeometry(rect).GenerateMesh(maxh=1))

# CORRECT - produces 2D mesh
mesh = Mesh(OCCGeometry(rect, dim=2).GenerateMesh(maxh=1))
```

## 4. Preconditioner Registration Order

```python
# WRONG - preconditioner doesn't see element matrices
a.Assemble()
c = Preconditioner(a, "bddc")  # Too late!

# CORRECT - register before assembly
c = Preconditioner(a, "bddc")
a.Assemble()
```

## 5. FreeDofs vs AllDofs

```python
# CORRECT - respects Dirichlet BC
inv = a.mat.Inverse(fes.FreeDofs())

# WRONG - includes constrained DOFs -> singular matrix
inv = a.mat.Inverse()  # Dangerous!
```

## 6. TaskManager Scope

```python
# CORRECT - wrap assembly and solve
with TaskManager():
    a.Assemble()
    f.Assemble()
    solvers.CG(...)

# Also valid - global TaskManager
SetNumThreads(8)
with TaskManager():
    # All parallel work here
    pass
```

## 7. BEM .Trace() Requirement

```python
# WRONG - corrupts boundary DOFs
V = LaplaceSL(j_trial * ds) * j_test * ds

# CORRECT
V = LaplaceSL(j_trial.Trace() * ds) * j_test.Trace() * ds
```

## 8. nograds for Magnetostatics

```python
# WRONG - singular system for curl-curl
fes = HCurl(mesh, order=2, dirichlet="outer")

# CORRECT - removes gradient null space
fes = HCurl(mesh, order=2, dirichlet="outer", nograds=True)
```

## 9. GridFunction.Set() vs Direct Assignment

```python
# CORRECT - projects function onto FE space
gfu.Set(sin(x)*cos(y), definedon=mesh.Materials("domain"))

# CORRECT - set with BND flag for Dirichlet
gfu.Set(x, BND)

# WRONG - BND only sets on Dirichlet-marked boundaries
gfu.Set(x, BND)  # Only sets on dirichlet="..." boundaries!

# To set on ALL boundaries:
gfu.Set(x, mesh.Boundaries(".*"))
```

## 10. Complex Spaces

```python
# For eddy current / time-harmonic: MUST use complex=True
fes = HCurl(mesh, order=2, complex=True, dirichlet="outer")

# WRONG - real space for complex problem
fes = HCurl(mesh, order=2, dirichlet="outer")
a += 1j * omega * sigma * u * v * dx  # Will fail or give wrong results!
```

## 11. Mesh.MaterialCF Spelling

```python
# Material names must match EXACTLY
mu_r = mesh.MaterialCF({"core": 1000}, default=1)

# Check available materials:
print(mesh.GetMaterials())  # ['air', 'core', 'coil']
```

## 12. InnerProduct vs Multiply

```python
# For vector-valued CoefficientFunctions, use InnerProduct:
a += InnerProduct(curl(u), curl(v)) * dx

# Or shorthand (works for simple cases):
a += curl(u) * curl(v) * dx

# For matrix-valued, always use InnerProduct
```

## 13. VTK Export

```python
# Export to VTK for ParaView
vtk = VTKOutput(mesh, coefs=[gfu, curl(gfu)],
                names=["A", "B"],
                filename="output",
                subdivision=2)
vtk.Do()
```

## 14. Regularization Term for curl-curl (Forum: Thread 3237)

Pure curl-curl without L2 regularization causes singular matrix errors:

```python
# WRONG - singular matrix with iterative solvers
a += (1/mu_0) * curl(u)*curl(v)*dx

# CORRECT - add small L2 regularization
a += (1/mu_0) * (curl(u)*curl(v)*dx + 1e-6*u*v*dx)
#                                      ^^^^^^^^ L2 term
```

**Note**: `1e-6*curl(u)*curl(v)*dx` is NOT the same as `1e-6*u*v*dx`.
The L2 mass term regularizes the gradient null space; a second curl-curl
term does nothing.

## 15. curl(E) Has No Trace on Edges in HCurl (Forum: Thread 3757)

```python
# WRONG - "don't know how I shall evaluate" error
line_integral = Integrate(curl(E), mesh, definedon=edge)

# CORRECT - interpolate H field first, then integrate
H_gf = GridFunction(HCurl(mesh, order=order))
H_gf.Set(1/(1j*omega*mu) * curl(E))
current = Integrate(H_gf, mesh, definedon=path)
```

**Rule**: curl of an HCurl field is element-wise constant. You cannot
evaluate it on lower-dimensional entities (edges, faces). Always
interpolate into an appropriate space first.

## 16. bonus_intorder for Curved HCurl Elements (Forum: Thread 2068)

```python
# Default integration order is insufficient for curved tets
# Causes O(1e-6) errors

# CORRECT - add bonus_intorder=2 for curved meshes
a += curl(u)*curl(v)*dx(bonus_intorder=2)
f += source*v*dx(bonus_intorder=2)
```

**When needed**: Only for curved tetrahedral meshes (`mesh.Curve(order>=2)`).
Linear geometry (order=1) or boundary layer meshes work fine with defaults.

## 17. BH Curve: Use Analytical Fit, NOT scipy interp (Forum: Thread 2821)

```python
# WRONG - scipy interp doesn't work with NGSolve CoefficientFunctions
from scipy.interpolate import interp1d
f = interp1d(H_data, B_data)
mu = f(H_gf)  # ValueError: object arrays not supported

# CORRECT - use NGSolve symbolic math
B_gf = GridFunction(fes)
mu_gf = GridFunction(fes)
mu_gf.Set(160*sqrt(1-((B_gf/2.5) + 0.17*(B_gf/2.5)**4)**2))
```

**Rule**: NGSolve CoefficientFunctions support `sqrt`, `**`, `+`, `*`,
`atan`, `exp`, `log`, but NOT arbitrary Python callbacks. Fit your
B-H data to an analytical expression.

## 18. GridFunction is NOT a NumPy Array (Forum: Thread 1859)

For p >= 2, `gfu.vec` contains polynomial coefficients, NOT point values.

```python
# WRONG - gives coefficients, not field values
values = np.array(gfu.vec.FV().NumPy())  # Coefficients!

# CORRECT - use IntegrationRuleSpace for point values
fesir = IntegrationRuleSpace(mesh, order=order)
gfuir = GridFunction(fesir)
gfuir.Interpolate(gfu)  # Now contains actual point values
point_values = np.array(gfuir.vec.data[:])
```

## 19. Python Krylov Solvers for Nested BlockMatrix (Forum: Thread 3399)

```python
# C++ GMRes cannot handle nested BlockMatrix
# Use Python implementation instead:
from ngsolve.krylovspace import CG, GMRes

lhs = BlockMatrix([[A_mat, -B_mat, None],
                   [C_mat, None, -D_mat],
                   [None, M_mat, V_mat]])

sol = GMRes(A=lhs, b=rhs, pre=pre, tol=1e-8, maxsteps=400)
```

## 20. SurfaceL2 for HDiv Normal Matching (Forum: Thread 3379)

Use SurfaceL2 as Lagrange multiplier space for matching HDiv normals:

```python
# SurfaceL2 is the proper space for HDiv normal-trace continuity
fes_lambda = SurfaceL2(mesh, order=order,
                       definedon=mesh.Boundaries("interface"))
```

## 21. type1=True for Nedelec Elements (EMPY)

For magnetostatic/eddy current A-formulations, use first-kind Nedelec elements:

```python
# RECOMMENDED for electromagnetic problems
fesA = HCurl(mesh, order=feOrder, type1=True, nograds=True)

# type1=True: tangential continuity, lower DOF count
# Default (type1=False): second-kind Nedelec, more DOFs
```

**When**: All A-based formulations (A-1, A-2, A-Phi, A-Omega). The T-Omega
formulation also uses type1=True for the electric vector potential T.

## 22. Dirichlet DOF Zeroing After Partial Assembly (EMPY)

When assembling RHS with both Dirichlet and Neumann contributions, the
Dirichlet part must be isolated before adding Neumann terms:

```python
# Step 1: Assemble Dirichlet contribution
gfA.Set(Av, BND, mesh.Boundaries(total_boundary))
f = LinearForm(fes)
f += 1/Mu * curl(gfA) * curl(N) * dx(reduced_region)
f.Assemble()

# Step 2: CRITICAL - Zero out boundary DOF contributions
fcut = np.array(f.vec.FV())[fes.FreeDofs()]
np.array(f.vec.FV(), copy=False)[:] = 0
np.array(f.vec.FV(), copy=False)[fes.FreeDofs()] = fcut

# Step 3: Now add Neumann terms
f += Cross(N.Trace(), Hv) * normal * ds(total_boundary)
f.Assemble()
```

**Why**: Without zeroing, Dirichlet DOF entries leak into the RHS,
corrupting the Neumann contribution.

## 23. CloseSurfaces for Quasi-2D Problems (EMPY)

To solve a 2D problem in 3D NGSolve, identify top/bottom faces
and use ZRefine to create a single element layer:

```python
# Geometry: identify top and bottom
iron.faces.Min(Z).Identify(
    iron.faces.Max(Z), "bot-top", type=IdentificationType.CLOSESURFACES)

# Mesh: single z-layer
ngmesh = OCCGeometry(geo).GenerateMesh(maxh=0.1)
ngmesh.ZRefine("bot-top", [])  # Empty list = no intermediate layers
mesh = Mesh(ngmesh).Curve(1)
```

**Pitfall**: Forgetting `ZRefine` creates multiple z-layers, wasting DOFs.
Always verify `mesh.ne` is the expected number.

## 24. A-Omega Interface Coupling is INDEFINITE (EMPY)

The A-Omega mixed formulation produces a saddle-point system:

```python
# The interface coupling term:
a += -(Omega * (curl(N).Trace() * normal) +
       o * (curl(A).Trace() * normal)) * ds(total_boundary)
```

**Consequence**: The system matrix is INDEFINITE. CG will fail or diverge.
Use MinRes, GMRES, or a custom solver. Extract CSR and use scipy:

```python
A_csr = sp.csr_matrix(a.mat.CSR())
x = sp.linalg.spsolve(A_csr[np.ix_(free, free)], f_free)
```

## 25. HtoOmega Surface Projection (EMPY)

Convert a vector H field to scalar potential Omega on a boundary surface:

```python
fes_surf = H1(mesh, order=feOrder, definedon=mesh.Boundaries(boundary))
omega, psi = fes_surf.TnT()

# Surface Laplacian: find Omega such that grad(Omega) ~= H on surface
a = BilinearForm(fes_surf)
a += grad(omega).Trace() * grad(psi).Trace() * ds(boundary)

f = LinearForm(fes_surf)
f += grad(psi).Trace() * H * ds(boundary)
```

**Use case**: Setting Dirichlet BC for Omega from a known H field
in the total/reduced domain decomposition.

## 26. EMPY_Field Version Incompatibility (EMPY)

C++ pybind11 modules compiled against one NGSolve version may break with
newer versions due to internal API changes (CoefficientFunction vtable, etc.).

```
# Symptom: import crashes or method not found errors
ImportError: DLL load failed while importing EMPY_Field

# Fix: rebuild .pyd against the target NGSolve version
# Or: pin NGSolve version in requirements.txt
ngsolve==6.2.2405
```

**Rule**: Always pin NGSolve version for C++ extension compatibility.

## 27. Static Condensation Pattern (i-tutorials unit-1.4)

Static condensation eliminates internal DOFs, solving only interface DOFs:

```python
a = BilinearForm(grad(u)*grad(v)*dx, condense=True).Assemble()

# Solution recovery: 3-step process
invS = a.mat.Inverse(freedofs=fes.FreeDofs(coupling=True))
ext = IdentityMatrix() + a.harmonic_extension
extT = IdentityMatrix() + a.harmonic_extension_trans
invA = ext @ invS @ extT + a.inner_solve
u.vec.data = invA * f.vec
```

| Attribute | Purpose |
|-----------|---------|
| `a.harmonic_extension` | Maps interface solution -> local DOFs |
| `a.harmonic_extension_trans` | Maps local RHS -> interface RHS |
| `a.inner_solve` | Direct solve of local DOFs |

**Key**: Use `fes.FreeDofs(coupling=True)` for interface-only free DOFs.

## 28. VectorH1 is WRONG for EM Fields (iFEM theory)

```python
# WRONG: 3 independent C^0 scalar components
fes = VectorH1(mesh, order=2)  # Over-constrains tangential continuity!

# CORRECT for E, A fields:
fes = HCurl(mesh, order=2)  # Tangential continuity, normal can jump

# CORRECT for B, J fields:
fes = HDiv(mesh, order=2)   # Normal continuity, tangential can jump
```

**Why**: VectorH1 enforces full C^0 continuity on ALL components. Physical
electromagnetic fields only have tangential (HCurl) or normal (HDiv)
continuity across material interfaces. Using VectorH1 introduces spurious
modes and incorrect interface conditions.

## 29. Higher Order Only Helps for Smooth Solutions (iFEM theory)

Convergence rates depend on solution regularity:
- **P1**: H1 error = O(h), L2 error = O(h^2)
- **P2**: H1 error = O(h^2), L2 error = O(h^3)
- **Pk**: H1 error = O(h^k), L2 error = O(h^{k+1})

**BUT**: At material interfaces (mu jumps), regularity is limited to
H^{1+alpha} where alpha < 1. Higher p gives no benefit there.

```python
# For problems with mu jumps: h-refine near interface, not p-refine
core.faces.maxh = 2e-3    # Fine mesh at mu-jump surface
air.solids.maxh = 8e-3    # Coarser elsewhere
```

## 30. HCurl AMG Preconditioner (i-tutorials unit-2.1.5)

For large HCurl systems, use the HCurl AMG preconditioner:

```python
from ngsolve import preconditioners

fes = HCurl(mesh, order=0)
a = BilinearForm(1/mu*curl(u)*curl(v)*dx + 1e-6/mu*u*v*dx)

# HCurl AMG with Hiptmair smoother
pre = preconditioners.HCurlAMG(a, verbose=2, smoothingsteps=3,
    smoothedprolongation=True, maxcoarse=10, maxlevel=10,
    potentialsmoother='amg')

with TaskManager():
    a.Assemble()
    inv = solvers.CGSolver(a.mat, pre.mat, tol=1e-8, maxiter=100)
    gfu.vec.data = inv * f.vec
```

**Hiptmair smoother**: Decomposes HCurl = grad(H1) + complement;
applies separate smoothers to each. Standard multigrid fails on HCurl
because the curl kernel (gradient fields) is not handled properly.

## 31. Maxwell Eigenvalue: Gradient Projection Required (i-tutorials unit-2.4)

The curl-curl eigenvalue problem has spurious zero eigenvalues from gradient
fields. Must project them out before PINVIT/LOBPCG:

```python
# Build gradient projection
gradmat, fesh1 = fes.CreateGradient()
gradmattrans = gradmat.CreateTranspose()
math1 = gradmattrans @ m.mat @ gradmat
math1[0,0] += 1  # Pin one DOF
invh1 = math1.Inverse(inverse="sparsecholesky")

# Projected preconditioner
proj = IdentityMatrix() - gradmat @ invh1 @ gradmattrans @ m.mat
projpre = proj @ pre.mat

# Solve
evals, evecs = solvers.PINVIT(a.mat, m.mat, pre=projpre, num=12, maxit=20)
```

**Why**: Without projection, PINVIT returns many spurious near-zero
eigenvalues (gradient modes) mixed with physical modes.

## 32. Symmetric COO Export Gives Half Matrix (i-tutorials unit-1.6)

```python
# WRONG - only upper triangle when symmetric=True
a = BilinearForm(fes, symmetric=True)
a.Assemble()
rows, cols, vals = a.mat.COO()  # Half the entries!

# CORRECT - reconstruct full matrix
import scipy.sparse as sp
A = sp.csr_matrix((vals, (rows, cols)), shape=(ndof, ndof))
A = A + A.T - sp.diags(A.diagonal())  # Symmetrize
```

**Rule**: When using `a.mat.COO()` with `symmetric=True`, the result is
only the upper triangle. You must explicitly symmetrize.

## 33. Periodic BC: Need >1 Element in Periodic Direction (i-tutorials unit-4.4)

```python
# WRONG - only 1 element in periodic direction -> singular system
mesh = Mesh(geo.GenerateMesh(maxh=0.6))  # maxh too large for thin domain

# CORRECT - ensure at least 2 elements
mesh = Mesh(geo.GenerateMesh(maxh=0.3))  # Small enough for 2+ layers
```

**Rule**: Periodic boundary conditions require at least 2 elements in the
periodic direction. If maxh is larger than half the domain width, the mesh
may have only 1 element and the periodic identification fails silently.

## 34. VectorH1 for Electromagnetic Fields (i-tutorials unit-2.3)

```python
# WRONG for electromagnetic fields
fes = VectorH1(mesh, order=2)  # All components C^0 continuous

# CORRECT
fes = HCurl(mesh, order=2)  # Tangential continuity only (E, A fields)
fes = HDiv(mesh, order=2)   # Normal continuity only (B, J fields)
```

**Why**: VectorH1 enforces full vector continuity across elements. EM fields
only have tangential (HCurl) or normal (HDiv) continuity at material
interfaces. VectorH1 introduces spurious constraint and wrong interface
conditions.

## 35. Surface-Only Mesh Generation (i-tutorials unit-11.1)

For BEM, you need a surface mesh without volume elements:

```python
from netgen.meshing import MeshingStep

# Surface mesh only (no tetrahedra)
mesh = Mesh(geo.GenerateMesh(maxh=0.5,
            perfstepsend=MeshingStep.MESHSURFACE))
mesh.Curve(2)  # Curved for accuracy
```

**Pitfall**: Using `geo.GenerateMesh(maxh=0.5)` without `perfstepsend`
creates a full volume mesh. BEM operators then see both volume and surface
elements, leading to incorrect results or excessive memory usage.
"""

NGSOLVE_LINALG = """
# Linear Algebra in NGSolve

## Vector Operations

```python
# Create from GridFunction
vu = gfu.vec
help_vec = vu.CreateVector()

# CRITICAL: Use .data for assignment
help_vec.data = 3 * vu              # Scalar multiply
help_vec.data += mat * vu            # Matrix-vector multiply
help_vec.data = 3 * u1 + 4 * u2     # Linear combination

# Inner product
ip = InnerProduct(help_vec, vu)

# Norm
from ngsolve import Norm
n = Norm(vu)
```

## NumPy Interop

```python
import numpy as np

# GridFunction -> NumPy (shared memory!)
arr = gfu.vec.FV().NumPy()

# Modify in-place
arr[:] = np.sin(np.linspace(0, 1, len(arr)))

# Sparse matrix -> NumPy
rows, cols, vals = a.mat.COO()
import scipy.sparse as sp
A_sp = sp.csr_matrix((vals, (rows, cols)))
```

## Block Matrices

```python
# Create block system from product space
fes = fesA * fesB
a = BilinearForm(fes)
# ... assemble ...

# Access blocks (0-indexed)
A00 = a.mat[0,0]   # Block (0,0)
A01 = a.mat[0,1]   # Block (0,1)

# Block preconditioner
pre = BlockMatrix([[inv_A, None],
                   [None, inv_S]])  # Schur complement
```

## GridFunction Operations

```python
gfu = GridFunction(fes)

# Set from CoefficientFunction
gfu.Set(sin(x)*cos(y))

# Evaluate at point
val = gfu(mesh(0.5, 0.5, 0.5))

# Integrate
integral = Integrate(gfu, mesh)
L2_err = sqrt(Integrate((gfu - exact)**2, mesh))

# Differentiate
grad_gfu = grad(gfu)       # H1
curl_gfu = curl(gfu)       # HCurl
div_gfu = div(gfu)         # HDiv
```
"""


NGSOLVE_EM_FORMULATIONS = """
# Electromagnetic Formulations in NGSolve

Reference implementations from EMPY_Analysis (K. Sugahara).

## Formulation Summary

| Formulation | Primary Unknown | FE Space | Domain | Application |
|-------------|-----------------|----------|--------|-------------|
| **A-1** | A (vector potential) | HCurl | Single | Magnetostatic |
| **A-2** | A | HCurl | Total + Reduced | Magnetostatic |
| **Omega-1** | Omega (scalar potential) | H1 | Single | Magnetostatic |
| **Omega-2** | Omega | H1 | Total + Reduced | Magnetostatic |
| **A-Omega** | A (total) + Omega (reduced) | HCurl * H1 | Hybrid | Magnetostatic |
| **A-Phi** | A + Phi (conductor) | HCurl * H1 | Total + Reduced | Eddy current |
| **T-Omega-1** | T (conductor) + Omega | HCurl * H1 | Single | Eddy current |
| **T-Omega-2** | T + Omega + Loop fields | HCurl * H1 + augmented | Total + Reduced | Eddy current (multiply connected) |

## Total/Reduced Domain Decomposition

Core pattern: split the domain into near-field (total) and far-field (reduced) regions.
The analytical source field (Biot-Savart) is subtracted in the reduced region, so FEM
solves only the material perturbation.

```python
# Geometry: iron + near-field air + far-field air
iron = Box(...).mat("iron")
total_air = Sphere(r=r_total) - iron
total_air.mat("A_domain")
reduced_air = Sphere(r=r_outer) - Sphere(r=r_total)
reduced_air.mat("Omega_domain")
geo = Glue([iron, total_air, reduced_air])

# Boundary naming
iron.faces.Min(X).name = "Bn0"      # B_n = 0 symmetry plane
iron.faces.Min(Z).name = "Ht0"      # H_t = 0 symmetry plane
```

## A-2 Formulation (Vector Potential, Two Regions)

```python
fesA = HCurl(mesh, order=feOrder, type1=True, nograds=True,
             dirichlet=Bn0_boundary)

# Bilinear form
a = BilinearForm(fesA)
a += 1/Mu * curl(A) * curl(N) * dx(total_region)
a += 1/Mu * curl(A) * curl(N) * dx(reduced_region)

# Dirichlet: set known source field on total-reduced boundary
gfA.Set(Av, BND, mesh.Boundaries(total_boundary))

# RHS: Dirichlet contribution + Neumann surface integral
f = LinearForm(fesA)
f += 1/Mu * curl(gfA) * curl(N) * dx(reduced_region)
f.Assemble()

# Isolate free DOFs (critical: zero out boundary DOFs)
fcut = np.array(f.vec.FV())[fesA.FreeDofs()]
np.array(f.vec.FV(), copy=False)[fesA.FreeDofs()] = fcut

# Add Neumann BC: tangential H continuity
f += Cross(N.Trace(), Hv) * normal * ds(total_boundary)
f.Assemble()
```

**Post-processing**: reconstruct full field from solved + source:
```python
BField = Bt + Br + Bs  # solved_total + solved_reduced + source(Biot-Savart)
```

## A-Omega Mixed Formulation (HCurl + H1 Hybrid)

Couples vector potential A in the total region with scalar potential Omega
in the reduced region via interface surface terms:

```python
fesA = HCurl(mesh, order=feOrder, type1=True, nograds=True,
             definedon=total_region, dirichlet=Bn0_boundary)
fesOmega = H1(mesh, order=feOrder, definedon=reduced_region,
              dirichlet=Ht0_boundary)
fes = fesA * fesOmega
(A, Omega), (N, o) = fes.TnT()

a = BilinearForm(fes)
a += 1/Mu * curl(A) * curl(N) * dx(total_region)
a += -Mu * grad(Omega) * grad(o) * dx(reduced_region)

# Interface coupling (saddle-point structure)
normal = specialcf.normal(mesh.dim)
a += -(Omega * (curl(N).Trace() * normal) +
       o * (curl(A).Trace() * normal)) * ds(total_boundary)

# RHS
f = LinearForm(fes)
f += -o * (Bv * normal) * ds(total_boundary)         # Normal B
f += Cross(N.Trace(), Hs) * normal * ds(total_boundary)  # Tangential H
```

**Note**: The A-Omega system is INDEFINITE (saddle-point). Use GMRES or MinRes,
not CG. Or use a custom solver (e.g., ICCG with augmented system).

## A-Phi Eddy Current Formulation

Product space HCurl * H1 where Phi is defined only in the conductor:

```python
fesA = HCurl(mesh, order=feOrder, type1=True, nograds=True,
             dirichlet=Bn0_boundary, complex=True)
fesPhi = H1(mesh, order=feOrder, definedon=conductive_region, complex=True)
fes = fesA * fesPhi
(A, phi), (N, psi) = fes.TnT()

s = 2j * pi * freq  # Complex frequency

a = BilinearForm(fes)
a += 1/Mu * curl(A) * curl(N) * dx
a += s * Sigma * (A + grad(phi)) * (N + grad(psi)) * dx(conductive_region)
```

**Current density**: `J = -s * Sigma * (A + grad(phi))`

**Joule loss** (complex):
```python
WJ = Integrate((J.real*J.real + J.imag*J.imag) / Sigma * dx(cond), mesh) / 2
```

## T-Omega Eddy Current Formulation

Electric vector potential T (conductor only) + magnetic scalar potential Omega:

```python
fesT = HCurl(mesh, order=feOrder, nograds=True,
             definedon="conductor", dirichlet="conductorBND", complex=True)
fesOmega = H1(mesh, order=feOrder, complex=True)
fes = fesT * fesOmega
(T, omega), (W, psi) = fes.TnT()

a = BilinearForm(fes)
a += Mu * grad(omega) * grad(psi) * dx("air")                        # air region
a += Mu * (T + grad(omega)) * (W + grad(psi)) * dx("conductor")      # conductor
a += 1/(s*Sigma) * curl(T) * curl(W) * dx("conductor")               # Faraday's law
```

**Physical fields**: `B = mu * (T + grad(Omega))`, `J = curl(T)`

**Impedance extraction**:
```python
R = Integrate(1/sigma * curl(gfT)**2 * dx("conductor"), mesh)
L = Integrate(mu * (gfT + grad(gfOmega) + loopField)**2 * dx, mesh)
Z = R + s * L
```

## Loop Fields for Multiply-Connected Conductors

For conductors with holes (T-Omega-2), topological loop fields must be computed:

```python
# 1. Compute surface genus from Euler characteristic
g = p - (nv - ne + nf) / 2  # genus = number of independent loops

# 2. For each loop: seed an edge DOF, solve curl-curl, project out gradients
for k in range(g):
    edge_dofs = fes.GetDofNrs(random_boundary_edge)
    gfu.vec[edge_dofs[0]] = 1
    fes.FreeDofs().__setitem__(edge_dofs[0], False)  # Fix DOF

    # Solve curl-curl in air region
    a = BilinearForm(curl(u) * curl(v) * dx("air"))

    # Helmholtz decomposition: subtract gradient part
    a_grad = BilinearForm(grad(phi) * grad(psi) * dx)
    f_grad = LinearForm(grad(psi) * gfu * dx)
    loop_field = gfu - grad(gfPhi)

    # Gram-Schmidt orthogonalization
    for prev_loop in loops:
        prod = Integrate(loop_field * prev_loop * dx, mesh)
        loop_field -= prod * prev_loop
```

**Circuit coupling**: Loop fields are coupled to the main system via
matrix augmentation (additional rows/columns for loop current amplitudes).

## Kelvin Transformation for Open Boundary

### Type 1: Inversion Kelvin Transform

Maps exterior domain via inversion through a sphere:

```python
# Geometry: identify outer sphere with Kelvin region
external_domain.faces[0].Identify(
    Omega_domain.faces[0], "kelvin", IdentificationType.PERIODIC)
fes = Periodic(fes)

# Modified bilinear form in Kelvin domain
rs = model.rKelvin
xs = 2 * rs  # center of inversion sphere
r = sqrt((x-xs)*(x-xs) + y*y + z*z)
fac = rs*rs / (r*r)

a += 1/(Mu*fac) * curl(A) * curl(N) * dx("Kelvin")       # A formulation
a += Mu * fac * grad(omega) * grad(psi) * dx("Kelvin")    # Omega formulation
```

### Type 2: Radial Scaling Kelvin Transform

Anisotropic permeability in a spherical shell (ra to rb):

```python
r = sqrt(x*x + y*y + z*z)
rvec = CF((x, y, z)) / r

# Radial vs tangential permeability
mut = Mu * (rb-ra) * ra / ((rb-r)*(rb-r))   # tangential
mun = Mu * (rb-ra) * ra / (r*r)             # normal

B = curl(A)
Bn = (B * rvec) * rvec          # normal component
Bt = B - Bn                      # tangential component

# CRITICAL: bonus_intorder=4 for accurate integration of varying coefficients
a += (1/mun * Bn*Nn + 1/mut * Bt*Nt) * dx("Kelvin", bonus_intorder=4)
```

## Ht Surface Regularization

Projects tangential H onto the surface to improve Neumann BC quality:

```python
normal = specialcf.normal(mesh.dim)
fes_reg = H1(mesh, order=feOrder, definedon=mesh.Boundaries(boundary))
u, v = fes_reg.TnT()

a = BilinearForm(fes_reg)
a += Cross(normal, grad(u).Trace()) * Cross(normal, grad(v).Trace()) * ds

f = LinearForm(fes_reg)
f += -H * Cross(normal, grad(v).Trace()) * ds

# Corrected tangential H
Ht_corrected = H + Cross(normal, grad(gfu).Trace())
```

This is a surface Hodge decomposition: finds scalar potential u such that
H + n x grad(u) is exactly tangential on the boundary.

## Flux Measurement Through Internal Faces

Uses gradient trick (divergence theorem) to measure flux without surface normals:

```python
class MeasureFace:
    def CalcFlux(self, field):
        # Create H1 function = 1 on face, 0 elsewhere (from one side)
        fes = H1(mesh, order=1, definedon=self.from_side, dirichlet=self.face)
        gf = GridFunction(fes)
        gf.Set(1, definedon=mesh.Boundaries(self.face))
        int1 = Integrate(field * grad(gf) * dx(self.from_side), mesh)

        # Same from other side
        fes = H1(mesh, order=1, definedon=self.to_side, dirichlet=self.face)
        gf = GridFunction(fes)
        gf.Set(1, definedon=mesh.Boundaries(self.face))
        int2 = Integrate(field * grad(gf) * dx(self.to_side), mesh)

        return (int1 - int2) / 2  # Average from both sides
```

Same technique works for current through cross-sections (impedance calculation).

## A Posteriori Error Estimation (ZZ-type)

Projects computed field onto a lower-order space; the difference is the error:

```python
# H-field error (for curl-curl formulations)
fesH = HCurl(mesh, order=feOrder-1, type1=True, nograds=True, definedon=region)
Hd = GridFunction(fesH)
Hd.Set(1/Mu * BField)
dH = 1/Mu * BField - Hd
err = Mu * dH * dH / 2
eta = Integrate(err, mesh, VOL, element_wise=True)

# B-field error (for scalar potential formulations)
fesBd = HDiv(mesh, order=feOrder-1, definedon=region)
Bd = GridFunction(fesBd)
Bd.Set(BField)
err = 1/Mu * (BField - Bd) * (BField - Bd)
eta = Integrate(err, mesh, VOL, element_wise=True)

# Adaptive refinement
maxerr = max(eta)
for el in mesh.Elements():
    mesh.SetRefinementFlag(el, eta[el.nr] > 0.25 * maxerr)
mesh.Refine()
mesh.Curve(curveOrder)
```

## CSR Matrix Extraction to External Solvers

```python
import scipy.sparse as sp

# Extract sparse matrix
asci = sp.csr_matrix(A.mat.CSR())

# Restrict to free DOFs (remove Dirichlet rows/columns)
free = list(fes.FreeDofs())
Acut = asci[np.ix_(free, free)]

# Extract RHS
fcut = np.array(f.vec.FV())[free]

# Solve with external solver (e.g., scipy, custom ICCG)
from scipy.sparse.linalg import spsolve
ucut = spsolve(Acut, fcut)

# Write solution back
np.array(gfu.vec.FV(), copy=False)[free] = ucut
```

## Quasi-2D with CloseSurfaces Identification

Reduce a 3D problem to 2D by identifying top/bottom faces:

```python
iron.faces.Min(Z).Identify(
    iron.faces.Max(Z), "bot-top", type=IdentificationType.CLOSESURFACES)

# Mesh with single element in z-direction
ngmesh = OCCGeometry(geo).GenerateMesh(maxh=0.1)
ngmesh.ZRefine("bot-top", [])  # No intermediate z-layers
mesh = Mesh(ngmesh).Curve(1)
```

## Key HCurl Flags for EM

```python
# type1=True: First-kind Nedelec elements (tangential continuity)
# nograds=True: Removes gradient DOFs (tree-cotree gauge for curl-curl)
# complex=True: Complex-valued space for eddy current (jw analysis)
# definedon=...: Region restriction (e.g., T only in conductor)

fesA = HCurl(mesh, order=2, type1=True, nograds=True,
             dirichlet="Bn0", complex=True)
```

## Material Properties as CoefficientFunction

```python
# Standard pattern: dictionary -> list ordered by mesh.GetMaterials()
mu_d = {"iron": mu0*mur, "A_domain": mu0, "Omega_domain": mu0,
        "Kelvin": mu0, 'default': mu0}
Mu = CoefficientFunction([mu_d[mat] for mat in mesh.GetMaterials()])

sigma_d = {"conductor": 5.8e7, "air": 0, 'default': 0}
Sigma = CoefficientFunction([sigma_d[mat] for mat in mesh.GetMaterials()])
```

## Boundary Condition Summary

| BC Name | Physical Meaning | Space | Method |
|---------|-----------------|-------|--------|
| **Bn=0** | Normal B = 0 (symmetry) | `HCurl(dirichlet="Bn0")` | Tangential A = 0 |
| **Ht=0** | Tangential H = 0 (symmetry) | `H1(dirichlet="Ht0")` | Omega = 0 |
| **n x H** | Tangential H continuity | Neumann | `Cross(N.Trace(), H) * n * ds` |
| **B . n** | Normal B continuity | Neumann | `(n * B) * psi * ds` |
| **Periodic** | Kelvin transform | `Periodic(fes)` | `Identify(PERIODIC)` |
| **CloseSurfaces** | Quasi-2D | `Identify(CLOSESURFACES)` | `ZRefine([])` |
"""

NGSOLVE_ADAPTIVE = """
# Adaptive Mesh Refinement in NGSolve for EM

## Error Estimation

### ZZ-type Estimator (Equilibrium Residual)

Project the computed field onto a lower-order conforming space.
The difference indicates inter-element discontinuity (error):

```python
# For A formulation: project H = (1/mu)*curl(A) into HCurl(order-1)
fesH = HCurl(mesh, order=feOrder-1, type1=True, nograds=True,
             definedon=total_region)
Hd = GridFunction(fesH, "Hprojected")
H = 1/Mu * curl(gfA)
Hd.Set(H)
dH = H - Hd

# Energy norm error indicator
err = Mu * dH * dH / 2
eta = Integrate(err, mesh, VOL, element_wise=True)

# For complex fields (eddy current):
err = Mu * (dH.real*dH.real + dH.imag*dH.imag) / 4
```

### For Scalar Potential: Project B into HDiv(order-1)

```python
fesBd = HDiv(mesh, order=feOrder-1, definedon=total_region)
Bd = GridFunction(fesBd, "Bprojected")
Bd.Set(BField)
err = 1/Mu * (BField - Bd) * (BField - Bd)
eta = Integrate(err, mesh, VOL, element_wise=True)
```

### Combined Error for Eddy Current (Flux + Current)

```python
# Flux error
eta_B = Integrate(Mu*dH*dH/2, mesh, VOL, element_wise=True)

# Current density error
fesJ = HDiv(mesh, order=feOrder-1, definedon=cond_region, complex=True)
Jd = GridFunction(fesJ)
Jd.Set(JField)
dJ = JField - Jd
eta_J = Integrate(1/(Sigma*omega) * (dJ.real*dJ.real + dJ.imag*dJ.imag)/2,
                  mesh, VOL, element_wise=True)

eta = eta_B + eta_J  # Combined error indicator
```

## Marking Strategy

Fixed-fraction marking (Doerfler-style):

```python
maxerr = max(eta)
errorRatio = 0.25  # Refine elements with error > 25% of max

for el in mesh.Elements():
    mesh.SetRefinementFlag(el, eta[el.nr] > errorRatio * maxerr)

mesh.Refine()
mesh.Curve(curveOrder)  # Re-curve after refinement!
```

## Adaptive Loop Pattern

```python
for level in range(max_levels):
    # 1. Create solver and solve
    solver = A_ReducedOmega_Method(model, coil, feOrder=feOrder)
    solver.Solve()

    # 2. Estimate error
    maxerr, eta = solver.CalcError()
    print(f"Level {level}: ndof={solver.fes.ndof}, maxerr={maxerr:.2e}")

    # 3. Check DOF limit
    if solver.fes.ndof > 1000000:
        break

    # 4. Refine and re-create solver
    solver.Refine(maxerr, eta, errorRatio=0.25)
```

**Key**: The solver object must be re-created after refinement because the
FE space changes. This is different from a simple `mesh.Refine()` loop.

## Kelvin Domain Error Scaling

Error indicators in the Kelvin-transformed region need Jacobian scaling:

```python
# Inside Kelvin region: scale by Jacobian factor
H_kelvin = 1/(Mu*fac) * curl(gfA)  # fac = rs^2/r^2
dH_kelvin = H_kelvin - Hd_kelvin
err_kelvin = Mu * fac * dH_kelvin * dH_kelvin / 2
eta_kelvin = Integrate(err_kelvin, mesh, VOL,
                       definedon=mesh.Materials("Kelvin"), element_wise=True)

eta_total = eta_inner + eta_kelvin
```
"""


def get_ngsolve_documentation(topic: str = "all") -> str:
    """Return NGSolve usage documentation by topic."""
    topics = {
        "overview": NGSOLVE_OVERVIEW,
        "spaces": NGSOLVE_FE_SPACES,
        "maxwell": NGSOLVE_MAXWELL,
        "solvers": NGSOLVE_SOLVERS,
        "preconditioners": NGSOLVE_PRECONDITIONERS,
        "bem": NGSOLVE_BEM,
        "mesh": NGSOLVE_MESH,
        "nonlinear": NGSOLVE_NONLINEAR,
        "pitfalls": NGSOLVE_PITFALLS,
        "linalg": NGSOLVE_LINALG,
        "formulations": NGSOLVE_EM_FORMULATIONS,
        "adaptive": NGSOLVE_ADAPTIVE,
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
