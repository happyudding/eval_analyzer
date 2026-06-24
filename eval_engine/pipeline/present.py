"""L6 Present — 결과 직렬화 + eval.db 적재.

persist: raw_metrics/features/evaluation/eval_evidence/case_signature 저장(store CRUD).
  ※ raw(per-DUT)는 저장 안 함 — m/f 의 계산값만.
to_result: RunResult.cases[i] dict (docs/INTEGRATION_CONTRACT §4).
"""
from .. import store


def persist(run_ctx, case_ctx, raw_metrics, features, verdict, sig_result, comment,
            engine_version, model_version):
    raise NotImplementedError("store CRUD 로 저장 구현 (raw 미저장)")


def to_result(case_ctx, verdict, sig_result, comment, precedents) -> dict:
    raise NotImplementedError("INTEGRATION_CONTRACT §4 형식으로 직렬화")
