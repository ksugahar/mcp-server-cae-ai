"""Intentionally bad GMSH script for lint testing.

This file triggers multiple lint rules:
- missing-gmsh-initialize (imports gmsh but no initialize)
- missing-gmsh-finalize (no finalize)
- missing-synchronize (generate without sync)
- missing-physical-groups (write without physical groups)
- missing-model-add (no model.add)
- hardcoded-absolute-path
- write-without-generate (write without generate - but this one won't fire
  because generate IS present, just without sync)
- gmsh-unicode-print
"""

import gmsh
import sys

sys.path.insert(0, r'D:\myproject\lib')

gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.1, 0.1)
gmsh.model.mesh.generate(3)
gmsh.write("output.msh")
print("Result: 5 m\u00b2")
