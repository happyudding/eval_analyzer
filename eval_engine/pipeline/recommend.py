"""L5 Recommend — 룰 골격 + 선례(precedent) + LLM 합성 → 분석방향 comment.

find_precedents: docs/DB_SCHEMA §9 — (bin + value_type + item명 퍼지≥config.PRECEDENT_NAME_SIMILARITY)
  로 과거 case_outcome/label 회수. store.search_precedents(...) 사용.
make_comment:
  - 입력: verdict(status/signature) + evidence + 선례(action/condition/result/comment).
  - LLM off(config.EVAL_LLM_ENABLED=False) 또는 실패 → 룰/선례 기반 **템플릿 코멘트** fallback.
  - LLM on → llm_client.complete(prompt) 로 자연어 합성(모델은 사용자 지정).
  - 예: "site 3 에서만 튐, golden unit 재측정 권장 (과거 retest→정상 이력)".
"""
from .. import store, config
from .. import llm_client


def find_precedents(case_ctx: dict, sig_result: dict) -> list:
    raise NotImplementedError("store.search_precedents (DB_SCHEMA §9) 구현")


def make_comment(case_ctx: dict, verdict: dict, sig_result: dict, precedents: list,
                 *, model_version: str | None = None) -> str:
    raise NotImplementedError("템플릿 fallback + (옵션) LLM 합성 구현")
