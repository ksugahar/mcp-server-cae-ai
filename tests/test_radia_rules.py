"""Tests for Radia lint rules.

Each test provides intentionally bad code and verifies the rule fires,
then provides correct code and verifies no findings.
"""

import pytest
from mcp_server_cae_ai.radia.rules import (
    ALL_RULES,
    check_objbckg_no_lambda,
    check_missing_utidelall,
    check_hardcoded_absolute_paths,
    check_removed_fldunits,
    check_removed_fldbatch,
    check_removed_solver_apis,
    check_docstring_hardcoded_mm,
    check_build_release_path,
    check_bessel_jv_for_sibc,
    check_peec_low_nseg,
    check_efie_v_minus_sign,
    check_classical_efie_breakdown,
    check_peec_p_over_jw,
    check_hcurl_missing_nograds,
    check_ngsolve_precond_after_assemble,
    check_ngsolve_missing_trace_bem,
    check_ngsolve_overwrite_xyz,
    check_ngsolve_vec_assign,
    check_ngsolve_dim2_occ,
    check_ngsolve_cg_on_saddle_point,
    check_ngsolve_vectorh1_for_em,
    check_ngsolve_pinvit_no_projection,
    check_eddy_current_missing_complex,
    check_joule_heat_missing_conj,
    check_ngsolve_kelvin_missing_bonus_intorder,
)


# ============================================================
# Helper
# ============================================================

def _run(rule_func, code: str, filepath: str = "test_script.py"):
    lines = code.splitlines()
    return rule_func(filepath, lines)


# ============================================================
# Radia rules
# ============================================================

