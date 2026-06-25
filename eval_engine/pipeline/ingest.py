"""L0 Ingest — run_input(메모리 raw) → 캐노니컬 fail_case 들.

입력: docs/INTEGRATION_CONTRACT §3 (meta + raw_table[per-DUT] 또는 degrade items).
할 일:
  1. product_master / item_master / item_spec upsert (마스터).
  2. item 명 파싱: item_canonical(정규화) / item_base / item_phase, item_alias 해소.
  3. category_major(TRIM 포함 여부) / value_type(units→V|A|Hz|CODE|TCODE|P_F) 분류.
  4. fail item 추출: bin != PASS_BIN 또는 limit 위반(CODE_TO_PORT §4)인 (item, bin) 조합.
  5. case_id = store.make_case_id(...), item_class = f"{category_major}|{value_type}|{bin}".
  6. ingest_run 생성(run_id, meta 의 temperature/corner 포함), run_case 링크, fail_case upsert.
  7. 각 case 에 per-DUT 측정 시리즈(values/x/y/site)를 메모리로 첨부(저장 안 함) → L1/L2 가 사용.
반환: {"run_id": int|None, "cases": [case_ctx, ...]}

주의: persist=False(preview) 모드는 DB 미접근 — item_id 를 canonical 해시로 대체한다.
  이 모드의 case_id 는 persist=True 재실행 시 달라질 수 있다(preview 전용).
"""
import hashlib
import re

from .. import store
from ._rules import load_yaml
from .. import config

PASS_BIN = 1

UNIT_TO_VALUE_TYPE = {
    "v": "V", "volt": "V", "volts": "V",
    "a": "A", "amp": "A", "amps": "A", "ma": "A", "ua": "A",
    "hz": "Hz", "khz": "Hz", "mhz": "Hz",
    "code": "CODE", "tcode": "TCODE",
    "p_f": "P_F", "pass/fail": "P_F", "p/f": "P_F", "": "P_F",
}
PHASE_TOKENS = {"init", "code", "trim", "p2", "p1", "final"}


def _alias_map():
    try:
        doc = load_yaml(str(config.ITEM_ALIAS_FILE))
        return {k.strip(): v for k, v in (doc.get("aliases") or {}).items()}
    except FileNotFoundError:
        return {}


def _canonicalize(raw_name: str) -> str:
    return re.sub(r"\s+", "_", raw_name.strip().lower())


def _classify_value_type(unit, item_name) -> str:
    if unit:
        vt = UNIT_TO_VALUE_TYPE.get(str(unit).strip().lower())
        if vt:
            return vt
    if "CODE" in item_name.upper():
        return "TCODE" if "TRIM" in item_name.upper() else "CODE"
    return "P_F"


def _classify_category_major(item_name: str) -> str:
    return "TRIM" if "TRIM" in item_name.upper() else "NON_TRIM"


def _parse_base_phase(item_canonical: str):
    parts = item_canonical.split("_")
    phase = next((p for p in parts if p in PHASE_TOKENS), None)
    base = "_".join(p for p in parts if p != phase) if phase else item_canonical
    return base, phase


def _is_num(x):
    return isinstance(x, (int, float)) and not (isinstance(x, float) and x != x)  # NaN 제외


def _resolve_item_identity(raw_name, value_type, persist, conn, alias):
    item_canonical = alias.get(raw_name.strip(), _canonicalize(raw_name))
    base, phase = _parse_base_phase(item_canonical)
    cat = _classify_category_major(raw_name)
    if persist:
        item_id = store.resolve_item_id(raw_name, conn=conn)
        if item_id is None:
            item_id = store.upsert_item_master(item_canonical, raw_name, base, phase,
                                               cat, None, value_type, None, conn=conn)
            store.upsert_item_alias(raw_name, item_id, conn=conn)
    else:
        item_id = int(hashlib.sha1(item_canonical.encode()).hexdigest()[:8], 16)
    return item_id, item_canonical, cat


