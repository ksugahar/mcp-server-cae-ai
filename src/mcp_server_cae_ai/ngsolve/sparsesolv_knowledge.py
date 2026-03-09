"""
ngsolve-sparsesolv knowledge base for Radia MCP server.

Repository: https://github.com/ksugahar/ngsolve-sparsesolv
Version: 2.4.0
License: MPL 2.0
Based on: JP-MARs/SparseSolv

This module provides reference documentation for the ngsolve-sparsesolv library,
a standalone pybind11 extension module that provides iterative solvers and
preconditioners as an add-on to NGSolve.
"""

SPARSESOLV_OVERVIEW = """
# ngsolve-sparsesolv

## What It Is

ngsolve-sparsesolv is a **standalone pybind11 extension module** that provides
iterative solvers and preconditioners as an **add-on to NGSolve**. It is NOT
a fork or patch of NGSolve itself -- it is an independent library that links
against NGSolve at build time and produces a single `sparsesolv_ngsolve.pyd`
(Windows) or `.so` (Linux/macOS) file.

**Key distinction from NGSolve built-in solvers:**

| Aspect               | NGSolve Built-in           | ngsolve-sparsesolv                    |
|----------------------|----------------------------|---------------------------------------|
| Installation         | Comes with NGSolve         | Separate `pip install` or CMake build |
| IC preconditioner    | Not available              | IC with auto-shift, diagonal scaling  |
| BDDC                 | Substructuring-based       | Element Schur complement + sparse coarse solver |
| SGS preconditioner   | Not as standalone          | Standalone SGS and SGS-MRTR           |
| Complex support      | Via built-in solvers       | Conjugate/unconjugate inner product   |
| Parallel tri-solve   | Not available for IC       | ABMC ordering + level scheduling      |
| Localized IC         | Not available              | Partition-level parallel IC (Fukuhara)|
| Custom DOF ordering  | Not available              | Morton Z-order curve, RCM, etc.       |
| Divergence detection | Not available              | Stagnation-based early termination    |

**Positioning:** Complements NGSolve's built-in direct/iterative solvers with
specialized preconditioners (IC, SGS, BDDC) and convergence controls not
available in the base NGSolve distribution.

Repository: https://github.com/ksugahar/ngsolve-sparsesolv
Based on: JP-MARs/SparseSolv (https://github.com/JP-MARs/SparseSolv)

## Architecture

- **Header-only C++17 core**: `include/sparsesolv/` (no separate .cpp compilation)
- **pybind11 Python bindings**: Single extension module `sparsesolv_ngsolve`
- **NGSolve integration**: Links against NGSolve's `SparseMatrix`, `BaseVector`,
  `BitArray`, `BilinearForm`, `FESpace` for seamless interop
- **Parallel backend**: Compile-time dispatch to NGSolve TaskManager, OpenMP, or serial

## Solver Methods

| Method   | Description                                      | Best For                        |
|----------|--------------------------------------------------|---------------------------------|
| ICCG     | CG + Incomplete Cholesky preconditioning         | SPD and semi-definite systems   |
| SGSMRTR  | Min. Residual Truncated + Symmetric Gauss-Seidel | When IC factorization fails     |
| CG       | Conjugate Gradient (no preconditioning)          | Well-conditioned SPD systems    |
| COCR     | Conjugate Orth. Conjugate Residual (C++ native)  | Complex-symmetric (A^T=A)       |
| GMRES    | NGSolve GMResSolver (external)                   | Non-symmetric preconditioners   |

## Preconditioners

| Preconditioner | Description                                                       |
|----------------|-------------------------------------------------------------------|
| IC             | Incomplete Cholesky with auto-shift for semi-definite systems     |
| SGS            | Symmetric Gauss-Seidel, factorization-free                        |
| BDDC           | Balancing Domain Decomposition by Constraints (block elimination) |
| HYPRE AMS      | Auxiliary-space Maxwell Solver for HCurl eddy current (via HYPRE) |
| BoomerAMG      | HYPRE BoomerAMG for H1 scalar elliptic systems                    |

## Key Features

- **Add-on to NGSolve**: Independent module, no NGSolve source modification needed
- Auto-shift IC decomposition for semi-definite matrices (curl-curl problems)
- Complex-valued system support (auto-dispatch real/complex)
- Conjugate inner product switch for Hermitian vs complex-symmetric systems
- Best-iterate tracking (returns best solution even if not fully converged)
- Divergence/stagnation detection with early termination
- FreeDofs (Dirichlet boundary condition) support
- Parallel triangular solves via level scheduling or ABMC ordering
- ABMC (Algebraic Block Multi-Color) ordering for enhanced parallel triangular solves
- RCM (Reverse Cuthill-McKee) bandwidth reduction preprocessing for ABMC
- Localized IC (Fukuhara 2009): partition-level independent IC for full parallelism
- Custom DOF ordering (Morton Z-order curve) for improved localized IC partitioning
- BDDC preconditioner with element-by-element assembly (2 iterations typical)
"""

