"""
GmshBuilder knowledge base for the Radia MCP server.

Covers the GmshBuilder high-level mesh generation API: geometry creation,
boolean operations, transforms, mesh control, generation, quality, access,
physical groups, export, entity wrappers, geometry analysis, groups,
post-processing, options, recipes, and best practices.
"""

GMSH_BUILDER_OVERVIEW = """
# GmshBuilder Overview

GmshBuilder is a high-level mesh generation API that wraps GMSH's OCC
(OpenCASCADE) kernel. It provides ~719 methods across 16 modules for
geometry creation, boolean operations, mesh control, and export.

## Import

```python
from radia.gmsh_builder import GmshBuilder
```

Requires: `pip install gmsh`

## Must Use as Context Manager

```python
with GmshBuilder(model_name='my_model', verbose=True) as gb:
    box = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_mesh_size(0.005)
    gb.generate()
    gb.export('output.msh')
```

The context manager handles GMSH initialize/finalize automatically.

## All Coordinates in Meters

Consistent with Radia's unit system. All lengths passed to GmshBuilder
methods are in meters.

## Core Workflow

```
1. Create geometry    -> add_box, add_cylinder, import_step, ...
2. Boolean operations -> fuse, cut, fragment, webcut, ...
3. Mesh control       -> set_mesh_size, set_divisions, fields, ...
4. Generate mesh      -> generate(), generate_hex(), ...
5. Export / to Radia   -> export(), to_radia(), to_ngsolve_mesh(), ...
```

## Quick Start Example

```python
from radia.gmsh_builder import GmshBuilder
import radia as rad

rad.UtiDelAll()

with GmshBuilder(verbose=False) as gb:
    # Create geometry
    box = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])

    # Mesh control
    gb.set_mesh_size(0.005)

    # Generate tetrahedral mesh
    gb.generate()

    # Export to file
    gb.export('iron_core.msh')

    # Or convert directly to Radia objects
    container = gb.to_radia(mu_r=1000)

# Use Radia for field computation
B = rad.Fld(container, 'b', [0, 0, 0.05])
rad.UtiDelAll()
```

## Module List (16 modules, ~707 methods)

| Module | Public Methods | Description |
|--------|---------------|-------------|
| core.py | 14 | Initialization, context manager, volume registry |
| geometry.py | 80 | Solid primitives, sweeps, low-level entities, import |
| boolean_ops.py | 29 | Fuse, cut, intersect, fragment, webcut |
| transforms.py | 26 | Translate, rotate, mirror, scale, arrays |
| mesh_control.py | 76 | Size, divisions, transfinite, boundary layer, fields |
| mesh_generate.py | 48 | Generate, refine, optimize, embed, topology |
| mesh_quality.py | 27 | Quality metrics, histograms, optimization |
| mesh_access.py | 75 | Node/element access, Jacobians, numpy export |
| physical_groups.py | 64 | Blocks, sidesets, nodesets, materials |
| query.py | 74 | Bounding box, center, surfaces, adjacency |
| export.py | 30 | MSH, VTK, STEP, STL, Radia, NGSolve, PyVista |
| entity_wrappers.py | 55 | Volume/surface/curve/vertex property queries |
| geometry_analysis.py | 35 | Heal, defeature, topology checks, curvature |
| groups.py | 30 | Selection groups, set operations |
| post_processing.py | 25 | Views, scalar/vector/tensor data |
| options.py | 20 | GMSH global settings |
"""

GMSH_BUILDER_GEOMETRY = """
# Geometry Creation (geometry.py, 80 methods)

## Solid Primitives (17 methods)

| Method | Description |
|--------|-------------|
| `add_box(center, size)` | Box centered at point |
| `add_box_at(origin, size)` | Box with corner at origin |
| `add_cylinder(center, axis, radius, height)` | Cylinder along axis ('x'/'y'/'z') |
| `add_cylinder_vector(base, direction, radius)` | Cylinder along arbitrary vector |
| `add_cylinder_between(p1, p2, radius)` | Cylinder between two points |
| `add_sphere(center, radius)` | Sphere |
| `add_cone(center, axis, r1, r2, height)` | Cone/frustum along axis |
| `add_cone_vector(base, direction, r1, r2)` | Cone along arbitrary vector |
| `add_torus(center, R, r, axis='z')` | Torus (R=major, r=minor) |
| `add_wedge(corner, dx, dy, dz, ltx=0)` | Wedge/prism shape |
| `add_ellipsoid(center, radii)` | Ellipsoid [rx, ry, rz] |
| `add_half_space(point, normal)` | Semi-infinite half-space |
| `add_hollow_cylinder(center, axis, r_inner, r_outer, h)` | Hollow cylinder |
| `add_hollow_sphere(center, r_inner, r_outer)` | Hollow sphere |
| `add_c_shape(center, size, gap, thickness)` | C-shaped magnet yoke |
| `add_prism(base_points, height, axis='z')` | Extruded polygon |
| `add_volume(surfaces)` | Volume from bounding surfaces |

```python
with GmshBuilder(verbose=False) as gb:
    # Box: 100x20x30 mm iron core
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])

    # Cylinder: R=50mm, H=10mm along Z
    cyl = gb.add_cylinder([0, 0, 0], 'z', 0.05, 0.01)

    # C-shape magnet yoke
    yoke = gb.add_c_shape([0, 0, 0], [0.1, 0.08, 0.02],
                          gap=0.02, thickness=0.02)
```

## Pipe and Thick Solid (2 methods)

| Method | Description |
|--------|-------------|
| `add_pipe(wire, profile)` | Sweep profile along wire |
| `add_thick_solid(vol_id, thickness, ...)` | Thicken shell |

## Sweep / Loft / Revolve (13 methods)

| Method | Description |
|--------|-------------|
| `extrude(vol_id, dx, dy, dz, num_elements=None, heights=None, recombine=False)` | Extrude volume (structured with num_elements) |
| `extrude_surface(surf, dx, dy, dz, num_elements=None, heights=None, recombine=False)` | Extrude surface (structured with num_elements) |
| `revolve(vol_id, center, axis, angle, num_elements=None, heights=None, recombine=False)` | Revolve volume (structured with num_elements) |
| `revolve_surface(surf, center, axis, angle, num_elements=None, heights=None, recombine=False)` | Revolve surface (structured with num_elements) |
| `loft(profiles)` | Loft through cross-section profiles |
| `add_thru_sections(wire_tags)` | Through-sections (OCC ThruSections) |
| `add_general_pipe(wire, profile, ...)` | General pipe sweep |
| `extrude_rotate(vol_id, axis_point, axis_dir, angle, ...)` | Helical extrude |
| `extrude_along_wire(vol_id, wire)` | Extrude along curve |
| `extrude_with_twist(vol_id, direction, distance, twist_angle)` | Twisted extrude |
| `revolve_partial(vol_id, axis_point, axis_dir, angle)` | Partial revolve |
| `sweep_surface(surf, wire)` | Sweep surface along wire |
| `extrude_to_point(surf, point)` | Extrude surface to point (cone-like) |

## Low-Level Entities (18 methods)

| Method | Description |
|--------|-------------|
| `add_point(x, y, z, mesh_size=0)` | Point (returns tag) |
| `add_line(p1, p2)` | Line segment |
| `add_circle_arc(p1, center, p2)` | Circular arc through 3 points |
| `add_circular_arc(center, radius, angle1, angle2, ...)` | Arc by angles |
| `add_circle(center, radius, axis='z')` | Full circle |
| `add_full_ellipse(center, rx, ry, axis='z')` | Full ellipse |
| `add_ellipse_arc(p1, center, p2, p3)` | Ellipse arc |
| `add_spline(points)` | Spline through points |
| `add_bspline(points, ...)` | B-spline |
| `add_bezier(points)` | Bezier curve |
| `add_wire(curve_tags)` | Wire from curves |
| `add_curve_loop(curve_tags)` | Closed curve loop |
| `add_rectangle(center, dx, dy, ...)` | Rectangle surface |
| `add_disk(center, rx, ry=None)` | Disk/ellipse surface |
| `add_polygon(points)` | Polygon surface |
| `add_plane_surface(wire_tags)` | Planar surface from wires |
| `add_surface_filling(wire_tag)` | Surface filling (coons patch) |
| `add_surface_loop(surface_tags)` | Closed surface loop |

## Advanced Surfaces (6 methods)

| Method | Description |
|--------|-------------|
| `add_offset_curve(curve, offset, ...)` | Offset curve |
| `add_bspline_surface(points, ...)` | B-spline surface from control grid |
| `add_bspline_filling(wire, ...)` | B-spline surface filling |
| `add_bezier_surface(points, ...)` | Bezier surface |
| `add_bezier_filling(wire, ...)` | Bezier filling |
| `add_trimmed_surface(surface, wires)` | Trimmed surface |

## Geometry Modification (5 methods)

| Method | Description |
|--------|-------------|
| `fillet(vol_id, curve_tags, radii)` | Fillet edges |
| `chamfer(vol_id, curve_tags, distances)` | Chamfer edges |
| `heal_geometry(vol_id=None, ...)` | Heal geometry defects |
| `remove_small_edges(vol_id, tol)` | Remove small edges |
| `convert_to_nurbs(vol_id)` | Convert to NURBS |

## Import / Export (9 methods)

| Method | Description |
|--------|-------------|
| `import_step(filename)` | Import STEP file |
| `import_iges(filename)` | Import IGES file |
| `import_brep(filename)` | Import BRep file |
| `import_stl(filename)` | Import STL file |
| `import_mesh(filename)` | Import mesh file |
| `import_sat(filename)` | Import ACIS SAT file |
| `import_x_t(filename)` | Import Parasolid X_T file |
| `import_from_string(data, format)` | Import from string buffer |
| `export_iges(filename)` | Export IGES |

## Domain-Specific (6 methods)

| Method | Description |
|--------|-------------|
| `add_multi_box(centers, sizes)` | Multiple boxes at once |
| `add_coil_helix(center, radius, pitch, turns, ...)` | Helical coil |
| `add_sector(center, r_inner, r_outer, angle, h)` | Annular sector |
| `add_racetrack(center, straight, radius, height)` | Racetrack shape |
| `add_e_shape(center, size, ...)` | E-shaped core |
| `add_u_shape(center, size, ...)` | U-shaped core |

## Misc (1 method)

| Method | Description |
|--------|-------------|
| `copy_geometry(vol_id)` | Deep copy volume geometry |
"""

