"""L3 signatures + L4 status 단독 테스트.

signatures.evaluate 는 DB 미접근(bin_taxonomy 는 rules yaml 조회) — DB fixture 불필요.
"""
from eval_engine.pipeline import signatures, status


def _case(**kw):
    c = {"product_type": None, "item_class": None, "bin": 99}
    c.update(kw)
    return c


def _full_features(**kw):
    """공간 feature 포함(full completeness) 기본 features."""
    f = {"spread_norm": 0.05, "skewness": 0.1, "kurtosis": 0.0, "outlier_ratio": 0.0,
         "spec_margin_low": 5.0, "spec_margin_high": 5.0, "site_cpk_delta": 0.0,
         "edge_fail_ratio": 1.0, "n_dut": 100}
    f.update(kw)
    return f


def test_gross_fail_fires_on_low_yield():
    case = _case()
    feats = _full_features()
    raw = {"yield": 0.3, "cpk": 1.5}
    sig = signatures.evaluate(case, feats, raw)
    ids = [s["id"] for s in sig["signatures"]]
    assert "GROSS_FAIL" in ids
    verdict = status.decide(case, feats, sig)
    assert verdict["status"] == "CRITICAL"


def test_severe_outlier_fires():
    case = _case()
    feats = _full_features(outlier_ratio=0.10)  # > outlier_ratio_bad(0.05)
    raw = {"yield": 0.95, "cpk": 1.5}
    sig = signatures.evaluate(case, feats, raw)
    assert "SEVERE_OUTLIER" in [s["id"] for s in sig["signatures"]]


def test_tail_risk_disabled_when_few_samples():
    case = _case()
    # skewness 큼 + spec margin 작음 → 정상이면 TAIL_RISK 발화. 단 n_dut < n_min 이면 비활성
    feats = _full_features(skewness=2.0, spec_margin_low=0.5, n_dut=5)
    raw = {"yield": 0.95, "cpk": 1.5}
    sig = signatures.evaluate(case, feats, raw)
    assert "TAIL_RISK" not in [s["id"] for s in sig["signatures"]]


def test_tail_risk_fires_with_enough_samples():
    case = _case()
    feats = _full_features(skewness=2.0, spec_margin_low=0.5, n_dut=100)
    raw = {"yield": 0.95, "cpk": 1.5}
    sig = signatures.evaluate(case, feats, raw)
    assert "TAIL_RISK" in [s["id"] for s in sig["signatures"]]


def test_specificity_picks_equipment_over_general():
    case = _case()
    # WIDE_DISTRIBUTION(일반) + EQUIPMENT_SUSPECT(구체) 동시 발화 → primary=EQUIPMENT
    feats = _full_features(spread_norm=0.5, site_cpk_delta=0.8)
    raw = {"yield": 0.95, "cpk": 1.5}
    sig = signatures.evaluate(case, feats, raw)
    ids = [s["id"] for s in sig["signatures"]]
    assert "EQUIPMENT_SUSPECT" in ids and "WIDE_DISTRIBUTION" in ids
    verdict = status.decide(case, feats, sig)
    assert verdict["primary_signature"] == "EQUIPMENT_SUSPECT"


def test_trump_low_cpk_low_yield_forces_critical():
    case = _case()
    feats = _full_features()  # 발화 signature 없음 → 기본 MONITOR
    raw = {"yield": 0.6, "cpk": 0.5}  # cpk<cpk_bad(1.0) AND yield<floor(0.7)
    sig = signatures.evaluate(case, feats, raw)
    verdict = status.decide(case, feats, sig)
    assert verdict["status"] == "CRITICAL"


def test_data_completeness_levels():
    case = _case()
    raw = {"yield": 0.95, "cpk": 1.5}
    # full: 공간 있고 n_dut 충분
    v_full = status.decide(case, _full_features(n_dut=100), signatures.evaluate(
        case, _full_features(n_dut=100), raw))
    assert v_full["data_completeness"] == "full"
    # partial: 공간 없음
    feats_p = _full_features(n_dut=100, edge_fail_ratio=None)
    v_part = status.decide(case, feats_p, signatures.evaluate(case, feats_p, raw))
    assert v_part["data_completeness"] == "partial"
    # low: n_dut=0
    feats_l = _full_features(n_dut=0, edge_fail_ratio=None)
    v_low = status.decide(case, feats_l, signatures.evaluate(case, feats_l, raw))
    assert v_low["data_completeness"] == "low"


def test_no_signature_gives_monitor():
    case = _case()
    feats = _full_features()
    raw = {"yield": 0.99, "cpk": 2.0}
    sig = signatures.evaluate(case, feats, raw)
    assert sig["signatures"] == []
    verdict = status.decide(case, feats, sig)
    assert verdict["status"] == "MONITOR"
    assert verdict["primary_signature"] is None