SPARSESOLV_API = """
# Python API Reference

## Import

```python
# Standalone add-on module (recommended)
from sparsesolv_ngsolve import (
    SparseSolvSolver,      # All-in-one solver factory
    ICPreconditioner,      # IC preconditioner for use with NGSolve CGSolver
    SGSPreconditioner,     # SGS preconditioner for use with NGSolve CGSolver
    BDDCPreconditioner,    # BDDC preconditioner (element-by-element)
    SparseSolvResult,      # Result container

    # HYPRE AMS (HCurl eddy current)
    HypreAMSPreconditioner,              # Real HYPRE AMS
    ComplexHypreAMSPreconditioner,       # Complex Re/Im TaskManager parallel
    HypreBoomerAMGPreconditioner,        # H1 AMG
    has_hypre,                           # HYPRE availability check

    COCRSolver,            # COCR for complex-symmetric (C++ native)
)
```

Note: `import ngsolve` must be called before `import sparsesolv_ngsolve`
to ensure NGSolve shared libraries are loaded first.

## SparseSolvSolver

Factory function that auto-detects real/complex from mat.IsComplex().

### Constructor

```python
solver = SparseSolvSolver(
    mat,                          # NGSolve SparseMatrix (required)
    method="ICCG",                # "ICCG", "SGSMRTR", or "CG"
    freedofs=None,                # BitArray for Dirichlet BCs (optional)
    tol=1e-10,                    # Relative convergence tolerance
    maxiter=1000,                 # Maximum iterations
    shift=1.05,                   # IC preconditioner shift parameter
    save_best_result=True,        # Track best solution during iteration
    save_residual_history=False,  # Record residual at each iteration
    printrates=False,             # Print convergence info
    conjugate=False,              # True for Hermitian, False for complex-symmetric
    use_abmc=False,               # Enable ABMC ordering for parallel triangular solves
    abmc_block_size=4,            # Rows per block in ABMC aggregation
    abmc_num_colors=4,            # Target number of colors for ABMC coloring
    abmc_use_rcm=False,           # RCM bandwidth reduction before ABMC
    abmc_block_ic=False,          # Localized IC (partition-level parallel IC)
    block_ic_num_partitions=0     # Partitions for localized IC (0=auto)
)
```

### Properties (read/write)

| Property              | Type  | Default  | Description                              |
|-----------------------|-------|----------|------------------------------------------|
| method                | str   | "ICCG"   | Solver method                            |
| tol                   | float | 1e-10    | Relative tolerance                       |
| maxiter               | int   | 1000     | Maximum iterations                       |
| shift                 | float | 1.05     | IC shift parameter                       |
| save_best_result      | bool  | True     | Track best solution                      |
| save_residual_history | bool  | False    | Record residual history                  |
| auto_shift            | bool  | False    | Auto-adjust for semi-definite systems    |
| diagonal_scaling      | bool  | False    | Enable 1/sqrt(A[i,i]) scaling            |
| divergence_check      | bool  | False    | Stagnation-based early termination       |
| divergence_threshold  | float | 1000.0   | Stagnation detection multiplier          |
| conjugate             | bool  | False    | Conjugated inner product (Hermitian)     |
| divergence_count      | int   | 100      | Bad iterations before stopping           |
| printrates            | bool  | False    | Print convergence info                   |
| use_abmc              | bool  | False    | ABMC ordering for parallel tri. solves   |
| abmc_block_size       | int   | 4        | Rows per block in ABMC aggregation       |
| abmc_num_colors       | int   | 4        | Target colors for ABMC graph coloring    |
| abmc_use_rcm          | bool  | False    | RCM bandwidth reduction before ABMC      |
| abmc_block_ic         | bool  | False    | Localized IC (partition-level parallel)   |
| block_ic_num_partitions| int  | 0        | Partitions for localized IC (0=auto)     |

### Methods

```python
# Set custom DOF ordering for localized IC partitioning
# ordering[old_dof] = new_position (list of int, length = ndof)
solver.set_custom_ordering(ordering)
```

### Usage

```python
# Operator interface (zero initial guess)
gfu.vec.data = solver * f.vec

# Solve with initial guess
result = solver.Solve(f.vec, gfu.vec)

# Check result
result = solver.last_result  # SparseSolvResult
print(result.converged, result.iterations, result.final_residual)
```

## ICPreconditioner

```python
pre = ICPreconditioner(mat, freedofs=None, shift=1.05)
pre.set_custom_ordering(ordering)  # Optional: custom DOF reordering
pre.Update()  # Must call to compute factorization

# Use with NGSolve CGSolver
from ngsolve.krylovspace import CGSolver
inv = CGSolver(a.mat, pre, tol=1e-10, maxiter=2000)
gfu.vec.data = inv * f.vec
```

## SGSPreconditioner

```python
pre = SGSPreconditioner(mat, freedofs=None)
pre.Update()  # Must call to set up preconditioner

# Use with NGSolve CGSolver
inv = CGSolver(a.mat, pre, tol=1e-10)
gfu.vec.data = inv * f.vec
```

## BDDCPreconditioner

BDDC extracts element matrices from a BilinearForm and builds a block-
elimination BDDC preconditioner. Requires the BilinearForm (not just the
assembled matrix) because it needs element-level information.

```python
pre = BDDCPreconditioner(a, fes)
pre.Update()

# Properties (read-only)
print(pre.num_wirebasket_dofs)  # Number of wirebasket (vertex/edge) DOFs
print(pre.num_interface_dofs)   # Number of interface DOFs per subdomain

# Use with NGSolve CGSolver
inv = CGSolver(a.mat, pre, tol=1e-10, maxiter=100)
gfu.vec.data = inv * f.vec
```

Parameters:
- `a`: Assembled BilinearForm (required)
- `fes`: FESpace (required, used to determine DOF classification)

### BDDC Performance Characteristics

| Problem Type     | SparseSolv BDDC | NGSolve BDDC | IC+CG   |
|------------------|-----------------|--------------|---------|
| Poisson (H1)     | 2 iterations    | ~19 iters    | ~40-200 |
| Elasticity (H1)  | 2 iterations    | ~19 iters    | ~80-400 |
| Eddy current     | 2 iterations    | ~19 iters    | ~100+   |

SparseSolv BDDC achieves ~2 iterations through element-by-element Schur
complement (dense LU on small per-element matrices) with MKL PARDISO for the
wirebasket coarse solve. The BDDC implementation is NGSolve-independent -- if
you have NGSolve, use NGSolve's own BDDC instead.
Requires Intel MKL (build prerequisite).
Practical limit: ~5000 interface DOFs per subdomain.

## SparseSolvResult

```python
result.converged          # bool
result.iterations         # int
result.final_residual     # float
result.residual_history   # list[float] (if save_residual_history=True)
```
"""