GMSH_BUILDER_BOOLEAN = """
# Boolean Operations (boolean_ops.py, 29 methods)

## Basic Boolean (5 methods)

| Method | Description |
|--------|-------------|
| `fuse(vol1, vol2)` | Union of two volumes |
| `cut(vol1, vol2)` | Subtract vol2 from vol1 |
| `intersect(vol1, vol2)` | Intersection of two volumes |
| `fragment(vol_ids)` | Fragment all volumes (shared interfaces) |
| `fragment_tracked(vol_ids)` | Fragment with mapping of old->new tags |

```python
with GmshBuilder(verbose=False) as gb:
    box1 = gb.add_box([0, 0, 0], [0.1, 0.1, 0.1])
    box2 = gb.add_box([0.05, 0, 0], [0.1, 0.1, 0.1])

    # Union
    result = gb.fuse(box1, box2)

    # Subtraction (cut box2 from box1)
    result = gb.cut(box1, box2)

    # Fragment for conformal mesh (shared interfaces)
    new_ids = gb.fragment([box1, box2])
```

## Extended Boolean (9 methods)

| Method | Description |
|--------|-------------|
| `cut_keep_tool(vol1, vol2)` | Cut but keep the tool volume |
| `fuse_keep(vol1, vol2)` | Fuse but keep originals |
| `subtract_list(target, tools)` | Subtract list of tools from target |
| `fuse_all(vol_ids)` | Fuse all volumes in list |
| `intersect_list(vol_ids)` | Intersect all volumes |
| `split_by_volume(vol1, vol2)` | Split vol1 using vol2 |
| `chop(vol_id, plane_point, plane_normal)` | Chop volume with plane |
| `separate_volumes(vol_id)` | Separate disconnected regions |
| `cut_with_plane(vol_id, point, normal)` | Cut with infinite plane |

## Webcut Operations (8 methods)

Webcut splits volumes into pieces for structured hex meshing.

| Method | Description |
|--------|-------------|
| `webcut_plane(vol_id, axis, position)` | Cut with axis-aligned plane |
| `webcut_cylinder(vol_id, center, axis, radius)` | Cut with cylinder |
| `webcut_sphere(vol_id, center, radius)` | Cut with sphere |
| `webcut_box(vol_id, box_min, box_max)` | Cut with box |
| `webcut_cone(vol_id, center, axis, r1, r2, h)` | Cut with cone |
| `webcut_torus(vol_id, center, R, r, axis)` | Cut with torus |
| `webcut_general(vol_id, tool_vol)` | Cut with arbitrary volume |
| `section(vol_id, surface)` | Section with surface |

```python
# Webcut for structured hex meshing
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])

    # Split into sub-volumes for structured hex
    gb.webcut_plane(core, 'x', 0.03)
    gb.webcut_plane(core, 'x', -0.03)

    # Set divisions and generate hex
    gb.set_divisions(5)
    gb.generate('hex')
    gb.export('structured_core.msh')
```

## Imprint / Merge / Remove (7 methods)

| Method | Description |
|--------|-------------|
| `imprint_and_merge(vol_ids)` | Imprint and merge coincident faces |
| `imprint_volumes(vol_ids)` | Imprint volumes (create shared faces) |
| `merge_volumes(vol_ids)` | Merge coincident entities |
| `remove_volume(vol_id)` | Remove a single volume |
| `remove_volumes(vol_ids)` | Remove multiple volumes |
| `remove_all_duplicates()` | Remove all duplicate entities |
| `keep_only(vol_ids)` | Remove all volumes except specified |
"""

GMSH_BUILDER_TRANSFORMS = """
# Transform Operations (transforms.py, 26 methods)

## Basic Transforms (11 methods)

| Method | Description |
|--------|-------------|
| `translate(vol_id, dx, dy, dz)` | Move volume by offset |
| `rotate(vol_id, center, axis, angle)` | Rotate (angle in radians) |
| `rotate_degrees(vol_id, center, axis, angle_deg)` | Rotate (angle in degrees) |
| `copy(vol_id)` | Copy volume in place |
| `mirror(vol_id, point, normal)` | Mirror across plane |
| `mirror_plane(vol_id, axis, position=0)` | Mirror across axis-aligned plane |
| `scale(vol_id, center, factor)` | Scale uniformly |
| `affine_transform(vol_id, matrix)` | General affine transform (4x4 matrix) |
| `translate_to(vol_id, target_point)` | Move center to target point |
| `center_at_origin(vol_id)` | Move center to origin |
| `align_to_axis(vol_id, direction, target_axis)` | Align direction to axis |

```python
with GmshBuilder(verbose=False) as gb:
    box = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])

    # Move 50mm in X
    gb.translate(box, 0.05, 0, 0)

    # Rotate 45 degrees around Z axis
    gb.rotate_degrees(box, [0, 0, 0], [0, 0, 1], 45)

    # Mirror across YZ plane
    gb.mirror_plane(box, 'x', 0)
```

## Copy-Transform (6 methods)

| Method | Description |
|--------|-------------|
| `copy_translate(vol_id, dx, dy, dz)` | Copy and translate |
| `copy_rotate(vol_id, center, axis, angle)` | Copy and rotate |
| `copy_mirror(vol_id, point, normal)` | Copy and mirror |
| `copy_scale(vol_id, center, factor)` | Copy and scale |
| `symmetrize(vol_id, axis, position=0)` | Create symmetric copy |
| `copy_all(vol_ids)` | Copy list of volumes |

## Array / Pattern (4 methods)

| Method | Description |
|--------|-------------|
| `array_linear(vol_id, direction, count, spacing)` | Linear array |
| `array_circular(vol_id, center, axis, count, angle=360)` | Circular array |
| `array_grid(vol_id, nx, ny, nz, spacing)` | 3D grid array |
| `array_along_curve(vol_id, curve, count)` | Array along curve |

```python
# Halbach array: 8 magnets in circular pattern
with GmshBuilder(verbose=False) as gb:
    mag = gb.add_box([0.05, 0, 0], [0.01, 0.01, 0.05])
    gb.array_circular(mag, [0, 0, 0], [0, 0, 1], 8)
```

## Bulk Transforms (5 methods)

| Method | Description |
|--------|-------------|
| `translate_all(vol_ids, dx, dy, dz)` | Translate multiple volumes |
| `rotate_all(vol_ids, center, axis, angle)` | Rotate multiple volumes |
| `mirror_all(vol_ids, point, normal)` | Mirror multiple volumes |
| `scale_all(vol_ids, center, factor)` | Scale multiple volumes |
| `swap_volumes(vol1, vol2)` | Swap two volume registrations |
"""

