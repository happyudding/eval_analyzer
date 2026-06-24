"""L1 Metric — per fail item raw(메모리)에서 표준 통계 계산. raw 자체는 저장 안 함.

공식: docs/CODE_TO_PORT §2 (cpk/cpl/cpu/cp/mean/stdev/min/max), yield/fail_count/total_count, bimodality.
반환: raw_metrics dict (DB_SCHEMA §4 컬럼). 결측(n<=1, limit 없음)이면 cpk 류 None.
"""


def compute(case_ctx: dict) -> dict:
    raise NotImplementedError("docs/CODE_TO_PORT §2 cpk_summary 재구현")
