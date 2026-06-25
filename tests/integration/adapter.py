"""df_honey → run_input 어댑터 (eval_engine 밖).

불변 규칙 1: eval_engine 은 report_server 를 import 하지 않는다. 이 어댑터는 호출자
(report_server) 쪽 코드 — df_honey 객체의 속성만 읽어 중립 dict(run_input)으로 변환한다.
실제 결합 시 이 함수를 report_server 의 report_generator 파이프라인 끝에 둔다
(HANDOFF_TO_REPORT_SERVER 의 build_run_input 역할). eval_engine 은 import 하지 않는다.
"""
import math


def _nan_to_none(x):
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


def df_honey_to_run_input(honey, meta_override=None):
    subjects = list(honey.subjects)
    units = dict(zip(subjects, honey.units))
    lower = {s: _nan_to_none(v) for s, v in zip(subjects, honey.lower_limits)}
    upper = {s: _nan_to_none(v) for s, v in zip(subjects, honey.upper_limits)}
    meta_df = honey.meta            # DUT/XCoord/YCoord/Bin/Serial
    scores = honey.numeric_scores   # 행=DUT, 열=subject idx

    rows = []
    for i in range(len(scores)):
        bin_raw = meta_df.iat[i, 3]
        try:
            bin_ = int(float(bin_raw))
        except (TypeError, ValueError):
            bin_ = 1                 # PASS_BIN fallback
        row = {"DUT": meta_df.iat[i, 0],
               "XCoord": _nan_to_none(meta_df.iat[i, 1]),
               "YCoord": _nan_to_none(meta_df.iat[i, 2]),
               "Bin": bin_,
               "Serial": meta_df.iat[i, 4]}
        for j, s in enumerate(subjects):
            val = scores.iat[i, j]
            row[s] = _nan_to_none(float(val)) if val == val else None  # NaN!=NaN
        rows.append(row)

    raw_table = {"meta_columns": ["DUT", "XCoord", "YCoord", "Bin", "Serial"],
                 "item_columns": subjects, "units": units,
                 "lower_limit": lower, "upper_limit": upper, "rows": rows}

    meta = {"product_name": "MASS_HUGE_TEST", "product_type": "PMIC", "revision": "EVT0",
            "lot_id": "MASS_LOT", "wafer_number": "W01", "family_product": "SOC PMIC",
            "source_file": "mass_huge_W01.csv", "ingested_by": "integration_test"}
    if meta_override:
        meta.update(meta_override)
    return {"meta": meta, "raw_table": raw_table}