GMSH_BUILDER_MESH_CONTROL = """
# Mesh Control (mesh_control.py, 84 methods)

## Global Size / Division (10 methods)

| Method | Description |
|--------|-------------|
| `set_mesh_size(size)` | Global element size |
| `set_mesh_size_at(point, size, influence_radius)` | Size at point |
| `set_mesh_size_on_surface(vol_id, surf_idx, size)` | Size on surface |
| `set_mesh_size_on_curve(vol_id, curve_tag, size)` | Size on curve |
| `set_mesh_size_on_point(point_tag, size)` | Size on point |
| `set_mesh_size_factor(factor)` | Multiply all sizes by factor |
| `set_mesh_size_from_boundary(flag)` | Extend boundary sizes |
| `set_min_max_size(min_size, max_size)` | Min/max element size |
| `set_divisions(n)` | Number of divisions per edge (structured) |
| `set_divisions_all(n)` | Divisions on all curves |

```python
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])

    # Global size for tet mesh
    gb.set_mesh_size(0.005)

    # Or structured divisions for hex mesh
    gb.set_divisions(10)
```

## Element Order / Scheme (4 methods)

| Method | Description |
|--------|-------------|
| `set_order(order)` | Element order (1=linear, 2=quadratic) |
| `set_scheme(scheme)` | Meshing scheme string |
| `set_algorithm(algorithm)` | 2D/3D algorithm (e.g., 'Delaunay') |
| `set_algorithm_on_surface(surf, algorithm)` | Algorithm on specific surface |

## Curve Control (3 methods)

| Method | Description |
|--------|-------------|
| `set_curve_divisions(curve_tag, n)` | Divisions on specific curve |
| `set_bias(curve_tag, ratio)` | Single bias (grading) on curve |
| `set_double_bias(curve_tag, ratio)` | Double-sided bias |

## Transfinite (4 methods)

| Method | Description |
|--------|-------------|
| `set_transfinite_surface(surf_tag, ...)` | Structured quad surface |
| `set_transfinite_volume(vol_tag, ...)` | Structured hex volume |
| `set_transfinite_automatic(vol_id)` | Auto-detect transfinite |
| `set_transfinite_automatic_all()` | Auto-transfinite all volumes |

## Boundary Layer (1 method)

| Method | Description |
|--------|-------------|
| `set_boundary_layer(surface_tags, sizes, ratios, ...)` | Boundary layer mesh |

## Sizing Fields (~25 methods)

| Method | Description |
|--------|-------------|
| `add_field_distance(entities, ...)` | Distance-based sizing |
| `add_field_threshold(field_id, min_size, max_size, ...)` | Threshold on field |
| `add_field_box(xmin, xmax, ymin, ymax, zmin, zmax, ...)` | Box region sizing |
| `add_field_ball(center, radius, ...)` | Ball region sizing |
| `add_field_cylinder(p1, p2, radius, ...)` | Cylinder region sizing |
| `add_field_frustum(p1, p2, r1, r2, ...)` | Frustum region sizing |
| `add_field_math(expression)` | Math expression field |
| `add_field_min(field_ids)` | Minimum of fields |
| `add_field_max(field_ids)` | Maximum of fields |
| `add_field_mean(field_ids)` | Mean of fields |
| `add_field_restrict(field_id, entities)` | Restrict field to entities |
| `add_field_attractor(entities, ...)` | Attractor field |
| `add_field_laplacian(...)` | Laplacian-based sizing |
| `add_field_gradient(field_id)` | Gradient of field |
| `add_field_curvature_field(...)` | Curvature-based sizing |
| `add_field_octree(...)` | Octree-based sizing |
| `add_field_external_process(command, ...)` | External process field |
| `add_field_structured(filename, ...)` | Structured grid field |
| `add_field_post_view(view_tag, ...)` | Post-processing view field |
| `add_field_param(field_type, **params)` | Generic parametric field |
| `set_background_field(field_id)` | Set active background field |
| `remove_field(field_id)` | Remove a field |
| `remove_all_fields()` | Remove all fields |
| `get_field_count()` | Count active fields |
| `get_field_type(field_id)` | Get field type string |
| `get_field_list()` | List all field IDs |

```python
# Adaptive sizing: fine near gap, coarse elsewhere
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_min_max_size(0.001, 0.01)

    f1 = gb.add_field_box(-0.01, 0.01, -0.005, 0.005,
                          -0.005, 0.005, v_in=0.001, v_out=0.01)
    gb.set_background_field(f1)
    gb.generate()
```

## Optimization / Recombination (~11 methods)

| Method | Description |
|--------|-------------|
| `set_curvature_mesh(n_pts)` | Curvature-adapted mesh |
| `set_recombine(surf_tag, angle=45.0)` | Recombine triangles into quads (angle=max deviation from right angle) |
| `set_recombine_all()` | Recombine all surfaces |
| `set_recombination_algorithm(algo)` | Recombination algorithm (0=simple, 1=blossom, 2=full_quad, 3=blossom_full_quad) |
| `set_smoothing(n_steps)` | Laplacian smoothing steps |
| `set_optimization(method)` | Optimization method |
| `set_growth_rate(rate)` | Element growth rate |
| `set_angle_threshold(angle)` | Angle threshold for meshing |
| `set_subdivision_algorithm(algo)` | Subdivision method |
| `get_mesh_options()` | Get current mesh options dict |

## Compound / Misc (~8 methods)

| Method | Description |
|--------|-------------|
| `set_compound(vol_ids)` | Compound meshing region |
| `set_compound_surfaces(surf_tags)` | Compound surface meshing |
| `set_compound_curves(curve_tags)` | Compound curve meshing |
| `set_reverse_mesh(surf_tag)` | Reverse element orientation |
| `set_size_callback(func)` | Python callback for dynamic sizing |
| `remove_size_callback()` | Remove size callback |
| `set_algorithm_on_volume(vol_tag, algo)` | Algorithm on specific volume |

## CFD Convenience Methods (8 methods) -- NEW

| Method | Description |
|--------|-------------|
| `add_size_gradient(entity_tags, dim, lc_near, lc_far, dist_near, dist_far, set_as_background=True)` | Distance+Threshold in one step (most common CFD sizing) |
| `set_background_mesh_from_fields(field_tags, operator='min')` | Combine fields (Min/Max/Mean) and set as background |
| `set_field_numbers(field_tag, key, values)` | Set list-valued field parameter (setNumbers) |
| `add_boundary_layer_field(entity_tags, dim, lc_min, lc_max, dist_min, dist_max, ...)` | BoundaryLayer field for wall resolution |
| `add_field_auto_mesh_size()` | Automatic geometry-based sizing (GMSH>=4.11) |
| `set_mesh_size_at_points_direct(point_tags, size)` | Batch mesh size on multiple points |
| `add_wake_refinement(curve_tags, direction, length, lc_min, lc_max, width)` | Anisotropic wake refinement (airfoil/bluff body) |
| `add_terrain_field(filename, format='structured')` | Terrain/elevation data as sizing field |

```python
# CFD typical workflow: boundary layer + wake refinement
with GmshBuilder(verbose=False) as gb:
    airfoil = gb.add_box([0, 0, 0], [1.0, 0.1, 0.1])
    gb.synchronize()

    # Wall-normal grading (fine near wall, coarse far away)
    wall_curves = [1, 2, 3, 4]  # curves on airfoil surface
    f1 = gb.add_size_gradient(wall_curves, 1,
                              lc_near=0.001, lc_far=0.05,
                              dist_near=0.001, dist_far=0.2,
                              set_as_background=False)

    # Wake refinement downstream
    f2 = gb.add_wake_refinement([3], direction=[1,0,0],
                                length=2.0, lc_min=0.005, lc_max=0.05)

    # Combine and set as background
    gb.set_background_mesh_from_fields([f1, f2], operator='min')
    gb.generate('tet')
```

## Hex Meshing Recipe

```python
with GmshBuilder(verbose=False) as gb:
    # 1. Create simple topology (mappable volumes)
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])

    # 2. Set structured divisions
    gb.set_divisions(10)

    # 3. Auto-transfinite for structured mesh
    gb.set_transfinite_automatic_all()

    # 4. Recombine to get quads on surfaces
    gb.set_recombine_all()

    # 5. Generate hex mesh
    gb.generate('hex')
```
"""

GMSH_BUILDER_GENERATION = """
# Mesh Generation (mesh_generate.py, 48 methods)

## Core Generation (15 methods)

| Method | Description |
|--------|-------------|
| `generate(element_type='tet')` | Generate 3D mesh ('tet', 'hex', 'mixed') |
| `generate_surface()` | Generate 2D surface mesh only |
| `generate_curve()` | Generate 1D curve mesh only |
| `generate_volume()` | Generate 3D volume mesh only |
| `generate_tet()` | Generate tetrahedral mesh |
| `generate_hex()` | Generate hexahedral mesh |
| `generate_mixed()` | Generate mixed element mesh |
| `generate_surface_quad()` | Generate quad surface mesh |
| `generate_and_optimize(opt_method='Netgen')` | Generate + optimize |
| `generate_adaptive(error_field, target_error)` | Adaptive refinement |
| `generate_boundary_layer_mesh()` | Boundary layer mesh |
| `generate_prism_layers(surface_tags, heights)` | Prism layer extrusion |
| `generate_surface_on_entity(surf_tag)` | Mesh single surface |
| `generate_curve_on_entity(curve_tag)` | Mesh single curve |
| `import_stl_mesh(filename)` | Import and register STL mesh |

```python
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_mesh_size(0.005)

    # Tetrahedral mesh (default)
    gb.generate()

    # Or hex mesh (requires structured topology)
    gb.set_divisions(5)
    gb.generate('hex')
```

## Mesh Modification (12 methods)

| Method | Description |
|--------|-------------|
| `delete_mesh()` | Delete mesh, keep geometry |
| `delete_all_mesh()` | Delete all meshes |
| `refine()` | Uniform refinement |
| `optimize_mesh(method='Netgen')` | Optimize quality |
| `smooth_laplacian(n_iter=5)` | Laplacian smoothing |
| `convert_to_second_order()` | Convert to 2nd order elements |
| `convert_to_first_order()` | Convert to 1st order elements |
| `recombine_mesh()` | Recombine triangles to quads |
| `split_quadrangles()` | Split quads to triangles |
| `reverse_elements(dim, tags)` | Reverse element orientation |
| `partition_mesh(n_parts)` | Partition mesh |
| `unpartition_mesh()` | Undo partitioning |

## Node / Element Operations (10 methods)

| Method | Description |
|--------|-------------|
| `renumber_nodes()` | Compact node numbering |
| `renumber_elements()` | Compact element numbering |
| `reorder_elements(method)` | Reorder for cache efficiency |
| `compute_renumbering(method)` | Compute optimal renumbering |
| `reclassify_nodes()` | Reclassify nodes on geometry |
| `relocate_nodes(dim, tag)` | Relocate nodes to geometry |
| `set_mesh_coherence()` | Remove duplicate nodes/elements |
| `rebuild_node_cache()` | Rebuild internal node cache |
| `rebuild_element_cache()` | Rebuild internal element cache |

## Embedding (3 methods)

| Method | Description |
|--------|-------------|
| `embed_point_in_volume(point_tag, vol_tag)` | Force mesh node at point |
| `embed_curve_in_surface(curve_tag, surf_tag)` | Embed curve in surface mesh |
| `embed_surface_in_volume(surf_tag, vol_tag)` | Embed surface in volume mesh |

## Topology / Homology (8 methods)

| Method | Description |
|--------|-------------|
| `classify_surfaces(angle)` | Classify surface patches |
| `create_geometry_from_mesh()` | Create geometry from mesh |
| `create_topology(angle)` | Create topology from mesh |
| `add_homology_request(dim, domain, subdomain)` | Add homology computation |
| `compute_homology()` | Compute homology groups |
| `compute_cross_field()` | Compute cross field for meshing |
| `clear_homology_requests()` | Clear homology requests |
| `get_ghost_elements(dim)` | Get ghost elements |
| `get_partition_count()` | Number of mesh partitions |
"""