SPARSESOLV_EXAMPLES = """
# Usage Examples

## 1. Basic Poisson Problem with ICCG

```python
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

solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-10, maxiter=2000)

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec
print(f"ICCG: {solver.last_result.iterations} iterations")
```

## 2. Auto-Shift for Curl-Curl (Electromagnetic) Problems

```python
from netgen.occ import Box, Pnt

box = Box(Pnt(0, 0, 0), Pnt(1, 1, 1))
for face in box.faces:
    face.name = "outer"
mesh = box.GenerateMesh(maxh=0.4)

fes = HCurl(mesh, order=1, dirichlet="outer", nograds=True)
u, v = fes.TnT()

a = BilinearForm(fes)
a += curl(u) * curl(v) * dx
a.Assemble()

f = LinearForm(fes)
f += CF((0, 0, 1)) * v * dx
f.Assemble()

solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-8, maxiter=2000, shift=1.0)
solver.auto_shift = True         # Critical for semi-definite curl-curl
solver.diagonal_scaling = True

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec
assert solver.last_result.converged
```

## 3. Complex Eddy Current Problem (Complex-Symmetric)

```python
fes = HCurl(mesh, order=1, complex=True, dirichlet="outer", nograds=True)
u, v = fes.TnT()

a = BilinearForm(fes)
a += InnerProduct(curl(u), curl(v)) * dx
a += 1j * InnerProduct(u, v) * dx    # complex-symmetric (A^T = A)
a.Assemble()

f = LinearForm(fes)
f += InnerProduct(CF((1, 0, 0)), v) * dx
f.Assemble()

# Complex-symmetric: conjugate=False (default)
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-8, maxiter=5000,
                           save_best_result=True)
gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec
```

## 3b. Hermitian System (conjugate=True)

```python
# Real-coefficient problem in complex FE space => Hermitian (A^H = A)
fes = H1(mesh, order=2, complex=True, dirichlet="bottom|right|top|left")
u, v = fes.TnT()

a = BilinearForm(fes)
a += grad(u) * grad(v) * dx + u * v * dx  # real coefficients => Hermitian
a.Assemble()

# Hermitian: use conjugate=True (conjugated inner product a^H * b)
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-10, conjugate=True)
gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec
```

## 4. Divergence Detection

```python
solver = SparseSolvSolver(a.mat, method="CG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-12, maxiter=5000)
solver.divergence_check = True
solver.divergence_threshold = 10.0
solver.divergence_count = 20

result = solver.Solve(f.vec, gfu.vec)
# Early termination if stagnating
```

## 5. IC Preconditioner with NGSolve CGSolver

```python
from ngsolve.krylovspace import CGSolver
from sparsesolv_ngsolve import ICPreconditioner

pre = ICPreconditioner(a.mat, freedofs=fes.FreeDofs(), shift=1.05)
pre.Update()
inv = CGSolver(a.mat, pre, printrates=True, tol=1e-10, maxiter=2000)
gfu.vec.data = inv * f.vec
```

## 6. Residual History Recording

```python
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-10, maxiter=2000,
                           save_residual_history=True)
result = solver.Solve(f.vec, gfu.vec)
print(f"History: {len(result.residual_history)} entries")
# Plot: plt.semilogy(result.residual_history)
```

## 7. ABMC Ordering for Parallel Triangular Solves

```python
# Enable ABMC ordering in IC preconditioner
# Beneficial for problems with >25,000 DOFs and multi-threaded execution
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-10, maxiter=2000,
                           use_abmc=True,
                           abmc_block_size=4,
                           abmc_num_colors=4)

# Also works with auto-shift and diagonal scaling
solver.auto_shift = True
solver.diagonal_scaling = True

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec
```

## 8. Localized IC (Partition-Level Parallel IC)

```python
# Localized IC: each partition performs IC factorization independently.
# Fully parallel setup and apply with no barriers.
# Based on Fukuhara et al. (2009).
solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-10, maxiter=2000,
                           abmc_block_ic=True,
                           block_ic_num_partitions=4)
solver.diagonal_scaling = True

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec
```

## 9. Localized IC with Morton Z-Order Curve Ordering

```python
import numpy as np

def compute_dof_coordinates(mesh, fes):
    # Compute spatial coordinate for each DOF (average of element centroids).
    ndof = fes.ndof
    coords = np.zeros((ndof, 3))
    counts = np.zeros(ndof, dtype=int)
    for el in mesh.Elements(VOL):
        verts = [mesh[v].point for v in el.vertices]
        centroid = np.mean(verts, axis=0)
        for d in fes.GetDofNrs(el):
            if d >= 0:
                coords[d] += centroid
                counts[d] += 1
    mask = counts > 0
    coords[mask] /= counts[mask, np.newaxis]
    return coords

def morton_encode(x, y, z):
    # Interleave bits of 21-bit integers (x, y, z) to form 63-bit Morton code.
    def spread(v):
        v = int(v) & 0x1fffff
        v = (v | (v << 32)) & 0x1f00000000ffff
        v = (v | (v << 16)) & 0x1f0000ff0000ff
        v = (v | (v << 8))  & 0x100f00f00f00f00f
        v = (v | (v << 4))  & 0x10c30c30c30c30c3
        v = (v | (v << 2))  & 0x1249249249249249
        return v
    return spread(x) | (spread(y) << 1) | (spread(z) << 2)

def compute_morton_ordering(mesh, fes):
    # Return ordering[old_dof] = new_position based on Morton Z-order curve.
    coords = compute_dof_coordinates(mesh, fes)
    ndof = len(coords)
    bbox_min = coords.min(axis=0)
    bbox_max = coords.max(axis=0)
    span = bbox_max - bbox_min
    span[span == 0] = 1.0
    max_val = (1 << 21) - 1
    q = ((coords - bbox_min) / span * max_val).astype(np.int64)
    q = np.clip(q, 0, max_val)
    codes = np.array([morton_encode(q[i, 0], q[i, 1], q[i, 2]) for i in range(ndof)])
    sorted_indices = np.argsort(codes)
    ordering = np.empty(ndof, dtype=np.int32)
    ordering[sorted_indices] = np.arange(ndof, dtype=np.int32)
    return ordering.tolist()

# Compute ordering and pass to solver
morton_ord = compute_morton_ordering(mesh, fes)

solver = SparseSolvSolver(a.mat, method="ICCG",
                           freedofs=fes.FreeDofs(),
                           tol=1e-10, maxiter=2000,
                           abmc_block_ic=True,
                           block_ic_num_partitions=4)
solver.diagonal_scaling = True
solver.set_custom_ordering(morton_ord)

gfu = GridFunction(fes)
gfu.vec.data = solver * f.vec
```

Morton Z-order curve reorders DOFs so spatially nearby DOFs get consecutive
indices. This dramatically reduces cross-partition entries (e.g., from 54% to
4% at P=4 for H1 problems), improving localized IC quality.

## 10. BDDC Preconditioner

```python
from sparsesolv_ngsolve import BDDCPreconditioner
from ngsolve.krylovspace import CGSolver

# BDDC requires BilinearForm (not just the matrix)
a = BilinearForm(fes)
a += grad(u) * grad(v) * dx
a.Assemble()

# Create BDDC preconditioner from BilinearForm + FESpace
pre = BDDCPreconditioner(a, fes)
pre.Update()

# Typically converges in ~2 CG iterations
inv = CGSolver(a.mat, pre, tol=1e-10, maxiter=100, printrates=True)

gfu = GridFunction(fes)
f = LinearForm(fes)
f += 1 * v * dx
f.Assemble()
gfu.vec.data = inv * f.vec
```
"""

