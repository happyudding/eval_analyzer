"""신규 raw df 포맷(REPORT_GENERATOR_DATA_REQUEST) ingest 테스트.

레이아웃: columns[:7]=meta(SERIAL,SHOT,DUT,XPOS,YPOS,BIN,FAILTNO), [7:]=item.
row0 TSEQ / row1 TNO / row2 STEP / row3 UNIT / row4 HILIM / row5 LOLIM / row6+ 측정.
fail 식별 = FAILTNO(serial이 fail한 test의 TNO) == item의 TNO.
"""
import math

import pandas as pd

from eval_engine import api, store
from eval_engine.pipeline import ingest

_COLS = ["SERIAL", "SHOT", "DUT", "XPOS", "YPOS", "BIN", "FAILTNO", "VREF_TRIM", "IDDQ"]
_VREF_TNO, _IDDQ_TNO = 101, 202


def _new_df(n_pass=20, n_fail=4):
    """VREF_TRIM 이 n_fail 개 serial 에서 fail(FAILTNO=101, bin18, edge). IDDQ 는 무fail."""
    nan = float("nan")
    meta_rows = [
        ["TSEQ", None, None, None, None, None, None, 1, 2],
        ["TNO", None, None, None, None, None, None, _VREF_TNO, _IDDQ_TNO],
        ["STEP", None, None, None, None, None, None, "P2", "P1"],
        ["UNIT", None, None, None, None, None, None, "V", "A"],
        ["HILIM", None, None, None, None, None, None, 1.4, 15.0],
        ["LOLIM", None, None, None, None, None, None, 1.0, nan],
    ]
    data_rows = []
    s = 1
    for i in range(n_pass):  # pass: bin1, 중앙부, spec 내, FAILTNO 없음
        data_rows.append([s, 1, s, i % 5, i // 5, 1, nan,
                          1.20 + 0.01 * (i % 3), 12.0 + 0.01 * (i % 4)])
        s += 1
    for i in range(n_fail):  # fail: VREF_TRIM(FAILTNO=101), bin18, edge, usl 초과
        data_rows.append([s, 1, s, 50 + i, 50 + i, 18, _VREF_TNO,
                          1.55 + 0.02 * i, 12.1])
        s += 1
    return pd.DataFrame(meta_rows + data_rows, columns=_COLS)


def _meta():
    return {"product_name": "S5E_TEST_0000001", "family_product": "SOC",
            "product_type": "PMIC", "revision": 0.0, "lot_id": "LOT001",
            "wafer_number": 3}


def test_raw_df_fail_mapping_no_persist():
    run = {"meta": _meta(), "raw_df": _new_df()}
    ctx = ingest.ingest(run, persist=False)
    cases = ctx["cases"]
    # VREF_TRIM 만 fail(FAILTNO=101), IDDQ 는 무fail → case 1개(bin18)
    assert len(cases) == 1
    c = cases[0]
    assert c["item_canonical"] == "vref_trim"
    assert c["bin"] == 18
    assert c["value_type"] == "V"
    assert c["lsl"] == 1.0 and c["usl"] == 1.4
    # 분포는 전체 serial(측정된 값) 기준, fail_mask 는 4개만 True
    assert len(c["values"]) == 24
    assert sum(1 for f in c["fail_mask"] if f) == 4
    # 공간: fail serial 은 edge 좌표
    assert all(x is not None for x in c["x_pos"])


def test_raw_df_e2e_fires_signature(fresh_db):
    result = api.evaluate({"meta": _meta(), "raw_df": _new_df()}, persist=True)
    assert result["run_id"] is not None
    cases = [c for c in result["cases"] if c["bin"] == 18]
    assert len(cases) == 1
    case = cases[0]
    assert case["item_canonical"] == "vref_trim"
    assert case["status"] in {"MAJOR", "CRITICAL"}
    assert case["primary_signature"] is not None
    with store.get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM fail_case").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM features").fetchone()[0] >= 1


def test_raw_df_failtno_blank_is_pass():
    """FAILTNO 공란/NaN serial 은 fail 로 잡히지 않는다(무fail df → case 0)."""
    df = _new_df(n_pass=24, n_fail=0)
    ctx = ingest.ingest({"meta": _meta(), "raw_df": df}, persist=False)
    assert ctx["cases"] == []