GMSH_BUILDER_QUALITY = """
# Mesh Quality (mesh_quality.py, 27 methods)

## Quality Metrics (8 methods)

| Method | Description |
|--------|-------------|
| `get_quality(vol_id=None, metric='scaledJacobian')` | Quality values array |
| `get_quality_histogram(vol_id=None, n_bins=20, ...)` | Quality histogram |
| `get_quality_range(vol_id=None, metric='scaledJacobian')` | (min, max, mean) |
| `get_quality_summary(vol_id=None)` | Printed summary string |
| `get_volume_quality(vol_id)` | Quality for specific volume |
| `count_below_threshold(threshold, vol_id=None, ...)` | Count bad elements |
| `count_above_threshold(threshold, vol_id=None, ...)` | Count good elements |
| `get_worst_elements(n=10, vol_id=None, ...)` | Worst N elements |

```python
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_mesh_size(0.005)
    gb.generate()

    # Quality summary
    print(gb.get_quality_summary())

    # Check for bad elements (scaled Jacobian < 0.3)
    n_bad = gb.count_below_threshold(0.3)
    print(f"Elements below 0.3: {n_bad}")
```

## Aspect Ratio (2 methods)

| Method | Description |
|--------|-------------|
| `get_aspect_ratio(vol_id=None)` | Aspect ratio array |
| `get_aspect_ratio_histogram(vol_id=None, n_bins=20)` | AR histogram |

## Edge Length (2 methods)

| Method | Description |
|--------|-------------|
| `get_edge_length_range(vol_id=None)` | (min, max, mean) edge lengths |
| `get_edge_length_histogram(vol_id=None, n_bins=20)` | Edge length histogram |

## Advanced Metrics (2 methods)

| Method | Description |
|--------|-------------|
| `get_warpage(vol_id=None)` | Face warpage values |
| `get_jacobian_range(vol_id=None)` | (min, max) Jacobian |

## Quality Improvement (2 methods)

| Method | Description |
|--------|-------------|
| `smooth_mesh(n_iter=5, method='Laplacian')` | Smooth mesh nodes |
| `optimize_quality(method='Netgen', n_iter=3)` | Optimize element quality |

## Statistics (2+ methods)

| Method | Description |
|--------|-------------|
| `get_mesh_info()` | Dict with node/element counts, types, sizes |
| `get_mesh_statistics()` | Comprehensive statistics dict |

Available quality metrics: 'scaledJacobian', 'gamma', 'eta', 'SICN', 'SIGE',
'minAngle', 'maxAngle', 'volume'.
"""

GMSH_BUILDER_MESH_ACCESS = """
# Mesh Access (mesh_access.py, 75 methods)

## Node Access (7 methods)

| Method | Description |
|--------|-------------|
| `get_nodes(vol_id=None)` | All node tags and coordinates |
| `get_node_coordinates(node_tag)` | Coordinates of single node |
| `get_node_coordinates_batch(node_tags)` | Batch coordinate lookup |
| `get_nodes_on_surface(vol_id, surf_idx)` | Nodes on specific surface |
| `get_surface_nodes_with_normals(vol_id, surf_idx)` | Nodes + normal vectors |
| `get_internal_nodes(vol_id=None)` | Interior nodes only |
| `get_boundary_nodes(vol_id=None)` | Boundary nodes only |

## Element Access (7 methods)

| Method | Description |
|--------|-------------|
| `get_elements(vol_id=None, element_type=None)` | Element tags and connectivity |
| `get_element_nodes(elem_tag)` | Node tags for element |
| `get_hex_count(vol_id=None)` | Number of hexahedra |
| `get_tet_count(vol_id=None)` | Number of tetrahedra |
| `get_pyramid_count(vol_id=None)` | Number of pyramids |
| `get_element_face_count(elem_tag)` | Number of faces |
| `get_elements_in_sphere(center, radius)` | Elements within sphere |

## Mapping (2 methods)

| Method | Description |
|--------|-------------|
| `get_node_to_element_map(vol_id=None)` | Node -> element connectivity |
| `get_edge_nodes(vol_id=None)` | Edge node pairs |

## Element Data (7 methods)

| Method | Description |
|--------|-------------|
| `get_element_edge_nodes(elem_tag)` | Edge nodes for element |
| `get_element_face_nodes(elem_tag)` | Face nodes for element |
| `get_element_by_coordinates(x, y, z)` | Find element at point |
| `get_element_properties(elem_tag)` | Element type, dim, nodes |
| `get_max_element_tag()` | Maximum element tag |
| `get_max_node_tag()` | Maximum node tag |
| `get_element_types(vol_id=None)` | Distinct element types |

## Jacobian / Basis Functions (5 methods)

| Method | Description |
|--------|-------------|
| `get_jacobian(elem_tag, ...)` | Jacobian matrix at points |
| `get_jacobians(elem_type, vol_tag, ...)` | Jacobians for element type |
| `get_basis_functions(elem_type, ...)` | Shape function values |
| `get_integration_points(elem_type, order)` | Quadrature points/weights |
| `get_element_barycenters(vol_id=None, ...)` | Element centroids |

## Element Sizes (1 method)

| Method | Description |
|--------|-------------|
| `get_element_sizes(vol_id=None)` | Element size (volume/area) |

## Node Manipulation (4 methods)

| Method | Description |
|--------|-------------|
| `set_node_coordinates(node_tag, x, y, z)` | Move node |
| `add_nodes_manual(coords, tags=None)` | Add nodes programmatically |
| `add_elements_manual(elem_type, node_tags, ...)` | Add elements manually |
| `remove_duplicate_nodes(tol=1e-10)` | Merge duplicate nodes |

## Periodic Mesh (3 methods)

| Method | Description |
|--------|-------------|
| `set_periodic_mesh(dim, tags1, tags2, affine)` | Set periodic BC |
| `get_periodic_nodes(dim, tag)` | Get periodic node pairs |
| `get_periodic_keys(dim)` | Get periodic entity pairs |

## Volume-Specific Counts (5 methods)

| Method | Description |
|--------|-------------|
| `get_volume_node_count(vol_id)` | Node count in volume |
| `get_volume_element_count(vol_id)` | Element count in volume |
| `get_volume_hex_count(vol_id)` | Hex count in volume |
| `get_volume_tet_count(vol_id)` | Tet count in volume |
| `get_surface_node_count(vol_id, surf_idx)` | Nodes on surface |

## Edge / Face Topology (5 methods)

| Method | Description |
|--------|-------------|
| `create_edges()` | Create edge data structure |
| `create_faces()` | Create face data structure |
| `get_all_edges()` | All edges (node pairs) |
| `get_all_faces()` | All faces (node lists) |
| `get_edges_for_element(elem_tag)` | Edges of element |

## NumPy Export (2 methods)

| Method | Description |
|--------|-------------|
| `to_numpy_nodes(vol_id=None)` | Nodes as (N,3) ndarray |
| `to_numpy_elements(vol_id=None, elem_type=None)` | Elements as (M,K) ndarray |

```python
import numpy as np
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_mesh_size(0.005)
    gb.generate()

    # NumPy arrays for custom processing
    nodes = gb.to_numpy_nodes()       # shape (N, 3)
    elems = gb.to_numpy_elements()    # shape (M, K)
    print(f"Nodes: {nodes.shape}, Elements: {elems.shape}")
```
"""

