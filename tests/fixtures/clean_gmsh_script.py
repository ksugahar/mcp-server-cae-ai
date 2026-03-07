"""Clean GMSH script that should trigger zero lint rule findings."""

import gmsh

gmsh.initialize()
gmsh.model.add("clean_model")

gmsh.model.occ.addBox(0, 0, 0, 0.1, 0.1, 0.1)
gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(3, [1], 1)
gmsh.model.setPhysicalName(3, 1, "domain")

gmsh.model.mesh.generate(3)
gmsh.write("clean_output.msh")

gmsh.finalize()