SPARSESOLV_ABMC = """
# ABMC Ordering: Parallel Triangular Solve Optimization

## Overview

ABMC (Algebraic Block Multi-Color) ordering enables parallel forward/backward
substitution in IC and SGS preconditioners. Without ABMC, triangular solves
are inherently sequential -- the main bottleneck for multi-threaded IC/SGS.

Algorithm (Iwashita, Nakashima, Takahashi, IPDPS 2012):
1. **BFS Aggregation**: Groups nearby rows into blocks of ~block_size rows
2. **Graph Coloring**: Colors the block adjacency graph so blocks of the same
   color have no data dependencies
3. **Parallel Execution**: Colors processed sequentially, blocks within each
   color processed in parallel

## When to Use ABMC

| DOFs     | Threads | ABMC Benefit    |
|----------|---------|-----------------|
| <10,000  | Any     | No benefit      |
| 10K-25K  | 4-8     | Marginal        |
| >25,000  | 4+      | 1.2-1.8x faster |
| >100,000 | 8+      | Significant     |

**Crossover point**: ~25,000 DOFs with 8 threads. Below this, the overhead of
reordering exceeds the parallelism benefit.

## Performance Benchmarks (8 threads)

| Problem                      | DOFs    | Without ABMC | With ABMC | Speedup |
|------------------------------|---------|--------------|-----------|---------|
| Poisson (unit cube, H1 p=2) | 186,219 | 111 ms/iter  | 87 ms     | 1.28x   |
| Toroidal coil (HCurl p=1)   | 148,439 | 145 ms/iter  | 81 ms     | 1.80x   |

The toroidal coil shows higher speedup because HCurl mesh topology creates
longer dependency chains that benefit more from multi-color parallelism.

## Configuration Parameters

| Parameter            | Default | Description                                  |
|----------------------|---------|----------------------------------------------|
| use_abmc             | False   | Enable ABMC ordering                         |
| abmc_block_size      | 4       | Rows per block (2-16 typical)                |
| abmc_num_colors      | 4       | Target colors (actual may be higher)         |
| abmc_reorder_spmv    | False   | Also reorder SpMV (usually slower)           |
| abmc_use_rcm         | False   | RCM bandwidth reduction before ABMC          |
| abmc_block_ic        | False   | Localized IC (partition-level parallel IC)   |
| block_ic_num_partitions | 0    | Partitions for localized IC (0=auto)         |

## RCM Preprocessing

RCM (Reverse Cuthill-McKee) bandwidth reduction is available via `abmc_use_rcm=True`.
It reorders the matrix to reduce bandwidth before ABMC coloring, improving cache
locality for both SpMV and triangular solves.

## Localized IC (Fukuhara 2009)

Localized IC (`abmc_block_ic=True`) divides the matrix into P contiguous row
partitions, each performing IC factorization independently (ignoring inter-partition
connections). This enables fully parallel Setup and Apply with no synchronization
barriers.

**Key trade-off**: More partitions = more parallelism but worse preconditioner
quality (more cross-partition fill ignored).

**DOF ordering matters**: Netgen's default DOF numbering has poor spatial locality.
Use `set_custom_ordering()` with Morton Z-order curve or RCM (`abmc_use_rcm=True`)
to ensure spatially nearby DOFs are contiguous, minimizing cross-partition entries.

| Ordering      | Cross-partition (P=4) | Iteration ratio |
|---------------|-----------------------|-----------------|
| Naive (Netgen)| ~54%                  | ~1.5x           |
| RCM           | ~10%                  | ~1.2x           |
| Morton Z-curve| ~4%                   | ~1.1-1.2x       |

## Known Limitations

- `abmc_num_colors` is a lower bound; the actual number of colors depends on
  the graph structure and may be higher for complex meshes
- `abmc_reorder_spmv=False` (default) is usually faster because FEM mesh
  ordering has better cache locality for SpMV than ABMC ordering
- Localized IC quality degrades for HCurl problems due to wider stencils and
  imprecise edge DOF coordinate estimation

## Implementation Details

The ABMC pipeline in the IC preconditioner:
1. **Setup phase** (once): Build ABMCSchedule, reorder L factor, pre-allocate work vectors
2. **Apply phase** (each iteration): Permute input -> parallel triangular solve -> unpermute output

Parallel execution uses a **persistent parallel region** with SpinBarrier
synchronization (one `parallel_for(nthreads, ...)` call with barriers between
color levels), avoiding per-level thread dispatch overhead.
"""