GMSH_BUILDER_PHYSICAL_GROUPS = """
# Physical Groups (physical_groups.py, 64 methods)

## Core Group Operations (8 methods)

| Method | Description |
|--------|-------------|
| `add_physical_group(dim, tags, name)` | Add physical group |
| `set_physical_group(vol_id, name)` | Assign physical group to volume |
| `add_block(vol_ids, block_id=None, name=None)` | Add volume block (3D physical group) |
| `add_block_by_name(vol_ids, name)` | Add block by name |
| `add_sideset(surf_tags, sideset_id=None, name=None)` | Add surface sideset (2D) |
| `add_nodeset(point_tags, nodeset_id=None, name=None)` | Add node set (0D) |
| `auto_assign_blocks()` | Auto-assign blocks to all volumes |
| `auto_assign_all()` | Auto-assign blocks + sidesets |

```python
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    coil = gb.add_cylinder([0, 0, 0.02], 'z', 0.05, 0.01)

    gb.set_mesh_size(0.005)
    gb.generate()

    # Assign blocks for multi-material export
    gb.add_block(core, name='iron_core')
    gb.add_block(coil, name='coil')

    # Or auto-assign
    gb.auto_assign_blocks()
```

## Query (10 methods)

| Method | Description |
|--------|-------------|
| `get_physical_groups(dim=None)` | List all physical groups |
| `get_all_blocks()` | List all volume blocks |
| `get_all_sidesets()` | List all surface sidesets |
| `get_all_nodesets()` | List all nodesets |
| `get_block_name(block_tag)` | Get name of a block (3D physical group) |
| `get_sideset_name(ss_tag)` | Get name of a sideset (2D physical group) |
| `get_nodeset_name(ns_tag)` | Get name of a nodeset (0D physical group) |
| `get_physical_group_name(tag, dim)` | Name of physical group |
| `find_physical_group_by_name(name)` | Find group by name |

## Material Assignment (9 methods)

| Method | Description |
|--------|-------------|
| `set_material(vol_id, mu_r, ...)` | Assign material to volume |
| `set_material_by_name(vol_ids, name, properties)` | Assign material by name with properties dict |
| `get_material(vol_id)` | Get material dict for volume |
| `has_material(vol_id)` | Check if material assigned |
| `get_all_materials()` | Dict of all materials |
| `set_material_conductivity(vol_id, sigma)` | Set conductivity |
| `set_material_density(vol_id, rho)` | Set density |
| `get_material_property(vol_id, prop)` | Get material property |
| `copy_material(src_id, dst_id)` | Copy material assignment |

```python
# Multi-material Radia export
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_material(core, mu_r=1000)

    gb.set_mesh_size(0.005)
    gb.generate()
    container = gb.to_radia_with_materials()
```

## Rename / Remove (3 methods)

| Method | Description |
|--------|-------------|
| `rename_physical_group(tag, dim, name)` | Rename group |
| `rename_block(block_tag, new_name)` | Rename a block (3D physical group) |
| `remove_physical_group(tag, dim)` | Remove group |

## Block Data Access (12 methods)

| Method | Description |
|--------|-------------|
| `get_block_elements(vol_id)` | Elements in block |
| `get_block_hex_count(vol_id)` | Hex count in block |
| `get_block_tet_count(vol_id)` | Tet count in block |
| `get_block_node_count(vol_id)` | Node count in block |
| `get_block_nodes(vol_id)` | Node tags in block |
| `get_block_element_count(vol_id)` | Total elements in block |
| `get_block_volumes(name)` | Volumes in named block |
| `get_block_surfaces(vol_id)` | Surfaces in block |
| `get_block_bounding_box(vol_id)` | Bounding box of block |
| `get_block_center(vol_id)` | Center of block |

## Sideset Data Access (8 methods)

| Method | Description |
|--------|-------------|
| `get_sideset_elements(name)` | Surface elements in sideset |
| `get_sideset_tri_count(name)` | Triangle count |
| `get_sideset_quad_count(name)` | Quad count |
| `get_sideset_node_count(name)` | Node count |
| `get_sideset_nodes(name)` | Node tags in sideset |
| `get_sideset_surfaces(name)` | Surface tags |
| `get_sideset_area(name)` | Total area |
| `get_sideset_bounding_box(name)` | Bounding box |

## Nodeset Data Access (4 methods)

| Method | Description |
|--------|-------------|
| `get_nodeset_nodes(name)` | Node tags in nodeset |
| `get_nodeset_node_count(name)` | Node count |
| `get_nodeset_coordinates(name)` | Node coordinates |
| `get_nodeset_bounding_box(name)` | Bounding box |

## Block Attributes (4 methods)

| Method | Description |
|--------|-------------|
| `set_block_attribute(vol_id, key, value)` | Set custom attribute |
| `get_block_attribute(vol_id, key)` | Get custom attribute |
| `get_block_attribute_names(vol_id)` | List attribute names |
| `remove_block_attribute(vol_id, key)` | Remove attribute |
"""

GMSH_BUILDER_EXPORT = """
# Export (export.py, 30 methods)

## Mesh File Export (8 methods)

| Method | Description |
|--------|-------------|
| `export(filename, version=2.2)` | Export .msh (GMSH format) |
| `export_msh(filename)` | Export MSH v2.2 |
| `export_msh_v4(filename)` | Export MSH v4.1 |
| `export_stl(filename)` | Export STL (surface triangles) |
| `export_vtk(filename)` | Export VTK for ParaView |
| `export_auto(filename)` | Auto-detect format from extension |
| `export_iges(filename)` | Export IGES geometry |
| `export_x3d(filename)` | Export X3D (web visualization) |

## Geometry Export (3 methods)

| Method | Description |
|--------|-------------|
| `export_geo(filename)` | Export GMSH .geo script |
| `export_step(filename)` | Export STEP geometry |
| `export_brep(filename)` | Export BRep geometry |

## Radia Integration (3 methods)

| Method | Description |
|--------|-------------|
| `to_radia(mu_r=1000, magnetization=None)` | Convert to Radia container |
| `to_radia_with_materials()` | Convert with per-block materials |
| `to_radia_container(material_map)` | Convert with custom material map |

```python
import radia as rad
rad.UtiDelAll()

with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_material(core, mu_r=1000)
    gb.set_mesh_size(0.005)
    gb.generate()

    # Direct conversion to Radia objects
    container = gb.to_radia(mu_r=1000)
    # Or with per-block materials
    container = gb.to_radia_with_materials()

B = rad.Fld(container, 'b', [0, 0, 0.05])
rad.UtiDelAll()
```

## NGSolve Integration (2 methods)

| Method | Description |
|--------|-------------|
| `to_ngsolve_mesh()` | Convert to NGSolve Mesh object |
| `to_ngsolve_mesh_with_groups()` | Convert with physical group mapping |

## Data Conversion (4 methods)

| Method | Description |
|--------|-------------|
| `to_dict()` | Export mesh as dict (nodes, elements, groups) |
| `to_pyvista()` | Convert to PyVista UnstructuredGrid |
| `to_numpy_nodes(vol_id=None)` | Nodes as NumPy array |
| `to_numpy_elements(vol_id=None, ...)` | Elements as NumPy array |

## Import / Merge (1 method)

| Method | Description |
|--------|-------------|
| `merge_file(filename)` | Merge a file (mesh or geometry) into the current model |

## Format Info (1 method)

| Method | Description |
|--------|-------------|
| `get_export_formats()` | List of supported export formats |

Recommended formats:
- `.msh` (v2.2): Best for Radia and NGSolve import
- `.step`: CAD geometry exchange
- `.vtk`: ParaView visualization
- `.stl`: 3D printing / surface mesh exchange
"""

