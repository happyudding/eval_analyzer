"""오프라인 보정 — 누적 데이터에서 임계값(분위수) 산출 + comment 채굴.

docs(설계 본문):
  1. 분위수 보정: features/raw_metrics 를 item_class/product_type 별로 모아 분위수 →
     rules/thresholds.yaml 갱신(estimator 표준값은 cold-start 시드).
  2. comment 채굴: label.human_comment + case_outcome 군집 → signature 후보/키워드 사전.
  3. 검증: 룰 high-severity 판정 vs 실제 label/outcome 비교(precision/recall 유사).
출력: thresholds.yaml(갱신) + engine_version_registry 신규 버전 등록(파일 ref+hash).
"""
from . import store, config


def recalibrate(*, product_type=None) -> dict:
    raise NotImplementedError("분위수 보정 + thresholds.yaml 갱신 구현")