SPARSESOLV_BEST_PRACTICES = """
# Best Practices and Recommendations

## Preconditioner Selection Guide

| Problem Type                    | Recommended                  | Why                              |
|---------------------------------|------------------------------|----------------------------------|
| H1 Poisson/Elasticity (small)  | IC (shift=1.05)              | Fast, reliable                   |
| H1 Poisson/Elasticity (large)  | BDDC                         | Mesh-independent convergence     |
| HCurl curl-curl (semi-definite)| IC + auto_shift              | Handles kernel automatically     |
| HCurl eddy current (small)     | BDDC+CG (conjugate=False)    | Symmetric preconditioner, memory efficient |
| HCurl eddy current (large p=1) | **HYPRE AMS+GMRES**          | Stable iteration count at scale (75 it @ 1.44M DOFs) |
| Large parallel (H1)            | Localized IC + Morton        | Full parallelism, low overhead   |
| Large parallel (HCurl, p>=3)   | ABMC                         | Better scaling than BDDC at p>=3 |
| Any problem, IC fails          | SGS-MRTR                     | No factorization needed          |

## Complex-Valued Problems: conjugate Setting

This is the most common source of confusion:

- **Complex-symmetric** (A^T = A): `conjugate=False` (default)
  - Examples: eddy current with `1j * sigma * u * v * dx`
  - Inner product: a^T * b (unconjugated)

- **Hermitian** (A^H = A): `conjugate=True`
  - Examples: real-coefficient problem assembled in complex FE space
  - Inner product: a^H * b (conjugated)

Using the wrong setting causes divergence or extremely slow convergence
(e.g., 5000 iterations instead of 58).

## Curl-Curl (HCurl) Problems

1. **Always use `nograds=True`**: Fewer DOFs, better conditioned
2. **Source construction matters**: `int_coil J.v dx` (domain integral) may not
   be discretely div-free, causing IC convergence failure
3. **Safe source approaches**:
   - curl-based: `int T.curl(v) dx`
   - Helmholtz correction: Remove gradient component via Laplacian solve
   - HDiv projection: Mixed FEM to enforce div=0
4. **Eddy current**: The `sigma * u * v * dx` term naturally regularizes

## Shift Parameter for IC

- Default `shift=1.05` works for most SPD problems
- For semi-definite (curl-curl): use `auto_shift=True` with `shift=1.0`
- Higher shift = more stable but slower convergence
- `diagonal_scaling=True` often helps for poorly scaled matrices

## ABMC Ordering

- Only enable for >25K DOFs with multi-threaded execution
- Default `abmc_block_size=4, abmc_num_colors=4` works well for most cases
- Keep `abmc_reorder_spmv=False` (default) for better SpMV cache locality
- Consider `abmc_use_rcm=True` for bandwidth reduction

## Localized IC (Block IC)

- Enable with `abmc_block_ic=True, block_ic_num_partitions=P`
- Fully parallel setup and apply — no synchronization barriers
- **Critical**: Use `set_custom_ordering()` with Morton Z-order curve for best
  partition quality. Without spatial reordering, cross-partition ratio is ~54%
  (P=4), causing ~1.5x iteration increase. With Morton ordering, drops to ~4%.
- Works well for H1 problems (P=2-4: ~1.1-1.2x iteration ratio)
- Less effective for HCurl due to wider stencils
- ABMC (use_abmc) generally outperforms localized IC at p>=3

## BDDC Preconditioner

- Best for h-refinement studies: iteration count stays constant (~2)
- Requires `BilinearForm` (not just assembled matrix) for element extraction
- Memory-intensive for large interface DOF counts (>5000 per subdomain)
- Coarse solver: MKL PARDISO (direct, no options needed)
- NGSolve-independent: BDDC core + MKL PARDISO, no NGSolve solver dependency
- If you have NGSolve, use NGSolve's own BDDC instead
- Requires Intel MKL (build prerequisite)
"""