GMSH_BUILDER_ENTITY_WRAPPERS = """
# Entity Wrappers (entity_wrappers.py, 55 methods)

Query geometric and topological properties of volumes, surfaces, curves,
and vertices by their tags.

## Volume Queries (14 methods)

| Method | Description |
|--------|-------------|
| `volume_surfaces(vol_id)` | List of surface tags |
| `volume_curves(vol_id)` | List of curve tags |
| `volume_vertices(vol_id)` | List of vertex (point) tags |
| `volume_bounding_box(vol_id)` | [xmin,ymin,zmin, xmax,ymax,zmax] |
| `volume_center(vol_id)` | Center point [x, y, z] |
| `volume_measure(vol_id)` | Volume in m^3 |
| `volume_inertia(vol_id)` | Inertia tensor |
| `volume_type(vol_id)` | Shape type string |
| `volume_adjacent_volumes(vol_id)` | Adjacent volume tags |
| `volume_physical_groups(vol_id)` | Physical groups containing volume |
| `volume_is_inside(vol_id, point)` | Point inside volume? |
| `volume_surface_area(vol_id)` | Total surface area |
| `volume_curve_count(vol_id)` | Number of bounding curves |
| `volume_vertex_count(vol_id)` | Number of vertices |

## Surface Queries (14 methods)

| Method | Description |
|--------|-------------|
| `surface_curves(surf_tag)` | List of curve tags |
| `surface_vertices(surf_tag)` | List of vertex tags |
| `surface_volumes(surf_tag)` | Volumes bounded by surface |
| `surface_bounding_box(surf_tag)` | Bounding box |
| `surface_center(surf_tag)` | Center point |
| `surface_area(surf_tag)` | Area in m^2 |
| `surface_type(surf_tag)` | Type string ('Plane', 'Cylinder', ...) |
| `surface_normal_at(surf_tag, u, v)` | Normal vector at parameter |
| `surface_closest_point(surf_tag, point)` | Closest point on surface |
| `surface_is_planar(surf_tag)` | Planarity check |
| `surface_is_cylindrical(surf_tag)` | Cylindrical check |
| `surface_is_conical(surf_tag)` | Conical check |
| `surface_is_spherical(surf_tag)` | Spherical check |
| `surface_physical_groups(surf_tag)` | Physical groups |

## Curve Queries (14 methods)

| Method | Description |
|--------|-------------|
| `curve_vertices(curve_tag)` | Endpoint vertex tags |
| `curve_surfaces(curve_tag)` | Adjacent surface tags |
| `curve_bounding_box(curve_tag)` | Bounding box |
| `curve_center(curve_tag)` | Center point |
| `curve_length(curve_tag)` | Arc length in meters |
| `curve_type(curve_tag)` | Type string ('Line', 'Circle', ...) |
| `curve_point_at(curve_tag, t)` | Point at parameter t in [0,1] |
| `curve_tangent_at(curve_tag, t)` | Tangent vector at parameter |
| `curve_curvature_at(curve_tag, t)` | Curvature at parameter |
| `curve_closest_point(curve_tag, point)` | Closest point on curve |
| `curve_is_line(curve_tag)` | Line check |
| `curve_is_circle(curve_tag)` | Circle check |
| `curve_is_bspline(curve_tag)` | B-spline check |
| `curve_physical_groups(curve_tag)` | Physical groups |

## Vertex Queries (13 methods)

| Method | Description |
|--------|-------------|
| `vertex_coordinates(vertex_tag)` | [x, y, z] |
| `vertex_curves(vertex_tag)` | Adjacent curve tags |
| `vertex_surfaces(vertex_tag)` | Adjacent surface tags |
| `vertex_volumes(vertex_tag)` | Adjacent volume tags |
| `vertex_physical_groups(vertex_tag)` | Physical groups |
| `vertex_distance_to(vertex_tag, point)` | Distance to point |
| `vertex_on_curve(vertex_tag, curve_tag)` | On curve check |
| `vertex_on_surface(vertex_tag, surf_tag)` | On surface check |
| `vertex_on_volume(vertex_tag, vol_tag)` | On volume check |
| `vertex_bounding_box(vertex_tag)` | Point bounding box |
| `get_vertex_count()` | Total vertex count |
| `get_all_vertices()` | All vertex tags |
| `vertices_in_bounding_box(xmin, ymin, zmin, xmax, ymax, zmax)` | Find vertices |
"""

GMSH_BUILDER_ADVANCED = """
# Advanced Features

## Geometry Analysis (geometry_analysis.py, 35 methods)

| Method | Description |
|--------|-------------|
| `heal_all(tolerance=1e-8)` | Heal all geometry defects |
| `defeature_volume(vol_id, tol)` | Remove small features |
| `remove_small_faces(vol_id, tol)` | Remove small faces |
| `find_small_curves(tol)` | Find curves shorter than tol |
| `find_small_surfaces(tol)` | Find surfaces smaller than tol |
| `find_small_volumes(tol)` | Find volumes smaller than tol |
| `find_narrow_surfaces(aspect_ratio)` | Find narrow (sliver) surfaces |
| `remove_duplicates(tol=1e-8)` | Remove duplicate entities |
| `find_orphan_entities()` | Find unconnected entities |
| `clean_geometry(tol=1e-8)` | Full geometry cleanup |
| `distance_between_entities(dim1, tag1, dim2, tag2)` | Min distance |
| `closest_entities(dim1, tag1, dim2, tags2)` | Find closest entity |
| `find_overlapping_volumes()` | Detect overlapping volumes |
| `check_watertight(vol_id)` | Watertight check |
| `get_curve_loops(surf_tag)` | Curve loops of surface |
| `get_surface_loops(vol_tag)` | Surface loops of volume |
| `principal_curvatures(surf_tag, u, v)` | Principal curvatures at point |

## Groups (groups.py, 30 methods)

Named selection groups for organizing entities.

| Method | Description |
|--------|-------------|
| `create_group(name)` | Create empty group |
| `delete_group(name)` | Delete group |
| `rename_group(old_name, new_name)` | Rename group |
| `group_add_volumes(name, vol_ids)` | Add volumes to group |
| `group_add_surfaces(name, surf_tags)` | Add surfaces to group |
| `group_add_curves(name, curve_tags)` | Add curves to group |
| `group_add_vertices(name, vertex_tags)` | Add vertices to group |
| `group_remove_volumes(name, vol_ids)` | Remove volumes from group |
| `group_remove_surfaces(name, surf_tags)` | Remove surfaces |
| `group_remove_curves(name, curve_tags)` | Remove curves |
| `group_remove_vertices(name, vertex_tags)` | Remove vertices |
| `group_get_entities(name, dim=None)` | Get entities in group |
| `merge_groups(name1, name2, result_name)` | Union of groups |
| `subtract_groups(name1, name2, result_name)` | Difference of groups |
| `intersect_groups(name1, name2, result_name)` | Intersection of groups |
| `add_curveset(name, curve_tags)` | Add curve set |

## Post-Processing (post_processing.py, 25 methods)

| Method | Description |
|--------|-------------|
| `add_view(name)` | Create post-processing view |
| `remove_view(view_tag)` | Remove view |
| `add_scalar_node_data(view, node_tags, values)` | Scalar at nodes |
| `add_vector_node_data(view, node_tags, vectors)` | Vector at nodes |
| `add_tensor_node_data(view, node_tags, tensors)` | Tensor at nodes |
| `add_scalar_element_data(view, elem_tags, values)` | Scalar per element |
| `add_vector_element_data(view, elem_tags, vectors)` | Vector per element |
| `probe_view(view, x, y, z)` | Probe view value at point |
| `set_view_option_number(view, name, value)` | Set view numeric option |
| `set_view_option_string(view, name, value)` | Set view string option |

## Options (options.py, 20 methods)

| Method | Description |
|--------|-------------|
| `set_option_number(name, value)` | Set GMSH numeric option |
| `set_option_string(name, value)` | Set GMSH string option |
| `get_option_number(name)` | Get numeric option |
| `get_option_string(name)` | Get string option |
| `restore_default_options()` | Reset all to defaults |
| `set_geometry_tolerance(tol)` | Geometry tolerance |
| `set_mesh_only_visible(flag)` | Mesh only visible entities |
| `set_mesh_save_all(flag)` | Save all elements |
| `set_entity_color(dim, tag, r, g, b, a=255)` | Set entity color |
| `set_entity_visibility(dim, tag, visible)` | Show/hide entity |
"""

GMSH_BUILDER_RECIPES = """
# Practical Recipes

## Recipe 1: C-Type Magnet Hex Mesh

```python
from radia.gmsh_builder import GmshBuilder
import radia as rad

rad.UtiDelAll()

with GmshBuilder(verbose=False) as gb:
    # Create C-shape yoke
    yoke = gb.add_c_shape([0, 0, 0], [0.1, 0.08, 0.02],
                          gap=0.02, thickness=0.02)

    # Webcut for structured hex
    gb.webcut_plane(yoke, 'x', 0.03)
    gb.webcut_plane(yoke, 'x', -0.03)
    gb.webcut_plane(yoke, 'y', 0.02)
    gb.webcut_plane(yoke, 'y', -0.02)

    # Structured divisions
    gb.set_divisions(5)
    gb.set_transfinite_automatic_all()
    gb.set_recombine_all()
    gb.generate('hex')

    # Convert to Radia
    container = gb.to_radia(mu_r=1000)

# Add coil and solve
coil = rad.ObjArcCur([0, 0, 0], [0.035, 0.045],
                     [-3.14159, 3.14159], 0.01, 100, 1e6)
assembly = rad.ObjCnt([container, coil])
rad.Solve(assembly, 0.0001, 1000, 0)
B = rad.Fld(assembly, 'b', [0, 0, 0])
rad.UtiDelAll()
```

## Recipe 2: Coil Tetrahedral Mesh

```python
with GmshBuilder(verbose=False) as gb:
    coil = gb.add_hollow_cylinder([0, 0, 0], 'z',
                                   r_inner=0.04, r_outer=0.05,
                                   h=0.01)
    gb.set_mesh_size(0.003)
    gb.generate()
    gb.export('coil.msh')
```

## Recipe 3: Multi-Material Assembly

```python
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    pole1 = gb.add_box([0.04, 0, 0.025], [0.02, 0.02, 0.02])
    pole2 = gb.add_box([-0.04, 0, 0.025], [0.02, 0.02, 0.02])

    # Fragment for shared interfaces (conformal mesh)
    new_ids = gb.fragment([core, pole1, pole2])

    # Assign materials per block
    gb.auto_assign_blocks()
    for vid in new_ids:
        gb.set_material(vid, mu_r=1000)

    gb.set_mesh_size(0.004)
    gb.generate()
    container = gb.to_radia_with_materials()
```

## Recipe 4: Structured Hex with Boundary Layer

```python
with GmshBuilder(verbose=False) as gb:
    box = gb.add_box([0, 0, 0], [0.1, 0.1, 0.1])

    # Boundary layer on bottom surface
    surfs = gb.volume_surfaces(box)
    gb.set_boundary_layer(surfs[:1], sizes=[0.001, 0.002, 0.004],
                          ratios=[1.5])

    gb.set_mesh_size(0.01)
    gb.generate()
    gb.export('bl_mesh.msh')
```

## Recipe 5: Structured Hex via Extrude with numElements

```python
with GmshBuilder(verbose=False) as gb:
    # Create 2D cross-section (rectangle)
    rect = gb.add_rectangle([0, 0, 0], 0.1, 0.02)

    # Extrude with structured layers: 10 elements along z
    vol_ids = gb.extrude_surface(rect, 0, 0, 0.03,
                                  num_elements=[10], recombine=True)

    # Non-uniform layers: 3 thin + 7 thick
    # heights=[0.1, 1.0] means 10% + 90% of total height
    vol_ids = gb.extrude_surface(rect, 0, 0, 0.03,
                                  num_elements=[3, 7],
                                  heights=[0.1, 1.0],
                                  recombine=True)

    # Set quad meshing on the base surface
    gb.set_recombine(rect)
    gb.set_recombination_algorithm('blossom')
    gb.set_transfinite_surface(rect)

    gb.generate()
    gb.export('structured_hex.msh')
```

## Recipe 6: Import STEP and Mesh

```python
with GmshBuilder(verbose=False) as gb:
    vol_ids = gb.import_step('magnet_assembly.step')

    # Heal imported geometry
    gb.heal_geometry()

    # Assign materials
    for vid in vol_ids:
        gb.set_material(vid, mu_r=1000)

    gb.set_mesh_size(0.005)
    gb.generate()
    container = gb.to_radia_with_materials()
```

## Recipe 6: Adaptive Mesh with Sizing Fields

```python
with GmshBuilder(verbose=False) as gb:
    core = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])

    # Distance field from all surfaces of core
    surfs = gb.volume_surfaces(core)
    f_dist = gb.add_field_distance([(2, s) for s in surfs])

    # Threshold: fine near surface, coarse far away
    f_thresh = gb.add_field_threshold(f_dist,
                                       min_size=0.001, max_size=0.01,
                                       dist_min=0.0, dist_max=0.02)
    gb.set_background_field(f_thresh)

    gb.generate()
    gb.export('adaptive_core.msh')
```
"""

