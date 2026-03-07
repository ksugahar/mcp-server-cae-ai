# mcp-server-cae-ai

[![PyPI version](https://badge.fury.io/py/mcp-server-cae-ai.svg)](https://pypi.org/project/mcp-server-cae-ai/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-cae-ai)](https://pypi.org/project/mcp-server-cae-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP (Model Context Protocol) servers for Computer-Aided Engineering (CAE) simulation workflows.

Provides AI coding assistants (Claude Code, Cursor, etc.) with domain knowledge for electromagnetic simulation, FEM/BEM analysis, and hex/tet meshing.

**Consolidated knowledge from Kindai University Sugahara Lab:**

- **Radia** (fork) -- BEM/PEEC magnetostatics, SIBC, FastHenry, coupled solver
- **NGSolve / ngbem** -- FEM spaces, Maxwell formulations, Kelvin transform, BEM operators
- **Coreform Cubit** -- Hex meshing, export workflows, Python scripting API
- **Cubit-to-Netgen** -- High-order curving, SetGeomInfo, name-based workflows
- **GMSH** -- Open-source meshing, OCC geometry, transfinite hex, Radia/NGSolve integration

## Installation

```bash
pip install mcp-server-cae-ai
```

Requires Python 3.10+. The only dependency is `mcp>=1.0.0`.

## Quick Start

### Claude Code

```bash
claude mcp add radia -- mcp-server-radia
claude mcp add cubit -- mcp-server-cubit
claude mcp add gmsh -- mcp-server-gmsh
```

### Project-level configuration (.mcp.json)

Add to your project root:

```json
{
  "mcpServers": {
    "radia": {
      "command": "mcp-server-radia"
    },
    "cubit": {
      "command": "mcp-server-cubit"
    },
    "gmsh": {
      "command": "mcp-server-gmsh"
    }
  }
}
```

### Verify

Inside Claude Code, run `/mcp` to confirm the servers are listed.

## Servers

### mcp-server-radia (8 tools, 21 lint rules)

Domain knowledge for [Radia](https://github.com/ksugahar/Radia) magnetostatics, NGSolve FEM, and ngbem BEM.

| Tool | Description |
|------|-------------|
| `lint_radia_script` | Lint a Python script for Radia/NGSolve violations |
| `lint_radia_directory` | Lint all scripts in a directory |
| `get_radia_lint_rules` | List all 21 lint rules with descriptions |
| `radia_usage` | Radia API docs (geometry, materials, PEEC, ngbem) |
| `ngsolve_usage` | NGSolve FEM guide (12 topics, 35 pitfalls) |
| `kelvin_transformation` | Kelvin transform for open boundary FEM |
| `sparsesolv_usage` | ngsolve-sparsesolv ICCG solver docs |
| `sparsesolv_code_example` | Ready-to-run solver examples |

### mcp-server-cubit (12 tools, 16 lint rules)

Domain knowledge for [Coreform Cubit](https://coreform.com/products/coreform-cubit/) meshing and Netgen high-order workflows.

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

### mcp-server-gmsh (8 tools, 14 lint rules)

Domain knowledge for [GMSH](https://gmsh.info/) open-source mesh generation.

| Tool | Description |
|------|-------------|
| `gmsh_docs` | GMSH API docs (35 topics: api, scripting, workflows) |
| `gmsh_code_example` | Ready-to-run GMSH examples (8 shapes/workflows) |
| `gmsh_script_template` | Customizable script templates (5 workflows) |
| `lint_gmsh_script` | Lint a GMSH Python script (14 rules) |
| `lint_gmsh_directory` | Lint all scripts in a directory |
| `get_gmsh_lint_rules` | List all 14 GMSH lint rules |
| `gmsh_element_types` | GMSH element type code reference |
| `gmsh_vs_cubit` | GMSH vs Cubit comparison guide |

## Knowledge Coverage

### Radia BEM/PEEC
- Geometry: hex/tet/wedge elements, ObjRecMag, ObjHexahedron, ObjTetrahedron
- Materials: linear (MatLin), nonlinear (B-H curve), permanent magnets
- Solvers: LU, BiCGSTAB, HACApK (H-matrix)
- Field computation, IMA symmetry, vector potential A
- PEEC: FastHenry parser, multi-filament skin effect, coupled PEEC+MMM
- SIBC: Bessel, Dowell, ESIM for nonlinear magnetic materials
- PRIMA model order reduction, SPICE circuit extraction

### NGSolve FEM (12 topics, 35 pitfalls)
- FE spaces: H1, HCurl, HDiv, L2
- Maxwell/magnetostatics formulations
- Solvers: PARDISO, UMFPACK, CG, GMRes
- Preconditioners: BDDC, AMG, multigrid
- Nonlinear Newton solver
- 35 documented pitfalls with code examples

### ngbem BEM
- LaplaceSL/DL, HelmholtzSL/DL operators
- FEM-BEM coupling
- Calderon preconditioner
- Loop-Star stabilized formulation (Weggler)

### EM Formulations
- A-formulation, Omega-formulation, A-Phi, T-Omega
- Total/reduced decomposition
- Kelvin transform for open boundary problems
- Loop fields, adaptive refinement

### Cubit Meshing
- Block registration, element order (1st/2nd)
- Hex/tet workflows, STEP exchange
- Mesh quality metrics and improvement
- 600+ Python API functions documented

### GMSH Meshing
- OCC kernel: primitives, booleans, STEP/IGES import
- Built-in kernel: bottom-up geometry (points, curves, surfaces)
- Mesh size fields (Distance, Threshold, Min, MathEval)
- Transfinite structured hex meshing
- Physical groups for material/boundary assignment
- Radia integration: gmsh_to_radia(), gmsh_surface_to_ngsolve()
- NGSolve integration: ReadGmsh, high-order curving

### Cubit-to-Netgen High-Order Curving
- SetGeomInfo API with UV parameter formulas
- Name-based OCC workflows (noheal import)
- Seam problem resolution
- Cylinder, sphere, torus, cone curving
- Tolerance tuning

## Testing

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run specific test suites
pytest tests/test_radia_rules.py -v    # 23 Radia rule tests
pytest tests/test_cubit_rules.py -v    # 16 Cubit rule tests
pytest tests/test_gmsh_rules.py -v     # 14 GMSH rule tests
pytest tests/test_selftest.py -v       # Selftest + fixture validation
```

### Self-Test

```bash
# From a project with examples/ directory
mcp-server-radia --selftest

# From anywhere (falls back to built-in test fixtures)
python -m mcp_server_cae_ai.radia.server --selftest
```

The `--selftest` flag lints the project's `examples/` directory when available.
When `examples/` is not found, it automatically uses built-in test fixtures
(`tests/fixtures/`) to validate all lint rules -- no external files needed.

See [docs/TESTING.md](docs/TESTING.md) for details.

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for:
- Adding new lint rules
- Adding knowledge topics
- Severity guidelines
- Architecture notes

## Release

New versions are automatically published to PyPI via GitHub Actions when a release is created.

## Related Projects

- [Radia](https://github.com/ksugahar/Radia) -- 3D Magnetostatics with NGSolve Integration
- [Coreform Cubit Mesh Export](https://github.com/ksugahar/Coreform_Cubit_Mesh_Export) -- Cubit-to-Netgen mesh pipeline
- [NGSolve](https://ngsolve.org/) -- High-performance FEM library
- [ngbem](https://github.com/nickrestrepo/ngbem) -- NGSolve BEM extension

## License

MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Kengo Sugahara, Kindai University