SPARSESOLV_BUILD = """
# Build & Installation Instructions

## Requirements

- CMake 3.16+
- C++17 compiler (MSVC 2022, GCC 10+, Clang 10+)
- Intel MKL (required for BDDC coarse solver via PARDISO)
- NGSolve installed (from source or pip) with CMake config files
- pybind11 (fetched automatically by CMake if not found)

## Step 1: Clone and Build

```bash
git clone https://github.com/ksugahar/ngsolve-sparsesolv.git
cd ngsolve-sparsesolv
mkdir build && cd build

cmake .. -DSPARSESOLV_BUILD_NGSOLVE=ON \\
         -DNGSOLVE_INSTALL_DIR=/path/to/ngsolve/install/cmake
cmake --build . --config Release
```

Produces: `sparsesolv_ngsolve.pyd` (Windows) or `.so` (Linux/macOS)

## Step 2: Install to Python Path

```bash
# Find NGSolve site-packages
SITE_PACKAGES=$(python -c "import ngsolve, pathlib; print(pathlib.Path(ngsolve.__file__).parent.parent)")

# Create package directory and copy
mkdir -p "$SITE_PACKAGES/sparsesolv_ngsolve"
cp build/Release/sparsesolv_ngsolve*.pyd "$SITE_PACKAGES/sparsesolv_ngsolve/"   # Windows
# cp build/sparsesolv_ngsolve*.so "$SITE_PACKAGES/sparsesolv_ngsolve/"          # Linux/macOS
echo "from .sparsesolv_ngsolve import *" > "$SITE_PACKAGES/sparsesolv_ngsolve/__init__.py"
```

## Step 3: Verify

```bash
python -c "import ngsolve; from sparsesolv_ngsolve import SparseSolvSolver; print('OK')"
```

Note: `import ngsolve` must be called before `import sparsesolv_ngsolve` to load
NGSolve shared libraries first.

## Alternative: pip install (from source)

```bash
pip install git+https://github.com/ksugahar/ngsolve-sparsesolv.git
```

Requires NGSolve to be discoverable by CMake.
"""


SPARSESOLV_EXAMPLE_POISSON = '''# 2D Poisson Problem with ICCG
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

SPARSESOLV_EXAMPLE_CURLCURL = '''# 3D Curl-Curl (Electromagnetic) with Auto-Shift ICCG
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

SPARSESOLV_EXAMPLE_EDDY = '''# Complex Eddy Current Problem
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

SPARSESOLV_EXAMPLE_PRECOND = '''# Using IC/SGS Preconditioners with NGSolve CGSolver
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

SPARSESOLV_EXAMPLE_DIVERGENCE = '''# Divergence Detection and Early Termination
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

SPARSESOLV_EXAMPLE_BDDC = '''# BDDC Preconditioner with CG (mesh-independent convergence)
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