GMSH_BUILDER_BEST_PRACTICES = """
# GmshBuilder Best Practices

## 1. Always Use Context Manager

```python
# CORRECT
with GmshBuilder() as gb:
    ...

# WRONG - GMSH not properly finalized
gb = GmshBuilder()
gb.__enter__()
...
```

## 2. Hex Meshing: Three Approaches

For structured hexahedral meshes:

```python
# Approach A: set_divisions + generate('hex') for box-like volumes
with GmshBuilder(verbose=False) as gb:
    box = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_divisions(10)
    gb.generate('hex')

# Approach B: Structured extrusion with numElements (most flexible)
with GmshBuilder(verbose=False) as gb:
    rect = gb.add_rectangle([0, 0, 0], 0.1, 0.02)
    gb.set_transfinite_surface(rect)
    gb.set_recombine(rect)
    gb.extrude_surface(rect, 0, 0, 0.03,
                       num_elements=[10], recombine=True)
    gb.generate()

# Approach C: set_recombination_algorithm for quality control
with GmshBuilder(verbose=False) as gb:
    box = gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
    gb.set_recombination_algorithm('blossom')  # best quality
    gb.set_recombine_all()
    gb.set_subdivision_algorithm(2)  # all hexas
    gb.generate()
```

## 3. Webcut for Structured Meshing

Use webcut_plane to split volumes into structured-meshable sub-volumes.

```python
gb.webcut_plane(vol_id, 'x', 0.03)   # Split at x=0.03
gb.webcut_plane(vol_id, 'z', 0.0)    # Split at z=0
```

## 4. Fragment for Multi-Body Assemblies

Use fragment() to create shared interfaces between touching bodies.
This ensures a conformal (matching) mesh at boundaries.

```python
new_ids = gb.fragment([body1, body2, body3])
```

## 5. Auto-Assign Blocks for Radia Export

Before exporting to Radia with materials, assign physical groups.

```python
gb.auto_assign_blocks()      # Assigns each volume as a block
gb.set_material(vol_id, mu_r=1000)
container = gb.to_radia_with_materials()
```

## 6. Set Mesh Size Before Generate for Tet

```python
gb.set_mesh_size(0.005)    # Must be called before generate()
gb.generate()               # Tet mesh
```

## 7. Suppress Output for Batch Runs

```python
with GmshBuilder(verbose=False) as gb:
    gb.set_verbose(False)  # Also suppress GMSH internal messages
    ...
```

## 8. to_radia() Returns Container ID

The returned ID is a Radia container ready for field computation.

```python
container = gb.to_radia(mu_r=1000)
B = rad.Fld(container, 'b', [0, 0, 0.05])
```

## 9. Export Format Recommendations

| Format | Use Case |
|--------|----------|
| `.msh` (v2.2) | Radia import, NGSolve import |
| `.step` | CAD exchange |
| `.vtk` | ParaView visualization |
| `.stl` | 3D printing, surface mesh |
| `.brep` | OpenCASCADE geometry |

## 10. All Coordinates in Meters

Consistent with Radia's unit policy. No unit conversion needed.

```python
# 100mm x 20mm x 30mm box
gb.add_box([0, 0, 0], [0.1, 0.02, 0.03])
```

## 11. Check Quality After Generation

```python
gb.generate()
summary = gb.get_quality_summary()
print(summary)
n_bad = gb.count_below_threshold(0.3)
if n_bad > 0:
    gb.optimize_quality()
```

## 12. Memory: Call rad.UtiDelAll() After Radia Use

```python
rad.UtiDelAll()
with GmshBuilder(verbose=False) as gb:
    container = gb.to_radia(mu_r=1000)

B = rad.Fld(container, 'b', [0, 0, 0.05])
rad.UtiDelAll()  # Cleanup Radia objects
```
"""


