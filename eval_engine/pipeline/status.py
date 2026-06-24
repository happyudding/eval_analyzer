"""L4 Status — 발화 signature/evidence → status/confidence/data_completeness.

규칙(docs 본문):
  - severity 가중합 → 구간 매핑(MONITOR/MINOR/MAJOR/CRITICAL) 기본.
  - trump 규칙: 예 cpk<1.0 AND 불량률>임계 → CRITICAL 우선.
  - specificity 충돌해소: 구체 signature(EQUIPMENT_SUSPECT 등) > 일반(LOW_CPK). 지배 signature=primary.
  - bin_class(defective/abnormal) 로 status_hint 변조(severity_bias).
  - data_completeness: cpk/산포 결측 정도(full/partial/low). 결측 많으면 confidence↓.
반환: {"status", "primary_signature", "secondary_signatures":[...], "confidence",
       "data_completeness", "evidence":[{signal_code,value,weight}...]}
"""


def decide(case_ctx: dict, features: dict, sig_result: dict) -> dict:
    raise NotImplementedError("severity 집계 + trump + specificity 구현")