SPARSESOLV_HYPRE_AMS = """
# HYPRE AMS Preconditioner (HCurl Eddy Current)

## Overview

HYPRE AMS (Auxiliary-space Maxwell Solver) is a preconditioner for HCurl
finite element curl-curl + mass systems, from the HYPRE library (Lawrence
Livermore National Laboratory). SparseSolv wraps HYPRE AMS as an NGSolve
BaseMatrix and provides ComplexHypreAMSPreconditioner for complex eddy
current problems with TaskManager Re/Im parallelism.

**When to use**: Large-scale HCurl p=1 eddy current problems (>100K DOFs).
For small/medium problems, BDDC+CG is competitive and uses less memory.

## Theory: AMS Helmholtz Decomposition

HCurl space has the Helmholtz decomposition: u = grad(phi) + z
where phi in H1 and z in curl-free complement.

AMS exploits this decomposition via two auxiliary spaces:
1. **G correction** (gradient): discrete gradient G maps H1 -> HCurl.
   H1 scalar AMG (BoomerAMG) solves grad(phi) component.
2. **Pi correction** (Nedelec interpolation): Pi = [diag(x)*G, diag(y)*G, diag(z)*G]
   maps vertex coordinates to HCurl. Vector H1 AMG solves z component.
3. **HCurl smoother**: l1-Jacobi or hybrid GS on HCurl space.

These are combined as a multiplicative V-cycle:
cycle_type=1: relax -> Pi -> G -> Pi -> relax

## Why HYPRE AMS + GMRES for Complex Eddy Current

HYPRE AMS uses hybrid Gauss-Seidel (relax_type=3) internally, making the
preconditioner **non-symmetric**. Therefore **GMRES is required** (not CG).

Why hybrid GS + GMRES is optimal (not l1-Jacobi + CG):
- Hybrid GS: GS within processor + Jacobi between = best smoothing + parallelism
- Fewer iterations compensate for GMRES memory overhead (Krylov basis storage)
- For complex eddy current with Re/Im splitting, preconditioner quality
  (= iteration count) dominates total performance

Symmetric smoothers (l1-Jacobi, Chebyshev) would allow CG, but at the cost
of more iterations. Currently these options are not exposed via Python API.

## Re/Im Splitting for Complex Systems

Complex system (K + jw*sigma*M) * x = b is handled by:
1. Build real SPD auxiliary matrix: A_real = K + eps*M + |omega|*sigma*M_cond
2. Create TWO independent HYPRE AMS instances (thread-safe)
3. Apply: y_re = AMS(x_re), y_im = AMS(x_im) in parallel via TaskManager

ComplexHypreAMSPreconditioner uses ParallelFor(2, ...) for ~1.5x speedup.

## Benchmark Results (GMRES, tol=1e-8)

Hiruma eddy current (Cu coil + Fe core, f=50Hz, 8 threads):

| Mesh  | DOFs  | Python sequential | C++ TaskManager  | Speedup  |
|-------|------:|------------------:|-----------------:|---------:|
| 2.5T  | 155k  | 5.40s, 50 it      | **3.43s, 50 it** | **1.57x** |
| 5.5T  | 331k  | 14.98s, 59 it     | **10.19s, 59 it**| **1.47x** |
| 20.5T | 1.44M | 103.09s, 75 it    | **69.16s, 75 it**| **1.49x** |

Iteration counts are identical -- same math, only parallelism differs.

## Solver Comparison: ABMC ICCG vs BDDC vs HYPRE AMS

| Aspect           | ABMC ICCG      | BDDC           | HYPRE AMS+GMRES    |
|------------------|----------------|----------------|---------------------|
| Target           | General SPD    | General (high-order) | HCurl eddy current |
| Structure used   | None (algebraic) | Element wirebasket | Helmholtz decomp   |
| Symmetry         | Symmetric      | Symmetric      | **Non-symmetric**   |
| Krylov solver    | CG / COCR      | CG / COCR      | **GMRES only**      |
| Memory           | **Best** (IC+CG=5 vecs) | Medium | **Largest** (GMRES basis + AMG) |
| Setup cost       | Low            | High           | Medium              |
| Iteration scaling| h-dependent    | h-independent  | h-quasi-independent |

**Key trade-off**: HYPRE AMS uses more memory than ABMC ICCG (GMRES stores
m Krylov vectors vs CG's 5), but provides stable iteration counts at scale.
At 1.44M DOFs: HYPRE AMS = 75 iterations, Custom AMS = 394 iterations.

## Python API

```python
import sparsesolv_ngsolve as ssn

# Check HYPRE availability
if not ssn.has_hypre():
    raise RuntimeError("HYPRE not available")

# Real HYPRE AMS (for real SPD HCurl systems)
pre_real = ssn.HypreAMSPreconditioner(
    mat=a_real.mat,                # SparseMatrix<double>
    grad_mat=G_mat,                # Discrete gradient (fes.CreateGradient())
    freedofs=fes_real.FreeDofs(),   # Dirichlet mask
    coord_x=cx, coord_y=cy, coord_z=cz,  # Vertex coordinates
    cycle_type=1,                  # 1=additive (default)
    print_level=0)

# Complex HYPRE AMS with TaskManager Re/Im parallelism
pre_complex = ssn.ComplexHypreAMSPreconditioner(
    a_real_mat=a_real.mat,         # Real SPD auxiliary matrix
    grad_mat=G_mat,
    freedofs=fes_real.FreeDofs(),
    coord_x=cx, coord_y=cy, coord_z=cz,
    ndof_complex=fes.ndof,         # Complex DOF count
    cycle_type=1,
    print_level=0)

# MUST use GMResSolver (HYPRE AMS is non-symmetric)
from ngsolve.krylovspace import GMResSolver
with TaskManager():
    inv = GMResSolver(mat=a.mat, pre=pre_complex, maxiter=500, tol=1e-8)
    gfu.vec.data = inv * f.vec

# BoomerAMG for H1 (e.g., thermal, Poisson)
pre_h1 = ssn.HypreBoomerAMGPreconditioner(
    mat=a_h1.mat,
    freedofs=fes_h1.FreeDofs(),
    relax_type=6,                  # 6=symmetric GS (CG-safe)
    print_level=0)
```

## COCR Solver (Complex-Symmetric)

For complex-symmetric systems (A^T = A) with a symmetric preconditioner,
COCR (Sogabe-Zhang 2007) is optimal: short recurrence, minimizes ||A*r||.

```python
# COCR with IC preconditioner
inv = ssn.COCRSolver(a.mat, pre_ic, maxiter=500, tol=1e-8)
gfu.vec.data = inv * f.vec

# Or via SparseSolvSolver dispatch
solver = ssn.SparseSolvSolver(a.mat, method="COCR",
    freedofs=fes.FreeDofs(), tol=1e-10, maxiter=1000)
```

Note: COCR uses non-conjugated inner product (x^T y, not x^H y).
For Hermitian systems, use CGSolver(conjugate=True) instead.
"""

