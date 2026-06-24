"""L2 Feature — robust 산포/spec margin/공간 판단지표 계산.

공식: docs/CODE_TO_PORT §5 (spread_norm/outlier_ratio/skewness/kurtosis/density_gap/cdf_gap,
  spec_margin_low/high/nearest_spec_side/limit_hit_ratio, edge/center/radial/quadrant/x/y gradient,
  wafer_zone_signature, n_dut, site_cpk_delta, code_edge_hit).
원칙: estimator=표준 robust(MAD 등), 임계값 하드코딩 금지(calibration). 결측은 None(룰 applies=False).
좌표/site 없으면 공간/ site feature 는 None.
반환: features dict (DB_SCHEMA §5 컬럼) — engine_version 별.
"""


def compute(case_ctx: dict, raw_metrics: dict, engine_version: str) -> dict:
    raise NotImplementedError("docs/CODE_TO_PORT §5 feature 공식 구현")
