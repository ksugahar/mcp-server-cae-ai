"""Tests for GMSH lint rules.

Each test provides intentionally bad code and verifies the rule fires,
then provides correct code and verifies no findings.
"""

import pytest
from mcp_server_cae_ai.gmsh.rules import (
    ALL_RULES,
    check_missing_gmsh_initialize,
    check_missing_gmsh_finalize,
    check_missing_synchronize,
    check_wrong_generate_dimension,
    check_missing_physical_groups,
    check_mixing_geo_and_occ,
    check_hardcoded_absolute_path,
    check_msh_v4_for_readgmsh,
    check_generate_before_synchronize,
    check_unit_conversion_in_coords,
    check_missing_model_add,
    check_setorder_before_generate,
    check_write_without_generate,
    check_gmsh_unicode_print,
)


# ============================================================
# Helper
# ============================================================

def _run(rule_func, code: str, filepath: str = "test_script.py"):
    lines = code.splitlines()
    return rule_func(filepath, lines)


# ============================================================
# GMSH rules
# ============================================================

class TestMissingGmshInitialize:
    def test_detects_missing_init(self):
        code = (
            'import gmsh\n'
            'gmsh.model.add("test")\n'
        )
        findings = _run(check_missing_gmsh_initialize, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'
        assert findings[0]['rule'] == 'missing-gmsh-initialize'

    def test_allows_with_init(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.add("test")\n'
        )
        assert _run(check_missing_gmsh_initialize, code) == []

    def test_skips_no_gmsh(self):
        code = 'import numpy\n'
        assert _run(check_missing_gmsh_initialize, code) == []


class TestMissingGmshFinalize:
    def test_detects_missing_finalize(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.add("test")\n'
        )
        findings = _run(check_missing_gmsh_finalize, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'
        assert findings[0]['rule'] == 'missing-gmsh-finalize'

    def test_allows_with_finalize(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.add("test")\n'
            'gmsh.finalize()\n'
        )
        assert _run(check_missing_gmsh_finalize, code) == []

    def test_skips_no_init(self):
        code = 'import numpy\n'
        assert _run(check_missing_gmsh_finalize, code) == []


class TestMissingSynchronize:
    def test_detects_generate_without_sync(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.model.mesh.generate(3)\n'
        )
        findings = _run(check_missing_synchronize, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'
        assert findings[0]['rule'] == 'missing-synchronize'

    def test_detects_physgroup_without_sync(self):
        code = (
            'import gmsh\n'
            'gmsh.model.geo.addPoint(0, 0, 0, 0.1)\n'
            'gmsh.model.addPhysicalGroup(3, [1])\n'
        )
        findings = _run(check_missing_synchronize, code)
        assert len(findings) == 1

    def test_allows_with_sync(self):
        code = (
            'import gmsh\n'
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.model.occ.synchronize()\n'
            'gmsh.model.mesh.generate(3)\n'
        )
        assert _run(check_missing_synchronize, code) == []

    def test_skips_no_geo_or_occ(self):
        code = (
            'import gmsh\n'
            'gmsh.open("mesh.msh")\n'
            'gmsh.model.mesh.generate(3)\n'
        )
        assert _run(check_missing_synchronize, code) == []


class TestWrongGenerateDimension:
    def test_detects_2d_for_volume(self):
        code = (
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.model.occ.synchronize()\n'
            'gmsh.model.mesh.generate(2)\n'
        )
        findings = _run(check_wrong_generate_dimension, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'

    def test_allows_3d_for_volume(self):
        code = (
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.model.occ.synchronize()\n'
            'gmsh.model.mesh.generate(3)\n'
        )
        assert _run(check_wrong_generate_dimension, code) == []

    def test_allows_2d_for_surface_only(self):
        code = (
            'gmsh.model.geo.addPoint(0, 0, 0, 0.1)\n'
            'gmsh.model.geo.addLine(1, 2)\n'
            'gmsh.model.geo.synchronize()\n'
            'gmsh.model.mesh.generate(2)\n'
        )
        assert _run(check_wrong_generate_dimension, code) == []


class TestMissingPhysicalGroups:
    def test_detects_no_physgroup(self):
        code = (
            'gmsh.model.mesh.generate(3)\n'
            'gmsh.write("output.msh")\n'
        )
        findings = _run(check_missing_physical_groups, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'

    def test_allows_with_physgroup(self):
        code = (
            'gmsh.model.addPhysicalGroup(3, [1])\n'
            'gmsh.model.mesh.generate(3)\n'
            'gmsh.write("output.msh")\n'
        )
        assert _run(check_missing_physical_groups, code) == []

    def test_skips_no_write(self):
        code = 'gmsh.model.mesh.generate(3)\n'
        assert _run(check_missing_physical_groups, code) == []


class TestMixingGeoAndOcc:
    def test_detects_mixing(self):
        code = (
            'gmsh.model.geo.addPoint(0, 0, 0, 0.1)\n'
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
        )
        findings = _run(check_mixing_geo_and_occ, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'
        assert findings[0]['rule'] == 'mixing-geo-and-occ'

    def test_allows_geo_only(self):
        code = (
            'gmsh.model.geo.addPoint(0, 0, 0, 0.1)\n'
            'gmsh.model.geo.addLine(1, 2)\n'
            'gmsh.model.geo.synchronize()\n'
        )
        assert _run(check_mixing_geo_and_occ, code) == []

    def test_allows_occ_only(self):
        code = (
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.model.occ.synchronize()\n'
        )
        assert _run(check_mixing_geo_and_occ, code) == []


class TestHardcodedAbsolutePath:
    def test_detects_windows_path(self):
        code = "sys.path.insert(0, r'D:\\myproject\\lib')"
        findings = _run(check_hardcoded_absolute_path, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'MODERATE'

    def test_allows_cubit_path(self):
        code = "sys.path.insert(0, r'C:\\Program Files\\Coreform Cubit 2024.3\\bin')"
        assert _run(check_hardcoded_absolute_path, code) == []

    def test_allows_ngsolve_path(self):
        code = "sys.path.insert(0, r'C:\\NGSolve\\lib')"
        assert _run(check_hardcoded_absolute_path, code) == []

    def test_allows_relative_path(self):
        code = "sys.path.insert(0, os.path.dirname(__file__))"
        assert _run(check_hardcoded_absolute_path, code) == []


class TestMshV4ForReadGmsh:
    def test_detects_v4_with_readgmsh(self):
        code = (
            'from netgen.read_gmsh import ReadGmsh\n'
            'gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)\n'
            'mesh = ReadGmsh("output.msh")\n'
        )
        findings = _run(check_msh_v4_for_readgmsh, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'MODERATE'

    def test_allows_v2_with_readgmsh(self):
        code = (
            'from netgen.read_gmsh import ReadGmsh\n'
            'gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)\n'
            'mesh = ReadGmsh("output.msh")\n'
        )
        assert _run(check_msh_v4_for_readgmsh, code) == []

    def test_skips_no_readgmsh(self):
        code = 'gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)\n'
        assert _run(check_msh_v4_for_readgmsh, code) == []


class TestGenerateBeforeSynchronize:
    def test_detects_generate_before_sync(self):
        code = (
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.model.mesh.generate(3)\n'
            'gmsh.model.occ.synchronize()\n'
        )
        findings = _run(check_generate_before_synchronize, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'

    def test_allows_sync_before_generate(self):
        code = (
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.model.occ.synchronize()\n'
            'gmsh.model.mesh.generate(3)\n'
        )
        assert _run(check_generate_before_synchronize, code) == []

    def test_skips_no_geo_ops(self):
        code = (
            'gmsh.open("mesh.msh")\n'
            'gmsh.model.mesh.generate(3)\n'
        )
        assert _run(check_generate_before_synchronize, code) == []


class TestUnitConversionInCoords:
    def test_detects_mm_to_m_conversion(self):
        code = 'gmsh.model.occ.addBox(0 * 0.001, 0 * 0.001, 0, 10 * 0.001, 5 * 0.001, 2 * 0.001)\n'
        findings = _run(check_unit_conversion_in_coords, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'MODERATE'

    def test_allows_direct_meters(self):
        code = 'gmsh.model.occ.addBox(0, 0, 0, 0.01, 0.005, 0.002)\n'
        assert _run(check_unit_conversion_in_coords, code) == []


class TestMissingModelAdd:
    def test_detects_missing_model_add(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
        )
        findings = _run(check_missing_model_add, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'MODERATE'

    def test_allows_with_model_add(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.add("test")\n'
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
        )
        assert _run(check_missing_model_add, code) == []

    def test_skips_no_gmsh(self):
        code = 'import numpy\n'
        assert _run(check_missing_model_add, code) == []


class TestSetorderBeforeGenerate:
    def test_detects_setorder_before_generate(self):
        code = (
            'gmsh.model.mesh.setOrder(2)\n'
            'gmsh.model.mesh.generate(3)\n'
        )
        findings = _run(check_setorder_before_generate, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'

    def test_allows_setorder_after_generate(self):
        code = (
            'gmsh.model.mesh.generate(3)\n'
            'gmsh.model.mesh.setOrder(2)\n'
        )
        assert _run(check_setorder_before_generate, code) == []


class TestWriteWithoutGenerate:
    def test_detects_write_without_generate(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)\n'
            'gmsh.write("output.msh")\n'
        )
        findings = _run(check_write_without_generate, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'

    def test_allows_with_generate(self):
        code = (
            'import gmsh\n'
            'gmsh.initialize()\n'
            'gmsh.model.mesh.generate(3)\n'
            'gmsh.write("output.msh")\n'
        )
        assert _run(check_write_without_generate, code) == []

    def test_allows_open_then_write(self):
        code = (
            'import gmsh\n'
            'gmsh.open("input.msh")\n'
            'gmsh.write("output.vtk")\n'
        )
        assert _run(check_write_without_generate, code) == []

    def test_skips_no_gmsh(self):
        code = 'with open("file.txt", "w") as f:\n    f.write("hello")\n'
        assert _run(check_write_without_generate, code) == []


class TestGmshUnicodePrint:
    def test_detects_unicode_in_print(self):
        code = 'print("Area = 5 m\u00b2")\n'
        findings = _run(check_gmsh_unicode_print, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'MODERATE'

    def test_allows_ascii_print(self):
        code = 'print("Area = 5 m^2")\n'
        assert _run(check_gmsh_unicode_print, code) == []

    def test_skips_non_print(self):
        code = 'label = "m\u00b2"\n'
        assert _run(check_gmsh_unicode_print, code) == []


# ============================================================
# Meta-tests
# ============================================================

class TestAllGmshRulesList:
    def test_all_rules_count(self):
        assert len(ALL_RULES) == 14

    def test_all_rules_callable(self):
        for rule in ALL_RULES:
            assert callable(rule)

    def test_clean_code_no_findings(self):
        """Clean code should produce zero findings across all rules."""
        clean = (
            'import numpy as np\n'
            'x = np.linspace(0, 1, 100)\n'
        )
        lines = clean.splitlines()
        for rule in ALL_RULES:
            findings = rule("clean.py", lines)
            assert findings == [], f"{rule.__name__} fired on clean code"