def _ingest_raw_table(meta, raw_table, persist, conn, alias):
    revision = meta.get("revision")
    item_cols = raw_table["item_columns"]
    units = raw_table.get("units", {})
    lowers = raw_table.get("lower_limit", {})
    uppers = raw_table.get("upper_limit", {})
    rows = raw_table["rows"]
    has_site = "Site" in (raw_table.get("meta_columns") or [])

    cases = []
    for item in item_cols:
        unit = units.get(item)
        value_type = _classify_value_type(unit, item)
        lsl, usl = lowers.get(item), uppers.get(item)

        values, x_pos, y_pos, site, bins = [], [], [], [], []
        for r in rows:
            v = r.get(item)
            if not _is_num(v):
                continue
            values.append(float(v))
            x_pos.append(r.get("XCoord"))
            y_pos.append(r.get("YCoord"))
            site.append(r.get("Site") if has_site else None)
            bins.append(r.get("Bin"))

        if not values:
            continue

        # fail bin 집합: limit 위반 DUT 의 bin + non-pass bin
        fail_bins = set()
        for v, b in zip(values, bins):
            lo = (lsl is not None) and (v < lsl)
            hi = (usl is not None) and (v > usl)
            if lo or hi or (b is not None and b != PASS_BIN):
                if b is not None:
                    fail_bins.add(int(b))
        fail_bins.discard(PASS_BIN)
        if not fail_bins:
            continue

        item_id, item_canonical, cat = _resolve_item_identity(
            item, value_type, persist, conn, alias)
        if persist and revision is not None and (lsl is not None or usl is not None):
            store.upsert_item_spec(item_id, meta.get("product_name"), revision,
                                   lsl, usl, conn=conn)

        for bin_ in sorted(fail_bins):
            fail_mask = [b == bin_ for b in bins]
            case_id = store.make_case_id(meta.get("product_name"), meta.get("lot_id"),
                                         meta.get("wafer_number"), item_id, bin_, revision)
            cases.append({
                "case_id": case_id, "item_id": item_id, "item_canonical": item_canonical,
                "category_major": cat, "value_type": value_type, "bin": bin_,
                "revision": revision, "item_class": f"{cat}|{value_type}|{bin_}",
                "product_type": meta.get("product_type"),
                "family_product": meta.get("family_product"),
                "lsl": lsl, "usl": usl, "skewness": None,
                "values": values, "fail_mask": fail_mask,
                "x_pos": x_pos, "y_pos": y_pos, "site": site,
            })
    return cases


def _ingest_degrade(meta, items, persist, conn, alias):
    revision = meta.get("revision")
    cases = []
    for it in items:
        raw_name = it["item_name"]
        value_type = _classify_value_type(it.get("unit"), raw_name)
        bin_ = int(it["bin"])
        lsl, usl = it.get("lsl"), it.get("usl")
        item_id, item_canonical, cat = _resolve_item_identity(
            raw_name, value_type, persist, conn, alias)
        if persist and revision is not None and (lsl is not None or usl is not None):
            store.upsert_item_spec(item_id, meta.get("product_name"), revision,
                                   lsl, usl, conn=conn)
        case_id = store.make_case_id(meta.get("product_name"), meta.get("lot_id"),
                                     meta.get("wafer_number"), item_id, bin_, revision)
        cases.append({
            "case_id": case_id, "item_id": item_id, "item_canonical": item_canonical,
            "category_major": cat, "value_type": value_type, "bin": bin_,
            "revision": revision, "item_class": f"{cat}|{value_type}|{bin_}",
            "product_type": meta.get("product_type"),
            "family_product": meta.get("family_product"),
            "lsl": lsl, "usl": usl, "skewness": it.get("skewness"),
            "values": [], "fail_mask": [], "x_pos": [], "y_pos": [], "site": [],
            "yield": it.get("yield"), "fail_count": it.get("fail_count"),
            "total_count": it.get("total_count"),
        })
    return cases


def _build_cases(meta, run_input, persist, conn):
    alias = _alias_map()
    raw_table = run_input.get("raw_table")
    if raw_table:
        cases = _ingest_raw_table(meta, raw_table, persist, conn, alias)
    else:
        cases = _ingest_degrade(meta, run_input["items"], persist, conn, alias)
    for case in cases:
        case["product_name"] = meta.get("product_name")
    return cases


def ingest(run_input: dict, *, persist: bool = True) -> dict:
    meta = run_input["meta"]
    if not persist:
        cases = _build_cases(meta, run_input, persist=False, conn=None)
        return {"run_id": None, "cases": cases}

    with store.get_conn() as conn:
        store.upsert_product_master(meta, conn=conn)
        run_id = store.create_ingest_run(meta, conn=conn)
        cases = _build_cases(meta, run_input, persist=True, conn=conn)
        for case in cases:
            store.upsert_fail_case(case["case_id"], meta.get("product_name"),
                                   meta.get("lot_id"), meta.get("wafer_number"),
                                   case["item_id"], case["bin"], case["revision"],
                                   case["item_class"], conn=conn)
            store.link_run_case(run_id, case["case_id"], conn=conn)
    return {"run_id": run_id, "cases": cases}
