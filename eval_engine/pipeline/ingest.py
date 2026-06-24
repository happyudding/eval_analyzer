"""L0 Ingest — run_input(메모리 raw) → 캐노니컬 fail_case 들.

입력: docs/INTEGRATION_CONTRACT §3 (meta + raw_table[per-DUT]).
할 일:
  1. product_master / item_master / item_spec / bin_taxonomy upsert (마스터).
  2. item 명 파싱: item_canonical(정규화) / item_base / item_phase, item_alias 해소.
  3. category_major(TRIM 포함 여부) / value_type(units→V|A|Hz|CODE|TCODE|P_F) 분류.
  4. fail item 추출: bin != PASS_BIN 또는 limit 위반(CODE_TO_PORT §4)인 (item, bin) 조합.
  5. case_id = store.make_case_id(...), item_class = f"{category_major}|{value_type}|{bin}".
  6. ingest_run 생성(run_id, meta 의 temperature/corner 포함), run_case 링크, fail_case upsert.
  7. 각 case 에 per-DUT 측정 시리즈(values/x/y/site)를 메모리로 첨부(저장 안 함) → L1/L2 가 사용.
반환: {"run_id": int|None, "cases": [case_ctx, ...]}
  case_ctx = {case_id, item_canonical, item_class, bin, value_type, category_major,
              lsl, usl, family_product, product_name, values, x_pos, y_pos, site, ...}
"""
from .. import store


def ingest(run_input: dict, *, persist: bool = True) -> dict:
    raise NotImplementedError("docs/INTEGRATION_CONTRACT, DB_SCHEMA 기준으로 구현")