GMSH_BUILDER_CFD_TECHNIQUES = """
# CFD Meshing Techniques with GmshBuilder

GmshBuilder uses the OCC (OpenCASCADE) kernel. The geo-kernel-only
`extrudeBoundaryLayer` is NOT available; use field-based boundary layers
and structured extrusion instead.

---

## Technique 1: Wall-Normal Grading (Boundary Layer Resolution)

The most critical CFD meshing requirement. Use `add_size_gradient` for
a single-call Distance+Threshold setup, or `add_boundary_layer_field`
for advanced BL control.

```python
with GmshBuilder(verbose=False) as gb:
    # Create channel with inlet/outlet
    channel = gb.add_box([0, 0, 0], [1.0, 0.1, 0.05])
    gb.synchronize()

    # Get wall surfaces (top and bottom)
    surfs = gb.volume_surfaces(channel)
    wall_surfs = [surfs[0], surfs[5]]  # top/bottom

    # Simple approach: add_size_gradient (one call)
    f1 = gb.add_size_gradient(
        wall_surfs, dim=2,
        lc_near=0.0005,   # first cell height (target y+ ~ 1)
        lc_far=0.005,     # far field size
        dist_near=0.001,  # BL thickness start
        dist_far=0.02,    # BL thickness end
        set_as_background=True
    )

    gb.generate('tet')
    gb.export('channel_bl.msh')
```

### Y+ Estimation for First Cell Height

```
y+ = 1:   y_wall = 6 * nu / u_tau
          u_tau  = sqrt(tau_w / rho)
          tau_w  ~ 0.5 * Cf * rho * U^2
          Cf     ~ 0.058 * Re_x^(-0.2)  (turbulent flat plate)

Example: U=10 m/s, L=0.1 m, nu=1.5e-5 m^2/s
  Re   = 10 * 0.1 / 1.5e-5 = 66,667
  Cf   ~ 0.058 * 66667^(-0.2) = 0.0056
  tau_w ~ 0.5 * 0.0056 * 1.225 * 100 = 0.343 Pa
  u_tau = sqrt(0.343/1.225) = 0.529 m/s
  y_wall (y+=1) ~ 6 * 1.5e-5 / 0.529 ~ 1.7e-4 m
  -> lc_near = 0.0002 m
```

## Technique 2: Structured Boundary Layer via Extrusion

For higher quality BL meshes, extrude a 2D surface with non-uniform
layers using `num_elements` and `heights`.

```python
with GmshBuilder(verbose=False) as gb:
    # Create 2D cross-section
    rect = gb.add_rectangle([0, 0, 0], 1.0, 0.1)
    gb.set_transfinite_surface(rect)
    gb.set_recombine(rect)
    gb.synchronize()

    # Extrude with graded layers (thin near wall, thick in core)
    # 5 thin layers (20% of height) + 5 thick layers (80% of height)
    vol_ids = gb.extrude_surface(rect, 0, 0, 0.05,
                                  num_elements=[5, 5],
                                  heights=[0.2, 1.0],
                                  recombine=True)

    gb.generate()
    gb.export('structured_bl.msh')
```

## Technique 3: Multi-Zone Refinement (Field Composition)

Combine multiple sizing fields for complex flow domains. Use
`set_background_mesh_from_fields` to merge them with Min operator.

```python
with GmshBuilder(verbose=False) as gb:
    # Outer domain + inner body
    outer = gb.add_box([0, 0, 0], [2.0, 1.0, 0.5])
    body = gb.add_cylinder([0.5, 0.5, 0], 'z', 0.05, 0.5)
    gb.cut(outer, body)
    gb.synchronize()

    # Zone 1: Body surface refinement
    body_surfs = gb.get_all_surfaces()
    f1 = gb.add_size_gradient(
        body_surfs[:4], dim=2,
        lc_near=0.002, lc_far=0.05,
        dist_near=0.005, dist_far=0.1,
        set_as_background=False)

    # Zone 2: Wake refinement downstream
    f2 = gb.add_wake_refinement(
        [body_surfs[0]], direction=[1, 0, 0],
        length=1.0, lc_min=0.005, lc_max=0.05)

    # Zone 3: Inlet/outlet coarser
    f3 = gb.add_field_box(
        xmin=-0.1, xmax=0.1, ymin=0.3, ymax=0.7,
        zmin=0.0, zmax=0.5,
        size_in=0.01, size_out=0.05)

    # Combine all zones (Min = finest wins)
    gb.set_background_mesh_from_fields([f1, f2, f3], operator='min')
    gb.generate('tet')
    gb.export('multi_zone.msh')
```

## Technique 4: Airfoil 2D Mesh

Classic CFD benchmark geometry. Create airfoil profile from points,
add far-field domain, apply wall-normal grading + wake refinement.

```python
import math

with GmshBuilder(verbose=False) as gb:
    # NACA 0012 profile points (simplified)
    n_pts = 40
    chord = 0.1  # 100mm chord
    points = []
    for i in range(n_pts + 1):
        x = chord * (1 - math.cos(math.pi * i / n_pts)) / 2
        t = 0.12  # thickness ratio
        yt = 5 * t * chord * (
            0.2969 * math.sqrt(x/chord)
            - 0.1260 * (x/chord)
            - 0.3516 * (x/chord)**2
            + 0.2843 * (x/chord)**3
            - 0.1015 * (x/chord)**4)
        points.append([x, yt, 0])

    # Mirror for lower surface
    lower = [[p[0], -p[1], 0] for p in reversed(points[1:-1])]
    all_pts = points + lower

    # Create spline profile
    airfoil_curve = gb.add_spline_curve(all_pts, closed=True)

    # Far-field circle
    ff_radius = 10 * chord
    ff = gb.add_circle([chord/2, 0, 0], 'z', ff_radius)

    # Create surface (far-field minus airfoil)
    gb.synchronize()

    # Wall grading
    f1 = gb.add_size_gradient(
        [airfoil_curve], dim=1,
        lc_near=chord/200,    # fine at wall
        lc_far=ff_radius/10,  # coarse at far-field
        dist_near=chord/50,
        dist_far=chord * 2,
        set_as_background=False)

    # Wake
    f2 = gb.add_wake_refinement(
        [airfoil_curve], direction=[1, 0, 0],
        length=5 * chord,
        lc_min=chord/50, lc_max=chord)

    gb.set_background_mesh_from_fields([f1, f2], operator='min')
    gb.generate_surface()
    gb.export('naca0012.msh')
```

## Technique 5: Pipe Flow (Axisymmetric Structured)

Structured hex mesh for pipe flow using revolve with numElements.

```python
with GmshBuilder(verbose=False) as gb:
    import math

    # 2D cross-section: annular sector
    r_in, r_out = 0.02, 0.025
    length = 0.2

    rect = gb.add_rectangle([r_in, 0, 0], r_out - r_in, length)
    gb.set_transfinite_surface(rect)
    gb.set_recombine(rect)
    gb.synchronize()

    # Revolve 360 degrees with structured divisions
    vol_ids = gb.revolve_surface(
        rect, [0, 0, 0], [0, 0, 1], 2 * math.pi,
        num_elements=[36], recombine=True)

    gb.generate()
    gb.export('pipe_hex.msh')
```

## Technique 6: STL Terrain / Ocean Mesh

Import STL terrain data, classify surfaces, create geometry, and mesh.

```python
with GmshBuilder(verbose=False) as gb:
    # Import STL terrain
    gb.import_stl_mesh('terrain.stl', angle=30)

    # Re-classify with finer angle control
    gb.classify_surfaces_parametric(
        angle=25.0,         # feature detection angle
        boundary=True,
        curve_angle=120.0)  # curve angle threshold
    gb.create_geometry_from_mesh()
    gb.synchronize()

    # Elevation-based sizing field (if .pos file available)
    f1 = gb.add_terrain_field('terrain_size.pos',
                               format='structured')
    gb.set_background_field(f1)

    # Or simple curvature-based sizing
    gb.set_curvature_mesh(30)  # 30 elements per 2*pi curvature
    gb.set_min_max_size(10.0, 500.0)  # meters for terrain

    gb.generate_surface()
    gb.export('terrain_mesh.msh')
```

## Technique 7: Adaptive Mesh Refinement

Iteratively refine mesh based on solution-driven sizing fields.

```python
with GmshBuilder(verbose=False) as gb:
    domain = gb.add_box([0, 0, 0], [1.0, 0.5, 0.2])
    gb.synchronize()

    # Initial coarse mesh
    gb.set_mesh_size(0.02)

    # Create math-based field (e.g., refine where gradient is high)
    f_math = gb.add_field_math("0.005 + 0.015 * sqrt(x*x + y*y)")
    gb.set_background_field(f_math)

    # Iterative adaptation
    gb.adapt_mesh_iterative(f_math, n_iterations=3, size_factor=0.7)
    gb.export('adapted.msh')
```

## Technique 8: BoundaryLayer Field Composition

Advanced: compose BoundaryLayer field with other fields for complex
geometries. Unlike set_boundary_layer, add_boundary_layer_field returns
a field tag that can be combined with other fields.

```python
with GmshBuilder(verbose=False) as gb:
    channel = gb.add_box([0, 0, 0], [1.0, 0.2, 0.1])
    obstacle = gb.add_cylinder([0.3, 0.1, 0], 'z', 0.02, 0.1)
    gb.cut(channel, obstacle)
    gb.synchronize()

    # BL field on obstacle surface
    obs_surfs = gb.get_all_surfaces()[:4]
    f_bl = gb.add_boundary_layer_field(
        obs_surfs, dim=2,
        lc_min=0.0005, lc_max=0.01,
        dist_min=0.001, dist_max=0.02,
        ratio=1.3, n_layers=8)

    # Coarse far field
    f_far = gb.add_field_box(
        xmin=-0.1, xmax=1.1, ymin=-0.1, ymax=0.3,
        zmin=-0.1, zmax=0.2,
        size_in=0.005, size_out=0.02)

    gb.set_background_mesh_from_fields([f_bl, f_far], operator='min')
    gb.generate('tet')
    gb.export('obstacle_flow.msh')
```

---

## Key Limitations (OCC Kernel)

| Feature | Status | Workaround |
|---------|--------|------------|
| `extrudeBoundaryLayer` | geo kernel only (planned GMSH 5) | Field-based BL + structured extrusion |
| Prism layers from surface extrusion | Limited | `extrude_surface` with `num_elements` + graded `heights` |
| Anisotropic mesh stretching | Limited | `add_wake_refinement` Box field approximation |
| Hex-dominant with BL | Complex | Structured extrude + recombine |

## Performance Tips

1. **set_min_max_size**: Always set to prevent extremely small/large elements
2. **set_mesh_size_factor**: Global multiplier; useful for mesh convergence studies (0.5, 1.0, 2.0)
3. **set_recombination_algorithm('blossom')**: Best quality for quad/hex recombination
4. **Mesh order**: Generate 1st order, then `convert_to_second_order()` for quality
5. **optimize_mesh('Netgen')**: Best for tet quality; use 'Laplacian' for speed
"""


def get_gmsh_builder_documentation(topic: str = "all") -> str:
    """Return GmshBuilder usage documentation by topic."""
    topics = {
        "overview": GMSH_BUILDER_OVERVIEW,
        "geometry": GMSH_BUILDER_GEOMETRY,
        "boolean": GMSH_BUILDER_BOOLEAN,
        "transforms": GMSH_BUILDER_TRANSFORMS,
        "mesh_control": GMSH_BUILDER_MESH_CONTROL,
        "generation": GMSH_BUILDER_GENERATION,
        "quality": GMSH_BUILDER_QUALITY,
        "mesh_access": GMSH_BUILDER_MESH_ACCESS,
        "physical_groups": GMSH_BUILDER_PHYSICAL_GROUPS,
        "export": GMSH_BUILDER_EXPORT,
        "entity_wrappers": GMSH_BUILDER_ENTITY_WRAPPERS,
        "advanced": GMSH_BUILDER_ADVANCED,
        "recipes": GMSH_BUILDER_RECIPES,
        "best_practices": GMSH_BUILDER_BEST_PRACTICES,
        "cfd_techniques": GMSH_BUILDER_CFD_TECHNIQUES,
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