class TestObjBckgNoLambda:
    def test_detects_list_arg(self):
        code = 'bkg = rad.ObjBckg([0, 0, 0.1])'
        findings = _run(check_objbckg_no_lambda, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'
        assert findings[0]['rule'] == 'objbckg-needs-callable'

    def test_allows_lambda(self):
        code = 'bkg = rad.ObjBckg(lambda p: [0, 0, 0.1])'
        assert _run(check_objbckg_no_lambda, code) == []

    def test_allows_function_ref(self):
        code = 'bkg = rad.ObjBckg(my_field_func)'
        assert _run(check_objbckg_no_lambda, code) == []


class TestMissingUtiDelAll:
    def test_detects_missing_cleanup(self):
        code = (
            'import radia as rad\n'
            'if __name__ == "__main__":\n'
            '    pm = rad.ObjRecMag([0,0,0], [0.1,0.1,0.1], [0,0,1])\n'
        )
        findings = _run(check_missing_utidelall, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'

    def test_ok_with_cleanup(self):
        code = (
            'import radia as rad\n'
            'if __name__ == "__main__":\n'
            '    pm = rad.ObjRecMag([0,0,0], [0.1,0.1,0.1], [0,0,1])\n'
            '    rad.UtiDelAll()\n'
        )
        assert _run(check_missing_utidelall, code) == []

    def test_skips_non_radia(self):
        code = (
            'import numpy\n'
            'if __name__ == "__main__":\n'
            '    pass\n'
        )
        assert _run(check_missing_utidelall, code) == []

    def test_skips_init_py(self):
        code = (
            'import radia as rad\n'
            'if __name__ == "__main__":\n'
            '    pass\n'
        )
        assert _run(check_missing_utidelall, code, filepath="__init__.py") == []


class TestHardcodedAbsolutePaths:
    def test_detects_windows_path(self):
        code = "sys.path.insert(0, r'S:\\Radia\\src')"
        findings = _run(check_hardcoded_absolute_paths, code)
        assert len(findings) == 1

    def test_allows_relative_path(self):
        code = "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/radia'))"
        assert _run(check_hardcoded_absolute_paths, code) == []

    def test_skips_comments(self):
        code = "# sys.path.insert(0, r'C:\\foo')"
        assert _run(check_hardcoded_absolute_paths, code) == []

    def test_detects_repo_root_assignment(self):
        code = "repo_root = r'D:\\projects\\radia'"
        findings = _run(check_hardcoded_absolute_paths, code)
        assert len(findings) == 1


class TestRemovedFldUnits:
    def test_detects_fldunits(self):
        code = 'rad.FldUnits("mm")'
        findings = _run(check_removed_fldunits, code)
        assert len(findings) == 1
        assert findings[0]['rule'] == 'removed-fldunits'

    def test_detects_bare_fldunits(self):
        code = 'FldUnits("mm")'
        findings = _run(check_removed_fldunits, code)
        assert len(findings) == 1

    def test_allows_clean_code(self):
        code = 'B = rad.Fld(obj, "b", [0,0,0])'
        assert _run(check_removed_fldunits, code) == []

    def test_skips_comments(self):
        code = '# rad.FldUnits() is removed'
        assert _run(check_removed_fldunits, code) == []


class TestRemovedFldBatch:
    def test_detects_fldbatch(self):
        code = 'result = rad.FldBatch(mag, pts)'
        findings = _run(check_removed_fldbatch, code)
        assert len(findings) == 1
        assert findings[0]['rule'] == 'removed-fldbatch'

    def test_detects_flda(self):
        code = 'A = rad.FldA(mag, pts)'
        findings = _run(check_removed_fldbatch, code)
        assert len(findings) == 1

    def test_detects_fldphi(self):
        code = 'phi = rad.FldPhi(mag, pts)'
        findings = _run(check_removed_fldbatch, code)
        assert len(findings) == 1

    def test_allows_unified_fld(self):
        code = 'B = rad.Fld(mag, "b", pts)'
        assert _run(check_removed_fldbatch, code) == []

    def test_skips_comments(self):
        code = '# FldBatch is removed'
        assert _run(check_removed_fldbatch, code) == []


class TestRemovedSolverApis:
    def test_detects_sethacapkparams(self):
        code = 'rad.SetHACApKParams(1e-4, 10, 2.0)'
        findings = _run(check_removed_solver_apis, code)
        assert len(findings) == 1
        assert findings[0]['rule'] == 'removed-solver-api'

    def test_detects_setbicgstabtol(self):
        code = 'rad.SetBiCGSTABTol(1e-6)'
        findings = _run(check_removed_solver_apis, code)
        assert len(findings) == 1

    def test_detects_setrelaxparam(self):
        code = 'rad.SetRelaxParam(0.3)'
        findings = _run(check_removed_solver_apis, code)
        assert len(findings) == 1

    def test_detects_setnewtonmethod(self):
        code = 'rad.SetNewtonMethod(True)'
        findings = _run(check_removed_solver_apis, code)
        assert len(findings) == 1

    def test_allows_solverconfig(self):
        code = 'rad.SolverConfig(hacapk_eps=1e-4)'
        assert _run(check_removed_solver_apis, code) == []

    def test_skips_comments(self):
        code = '# rad.SetHACApKParams is replaced by SolverConfig'
        assert _run(check_removed_solver_apis, code) == []


class TestDocstringHardcodedMm:
    def test_detects_in_src_radia(self):
        code = '"""\n    point coordinates in mm\n"""'
        findings = _run(check_docstring_hardcoded_mm, code,
                       filepath="src/radia/field.py")
        assert len(findings) == 1

    def test_ignores_non_src(self):
        code = '"""\n    point coordinates in mm\n"""'
        assert _run(check_docstring_hardcoded_mm, code,
                    filepath="examples/demo.py") == []


class TestBuildReleasePath:
    def test_detects_old_path(self):
        code = "sys.path.insert(0, 'build/Release')"
        findings = _run(check_build_release_path, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'LOW'

    def test_allows_src_radia(self):
        code = "sys.path.insert(0, 'src/radia')"
        assert _run(check_build_release_path, code) == []


class TestBesselJvForSibc:
    def test_detects_jv_in_sibc_context(self):
        code = (
            '# SIBC calculation\n'
            'from scipy.special import jv\n'
            'Z = jv(0, ka) / jv(1, ka)\n'
        )
        findings = _run(check_bessel_jv_for_sibc, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'
        assert findings[0]['rule'] == 'bessel-jv-not-iv'

    def test_allows_iv(self):
        code = (
            '# SIBC calculation\n'
            'from scipy.special import iv\n'
            'Z = iv(0, ka) / iv(1, ka)\n'
        )
        assert _run(check_bessel_jv_for_sibc, code) == []

    def test_allows_jv_in_non_sibc(self):
        code = (
            'from scipy.special import jv\n'
            'y = jv(0, x)\n'
        )
        assert _run(check_bessel_jv_for_sibc, code) == []

    def test_allows_both_imported(self):
        code = (
            '# SIBC calculation\n'
            'from scipy.special import iv, jv\n'
        )
        assert _run(check_bessel_jv_for_sibc, code) == []


class TestPeecLowNseg:
    def test_detects_low_nseg(self):
        code = (
            '# PEEC coil model\n'
            'n_seg = 16\n'
        )
        findings = _run(check_peec_low_nseg, code)
        assert len(findings) == 1
        assert 'n_seg=16' in findings[0]['message']

    def test_allows_high_nseg(self):
        code = (
            '# PEEC coil model\n'
            'n_seg = 64\n'
        )
        assert _run(check_peec_low_nseg, code) == []

    def test_skips_non_peec(self):
        code = 'segments = 4\n'
        assert _run(check_peec_low_nseg, code) == []


class TestEfieVMinusSign:
    def test_detects_minus_sign(self):
        code = (
            '# ShieldBEMSIBC solver\n'
            'Z_LL = Zs * M_LL - 1j * omega * mu_0 * V_LL\n'
        )
        findings = _run(check_efie_v_minus_sign, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'

    def test_allows_plus_sign(self):
        code = (
            '# ShieldBEMSIBC solver\n'
            'Z_LL = Zs * M_LL + 1j * omega * mu_0 * V_LL\n'
        )
        assert _run(check_efie_v_minus_sign, code) == []


class TestClassicalEfieBreakdown:
    def test_detects_one_over_kappa_squared(self):
        code = (
            'from ngbem import HelmholtzSL\n'
            'P = 1 / kappa ** 2 * V_SL\n'
        )
        findings = _run(check_classical_efie_breakdown, code)
        assert len(findings) == 1

    def test_allows_stabilized(self):
        code = (
            'from ngbem import HelmholtzSL\n'
            'P = kappa ** 2 * V_SL\n'
        )
        assert _run(check_classical_efie_breakdown, code) == []


class TestPeecPOverJw:
    def test_detects_p_over_jw(self):
        code = (
            '# Loop-Star PEEC\n'
            'Z_SS = self.P / (1j * omega)\n'
        )
        findings = _run(check_peec_p_over_jw, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'

    def test_allows_reformulated(self):
        code = (
            '# Loop-Star PEEC\n'
            'Z_SS = 1j * omega * P_inv_MLS\n'
        )
        assert _run(check_peec_p_over_jw, code) == []

    def test_skips_docstrings(self):
        code = (
            '# Loop-Star PEEC\n'
            '"""\n'
            'Z_SS = self.P / (1j * omega)  # old formula\n'
            '"""\n'
        )
        assert _run(check_peec_p_over_jw, code) == []


# ============================================================
# NGSolve rules
# ============================================================

class TestHCurlMissingNograds:
    def test_detects_hcurl_without_nograds(self):
        code = (
            '# magnetostatic solver\n'
            'fes = HCurl(mesh, order=2)\n'
        )
        findings = _run(check_hcurl_missing_nograds, code)
        assert len(findings) == 1

    def test_allows_nograds_true(self):
        code = (
            '# magnetostatic solver\n'
            'fes = HCurl(mesh, order=2, nograds=True)\n'
        )
        assert _run(check_hcurl_missing_nograds, code) == []

    def test_allows_complex(self):
        code = (
            '# magnetostatic solver\n'
            'fes = HCurl(mesh, order=2, complex=True)\n'
        )
        assert _run(check_hcurl_missing_nograds, code) == []


class TestNgsolvePrecondAfterAssemble:
    def test_detects_late_precond(self):
        code = (
            'a.Assemble()\n'
            'pre = Preconditioner(a, "bddc")\n'
        )
        findings = _run(check_ngsolve_precond_after_assemble, code)
        assert len(findings) == 1

    def test_allows_precond_before_assemble(self):
        code = (
            'pre = Preconditioner(a, "bddc")\n'
            'a.Assemble()\n'
        )
        assert _run(check_ngsolve_precond_after_assemble, code) == []


class TestNgsolveMissingTraceBem:
    def test_detects_missing_trace(self):
        code = (
            'fes = HDivSurface(mesh, order=1)\n'
            'u, v = fes.TnT()\n'
            'a = BilinearForm(LaplaceSL(3) * u * v * ds)\n'
        )
        findings = _run(check_ngsolve_missing_trace_bem, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'CRITICAL'

    def test_allows_trace(self):
        code = (
            'fes = HDivSurface(mesh, order=1)\n'
            'u, v = fes.TnT()\n'
            'a = BilinearForm(LaplaceSL(3) * u.Trace() * v.Trace() * ds)\n'
        )
        assert _run(check_ngsolve_missing_trace_bem, code) == []


class TestNgsolveOverwriteXyz:
    def test_detects_for_x_in(self):
        code = (
            'from ngsolve import *\n'
            'for x in range(10):\n'
            '    pass\n'
        )
        findings = _run(check_ngsolve_overwrite_xyz, code)
        assert len(findings) == 1
        assert 'overwrites' in findings[0]['message']

    def test_allows_for_xi_in(self):
        code = (
            'from ngsolve import *\n'
            'for xi in range(10):\n'
            '    pass\n'
        )
        assert _run(check_ngsolve_overwrite_xyz, code) == []

    def test_skips_non_ngsolve(self):
        code = 'for x in range(10):\n    pass\n'
        assert _run(check_ngsolve_overwrite_xyz, code) == []


class TestNgsolveVecAssign:
    def test_detects_bad_assign(self):
        code = (
            'from ngsolve import *\n'
            'gfu.vec = f.vec\n'
        )
        findings = _run(check_ngsolve_vec_assign, code)
        assert len(findings) == 1

    def test_allows_data_assign(self):
        code = (
            'from ngsolve import *\n'
            'gfu.vec.data = f.vec\n'
        )
        assert _run(check_ngsolve_vec_assign, code) == []


class TestNgsolveDim2Occ:
    def test_detects_missing_dim2(self):
        code = (
            'shape = Rectangle(1, 1).Face()\n'
            'geo = OCCGeometry(shape)\n'
        )
        findings = _run(check_ngsolve_dim2_occ, code)
        assert len(findings) == 1

    def test_allows_dim2(self):
        code = (
            'shape = Rectangle(1, 1).Face()\n'
            'geo = OCCGeometry(shape, dim=2)\n'
        )
        assert _run(check_ngsolve_dim2_occ, code) == []


class TestNgsolveCgOnSaddlePoint:
    def test_detects_cg_on_saddle(self):
        code = (
            'fes = fesA * fesOmega\n'
            'gfu = solvers.CG(a.mat, rhs.vec)\n'
        )
        findings = _run(check_ngsolve_cg_on_saddle_point, code)
        assert len(findings) == 1

    def test_allows_gmres(self):
        code = (
            'fes = fesA * fesOmega\n'
            'gfu = solvers.GMRes(a.mat, rhs.vec)\n'
        )
        assert _run(check_ngsolve_cg_on_saddle_point, code) == []


class TestNgsolveVectorH1ForEm:
    def test_detects_vectorh1_em(self):
        code = (
            '# magnetostatic simulation\n'
            'fes = VectorH1(mesh, order=2)\n'
        )
        findings = _run(check_ngsolve_vectorh1_for_em, code)
        assert len(findings) == 1

    def test_allows_non_em(self):
        code = (
            '# structural mechanics\n'
            'fes = VectorH1(mesh, order=2)\n'
        )
        assert _run(check_ngsolve_vectorh1_for_em, code) == []


class TestNgsolvePinvitNoProjection:
    def test_detects_no_projection(self):
        code = (
            'fes = HCurl(mesh, order=2)\n'
            'evals, evecs = solvers.PINVIT(a.mat, m.mat, pre, num=10)\n'
        )
        findings = _run(check_ngsolve_pinvit_no_projection, code)
        assert len(findings) == 1

    def test_allows_with_projection(self):
        code = (
            'fes = HCurl(mesh, order=2)\n'
            'gradmat = fes.CreateGradient()\n'
            'evals, evecs = solvers.PINVIT(a.mat, m.mat, pre, num=10)\n'
        )
        assert _run(check_ngsolve_pinvit_no_projection, code) == []


class TestEddyCurrentMissingComplex:
    def test_detects_missing_complex(self):
        code = (
            '# eddy current simulation\n'
            'fes = HCurl(mesh, order=2)\n'
        )
        findings = _run(check_eddy_current_missing_complex, code)
        assert len(findings) == 1
        assert findings[0]['severity'] == 'HIGH'

    def test_allows_complex_true(self):
        code = (
            '# eddy current simulation\n'
            'fes = HCurl(mesh, order=2, complex=True)\n'
        )
        assert _run(check_eddy_current_missing_complex, code) == []

    def test_skips_thermal(self):
        code = (
            '# eddy current simulation\n'
            'fes_T = H1(mesh, order=2)  # temperature\n'
        )
        assert _run(check_eddy_current_missing_complex, code) == []


class TestJouleHeatMissingConj:
    def test_detects_missing_conj(self):
        code = 'Q = sigma * InnerProduct(E, E)'
        findings = _run(check_joule_heat_missing_conj, code)
        assert len(findings) == 1

    def test_allows_conj(self):
        code = 'Q = 0.5 * sigma * InnerProduct(E, Conj(E)).real'
        assert _run(check_joule_heat_missing_conj, code) == []


class TestKelvinMissingBonusIntorder:
    def test_detects_missing_bonus(self):
        code = 'a += mu * curl(u) * curl(v) * dx("Kelvin")'
        findings = _run(check_ngsolve_kelvin_missing_bonus_intorder, code)
        assert len(findings) == 1

    def test_allows_bonus(self):
        code = 'a += mu * curl(u) * curl(v) * dx("Kelvin", bonus_intorder=4)'
        assert _run(check_ngsolve_kelvin_missing_bonus_intorder, code) == []


# ============================================================
# Meta-tests
# ============================================================

class TestAllRulesList:
    def test_all_rules_count(self):
        assert len(ALL_RULES) == 29

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
