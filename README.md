# mcp-server-cae-ai

MCP (Model Context Protocol) servers for Computer-Aided Engineering (CAE) simulation workflows.

Provides AI coding assistants (Claude Code, etc.) with domain knowledge for electromagnetic simulation, FEM/BEM analysis, and hex/tet meshing.

**Consolidated knowledge from Kindai University Sugahara Lab:**

- **Radia** (fork) -- BEM/PEEC magnetostatics, SIBC, FastHenry, coupled solver
- **NGSolve / ngbem** -- FEM spaces, Maxwell formulations, Kelvin transform, BEM operators
- **Coreform Cubit** -- Hex meshing, export workflows, Python scripting API
- **Cubit-to-Netgen** -- High-order curving, SetGeomInfo, name-based workflows

## Installation

```bash
pip install mcp-server-cae-ai
```

## Registration with Claude Code

```bash
claude mcp add radia -- mcp-server-radia
claude mcp add cubit -- mcp-server-cubit
```

Or add to your project's `.mcp.json`:

```json
{
  "radia": {
    "command": "mcp-server-radia"
  },
  "cubit": {
    "command": "mcp-server-cubit"
  }
}
```

## Servers

### mcp-server-radia (8 tools, 21 lint rules)

| Tool | Description |
|------|-------------|
| `lint_radia_script` | Lint a Python script for Radia/NGSolve violations |
| `lint_radia_directory` | Lint all scripts in a directory |
| `get_radia_lint_rules` | List all 21 lint rules |
| `radia_usage` | Radia API docs (geometry, materials, PEEC, ngbem) |
| `ngsolve_usage` | NGSolve FEM guide (12 topics, 35 pitfalls) |
| `kelvin_transformation` | Kelvin transform for open boundary FEM |
| `sparsesolv_usage` | ngsolve-sparsesolv ICCG solver docs |
| `sparsesolv_code_example` | Ready-to-run solver examples |

### mcp-server-cubit (12 tools, 16 lint rules)

| Tool | Description |
|------|-------------|
| `cubit_export_docs` | Export format documentation (Gmsh, VTK, Netgen, Exodus) |
| `netgen_workflow_guide` | Cubit-to-Netgen curving workflows |
| `netgen_code_example` | Ready-to-run Netgen examples |
| `cubit_scripting_guide` | Cubit Python scripting patterns |
| `cubit_forum_tips` | Real-world tips from Cubit forums |
| `cubit_api_reference` | 600+ Cubit API functions |
| `lint_cubit_script` | Lint a Cubit Python script |
| `lint_cubit_directory` | Lint all scripts in a directory |
| `generate_cubit_script` | Generate template scripts |
| `mesh_quality_guide` | Mesh quality checking & improvement |
| `get_lint_rules` | List all 16 Cubit lint rules |
| `troubleshooting_guide` | Debugging guidance |

## Knowledge Coverage

- **Radia BEM**: Geometry (hex/tet/wedge), materials (linear/nonlinear/PM), solvers (LU/BiCGSTAB/HACApK), field computation, IMA symmetry
- **PEEC**: FastHenry parser, multi-filament skin effect, coupled PEEC+MMM, SIBC (Bessel/Dowell/ESIM), PRIMA model order reduction
- **NGSolve FEM**: FE spaces (H1/HCurl/HDiv/L2), Maxwell/magnetostatics, solvers (PARDISO/UMFPACK/CG/GMRes), BDDC/AMG preconditioners, Newton nonlinear, 35 pitfalls
- **ngbem BEM**: LaplaceSL/DL, HelmholtzSL/DL, FEM-BEM coupling, Calderon preconditioner, Loop-Star stabilized formulation
- **EM Formulations**: A-1/A-2/Omega/A-Omega/A-Phi/T-Omega, total/reduced decomposition, Kelvin transform, loop fields, adaptive refinement
- **Cubit Meshing**: Block registration, element order, hex/tet workflows, STEP exchange, mesh quality
- **Cubit-to-Netgen**: SetGeomInfo API, name-based OCC workflows, seam problem resolution, 2nd-order curving, tolerance tuning

## Self-Test

```bash
# Run from a project directory that has examples/
mcp-server-radia --selftest
mcp-server-cubit --selftest
```

## Related Projects

- [Radia](https://github.com/ksugahar/Radia) -- 3D Magnetostatics with NGSolve Integration
- [Coreform Cubit Mesh Export](https://github.com/ksugahar/Coreform_Cubit_Mesh_Export) -- Cubit-to-Netgen mesh pipeline
- [NGSolve](https://ngsolve.org/) -- High-performance FEM library

## License

MIT
