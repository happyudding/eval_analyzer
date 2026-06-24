# report_server ↔ eval_analyzer 연동 계약

> 별도 프로젝트지만 **같이 움직인다**: client 가 파일을 1회 run 할 때마다 eval_analyzer 가 작동.
> 의존 방향은 **report_server → eval_analyzer 한 방향**(report_server 가 eval_analyzer 를 import 해 호출).
> **eval_analyzer 는 report_server 를 절대 import 하지 않는다.**

---

## 1. 트리거 지점
- report_server 의 `report_generator` 파이프라인이 raw 측정을 처리해 리포트를 만드는 시점
  (df_honey 로 raw 가 메모리에 올라온 직후, 한 파일/세션당 1회).
- 그 시점에 report_server 가 `eval_analyzer.evaluate(run_input)` 를 호출.
- eval_analyzer 는 결과를 **자체 eval.db** 에 적재하고 결과 dict 를 반환. report_server 는
  반환값을 UI 표시에 쓰거나 무시 가능(저장 주인은 eval_analyzer).

## 2. evaluate() 시그니처
```python
# eval_engine/api.py
def evaluate(run_input: dict, *, engine_version: str | None = None,
             model_version: str | None = None, persist: bool = True) -> dict:
    """한 세션(파일 1회 run)의 fail item 들을 평가.
    - run_input: §3 형식 (meta + raw_table). report_server 가 구성해 넘김.
    - persist=True 면 eval.db 에 ingest_run/fail_case/raw_metrics/features/evaluation 적재.
    - 반환: §4 RunResult dict.
    """
```

## 3. 입력 — run_input (plain dict, pandas/df_honey 의존 없음)
report_server 가 df_honey 에서 아래 **중립 dict** 로 변환해 전달(eval_analyzer 는 내부에서
자체 numpy/pandas 로 재구성. df_honey 객체를 직접 받지 않는다 — 결합 분리).
```python
run_input = {
  "meta": {
     "product_name": "S5E_XXXX_13",     # EDS 13자리
     "family_product": "SOC PMIC",
     "product_type": "PMIC",
     "process": "BCD1370F", "revision": "EVT0",
     "inch": 12, "gross_die": 280, "fab_line": "L1",
     "tester": "T01", "para": "P01",
     "lot_id": "LOT001", "wafer_number": "W03",
     "temperature": 25.0,                # [req0] 입력만
     "corner": "NN",                     # [req0] NN/SS/FF
     "source_file": "....csv",
     "ingested_by": "honey_client",
     "analysis_key": null                # (선택) report.db 링크 — 없어도 됨
  },
  # raw_table: df_honey 레이아웃을 dict 로 (per-DUT 행)
  "raw_table": {
     "meta_columns": ["DUT", "XCoord", "YCoord", "Bin", "Serial"],
     "item_columns": ["VREF_TRIM", "IDDQ_INIT", "..."],
     "units":       {"VREF_TRIM": "V", "IDDQ_INIT": "A"},   # → value_type 매핑
     "lower_limit": {"VREF_TRIM": 1.0,  "IDDQ_INIT": null},
     "upper_limit": {"VREF_TRIM": 1.4,  "IDDQ_INIT": 15.0},
     "rows": [
        {"DUT": 1, "XCoord": -3, "YCoord": 5, "Bin": 1,  "Serial": "...",
         "VREF_TRIM": 1.21, "IDDQ_INIT": 12.3},
        {"DUT": 2, "XCoord": -3, "YCoord": 6, "Bin": 18, "Serial": "...",
         "VREF_TRIM": 1.55, "IDDQ_INIT": 12.1},
        # ... per-DUT
     ]
  }
}
```
- **value_type(unit계열)** 는 units 값에서 매핑(V/A/Hz/CODE/TCODE/P_F). category_major(TRIM/NON_TRIM)
  는 item_name 에 'TRIM' 포함 여부로 판정(또는 meta 로 명시 가능).
- **degrade 입력**: raw_table 없이 집계만 줄 수도 있음(아래). 그러면 yield-only.
```python
# degrade 형식 (raw 없을 때)
run_input = { "meta": {...},
  "items": [ {"item_name":"X","bin":18,"unit":"V","yield":0.68,"fail_count":3,"total_count":280,
              "lsl":1.0,"usl":1.4}, ... ] }
```

## 4. 출력 — RunResult
```python
{
  "run_id": 123,
  "engine_version": "ev1", "model_version": "user-model-x",
  "cases": [
    {
      "case_id": "<sha256>",
      "item_canonical": "vref_trim", "item_class": "TRIM|V|18", "bin": 18,
      "status": "MAJOR",
      "primary_signature": "SEVERE_OUTLIER",
      "secondary_signatures": ["TAIL_RISK"],
      "confidence": 0.8, "data_completeness": "full",
      "comment": "site 3 에서만 튐, golden unit 재측정 권장 (과거 retest→정상 이력)",
      "evidence": [ {"signal_code":"OUTLIER_RATIO","value":0.06,"weight":1.0}, ... ],
      "precedents": [ {"action":"retest","result":"recovered_normal","comment":"..."} ]
    },
    ...
  ]
}
```

## 5. 서로가 필요한 것 (상호 의존 정리)
**report_server → eval_analyzer 에 줘야 할 것:**
- 트리거(파일 run 시 evaluate 호출).
- run_input.meta (product/lot/wafer/process/revision/inch/gross_die/tester/para/temperature/corner).
- run_input.raw_table (per-DUT 측정 + limit + 좌표 + bin) — cpk/산포/공간 계산의 원재료.
  ※ 현재 report_server 는 이걸 *버린다*(REPORT_SERVER_CONTEXT §5) → 결합 시 메모리로 넘겨주는 게 핵심.

**eval_analyzer → report_server 에 주는 것:**
- RunResult(§4) — status/signature/comment/confidence. report_server UI 가 표시(후속).
- 저장은 eval_analyzer 가 자체 eval.db 에. report_server DB 변경 불요(독립).

**충족 안 될 때(raw 미전달):** eval_analyzer 는 yield-only degrade
(LOW_YIELD/GROSS_FAIL 만, cpk/산포 signature 휴면, data_completeness="low").

## 6. 결합 시 코드 위치 (report_server 측, 다른 담당)
- report_server 가 `pip install -e eval_analyzer` 또는 경로 추가로 `eval_engine` 을 import.
- report_generator 파이프라인 끝에서:
  ```python
  from eval_engine import evaluate
  result = evaluate(build_run_input(df_honey_group, meta))
  # result 를 UI/응답에 첨부 (저장은 eval_analyzer 가 함)
  ```
- `build_run_input` 어댑터는 **report_server 쪽**에 둔다(eval_analyzer 는 중립 dict 만 받음).