SPARSESOLV_EXAMPLE_HYPRE_AMS = '''# HYPRE AMS for Complex Eddy Current
# ComplexHypreAMSPreconditioner + GMResSolver (TaskManager parallel Re/Im)
from ngsolve import *
import sparsesolv_ngsolve as ssn
from ngsolve.krylovspace import GMResSolver

# Check HYPRE availability
assert ssn.has_hypre(), "Build with SPARSESOLV_USE_HYPRE=ON"

# --- Problem setup (simplified eddy current) ---
from netgen.occ import Box, Pnt
box = Box(Pnt(0,0,0), Pnt(1,1,1))
for f in box.faces: f.name = "outer"
mesh = Mesh(box.GenerateMesh(maxh=0.15))

omega = 2 * 3.14159265 * 50  # 50 Hz
sigma = 5.96e7  # Cu conductivity
nu = 1.0  # 1/mu_0 (simplified)

# Complex HCurl space
fes = HCurl(mesh, order=1, nograds=True, dirichlet="outer", complex=True)
u, v = fes.TnT()
a = BilinearForm(fes)
a += nu * curl(u) * curl(v) * dx
a += 1j * omega * sigma * u * v * dx
a.Assemble()

f_vec = LinearForm(fes)
f_vec += CF((0, 0, 1)) * v * dx
f_vec.Assemble()

# --- Real auxiliary matrix for HYPRE AMS ---
fes_real = HCurl(mesh, order=1, nograds=True, dirichlet="outer", complex=False)
u_r, v_r = fes_real.TnT()
a_real = BilinearForm(fes_real)
a_real += nu * curl(u_r) * curl(v_r) * dx
a_real += 1e-6 * nu * u_r * v_r * dx           # regularization
a_real += abs(omega) * sigma * u_r * v_r * dx   # eddy current
a_real.Assemble()

# --- Discrete gradient + vertex coordinates ---
G_mat, h1_fes = fes_real.CreateGradient()
nv = mesh.nv
cx, cy, cz = [0.0]*nv, [0.0]*nv, [0.0]*nv
for i in range(nv):
    pt = mesh.ngmesh.Points()[i + 1]  # 1-indexed
    cx[i], cy[i], cz[i] = pt[0], pt[1], pt[2]

# --- ComplexHypreAMSPreconditioner ---
pre = ssn.ComplexHypreAMSPreconditioner(
    a_real_mat=a_real.mat, grad_mat=G_mat,
    freedofs=fes_real.FreeDofs(),
    coord_x=cx, coord_y=cy, coord_z=cz,
    ndof_complex=fes.ndof, cycle_type=1, print_level=1)

# --- Solve with GMRES (HYPRE AMS is non-symmetric -> GMRES required) ---
gfu = GridFunction(fes)
with TaskManager():
    inv = GMResSolver(mat=a.mat, pre=pre, maxiter=500, tol=1e-8, printrates=True)
    gfu.vec.data = inv * f_vec.vec

print(f"GMRES converged in {inv.GetSteps()} iterations")
'''


def get_full_documentation() -> str:
    """Return complete ngsolve-sparsesolv documentation."""
    return "\n\n".join([
        SPARSESOLV_OVERVIEW,
        SPARSESOLV_API,
        SPARSESOLV_EXAMPLES,
        SPARSESOLV_ABMC,
        SPARSESOLV_HYPRE_AMS,
        SPARSESOLV_BEST_PRACTICES,
        SPARSESOLV_BUILD,
    ])


def get_sparsesolv_documentation(topic: str = "all") -> str:
    """Return sparsesolv documentation by topic, including code examples."""
    topics = {
        "overview": SPARSESOLV_OVERVIEW,
        "api": SPARSESOLV_API,
        "examples": SPARSESOLV_EXAMPLES,
        "abmc": SPARSESOLV_ABMC,
        "best_practices": SPARSESOLV_BEST_PRACTICES,
        "build": SPARSESOLV_BUILD,
        "example_poisson": SPARSESOLV_EXAMPLE_POISSON,
        "example_curlcurl": SPARSESOLV_EXAMPLE_CURLCURL,
        "example_eddy": SPARSESOLV_EXAMPLE_EDDY,
        "example_precond": SPARSESOLV_EXAMPLE_PRECOND,
        "example_divergence": SPARSESOLV_EXAMPLE_DIVERGENCE,
        "example_bddc": SPARSESOLV_EXAMPLE_BDDC,
        "hypre_ams": SPARSESOLV_HYPRE_AMS,
        "example_hypre_ams": SPARSESOLV_EXAMPLE_HYPRE_AMS,
    }
    topic = topic.lower().strip()
    if topic in ("best-practices", "bestpractices", "tips"):
        topic = "best_practices"
    if topic == "all":
        return get_full_documentation()
    elif topic in topics:
        return topics[topic]
    else:
        return (
            f"Unknown topic: '{topic}'. "
            f"Available: {', '.join(topics.keys())}"
        )
