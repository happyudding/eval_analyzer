"""L3 Signature — feature 조합 → 발화 signature. 선언형 rules/signatures.yaml + thresholds.yaml.

할 일:
  1. thresholds.yaml 로드(item_class/product_type override). 임계값은 여기서만(코드 아님).
  2. Layer1 단위룰(LOW_CPK/OUTLIER_RATIO/...) 발화 + reason_codes(=eval_evidence 후보).
  3. Layer2 signature(signatures.yaml when_all/when_metric/scope) 평가 → 발화 signature 목록.
  4. 결측(feature None) → 해당 룰 applies=False (양호로 오판 금지).
  5. bin_taxonomy 로 bin_class 조회 → status_hint 변조 컨텍스트 첨부.
룰 스코프 = item_class(category_major|value_type|bin). 임계 정규화+분위수.
반환: {"signatures":[{id, role?, score, evidence:[...]}], "reason_codes":[...], "bin_class":..., "applies":{...}}
"""


def evaluate(case_ctx: dict, features: dict, raw_metrics: dict) -> dict:
    raise NotImplementedError("rules/*.yaml 로드 + 선언형 평가 구현")
