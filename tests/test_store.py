"""store CRUD + search_precedents 단독 테스트 (모두 tmp DB)."""
from eval_engine import store


def _seed_precedent(conn, *, product="P1", item_raw="VREF_TRIM", item_canon="vref_trim",
                    value_type="V", bin_=18, family="SOC",
                    action="retest", result="recovered_normal", comment="과거 정상복귀"):
    store.upsert_product_master(
        {"product_name": product, "family_product": family, "product_type": "PMIC"}, conn=conn)
    item_id = store.upsert_item_master(item_canon, item_raw, None, None, "TRIM", None,
                                       value_type, None, conn=conn)
    case_id = store.make_case_id(product, "L1", 1, item_id, bin_, 0.0)
    store.upsert_fail_case(case_id, product, "L1", 1, item_id, bin_, 0.0,
                           f"TRIM|{value_type}|{bin_}", conn=conn)
    label_id = store.insert_label(case_id, None, "MAJOR", "equipment", None, 0, 0,
                                  comment, "seed", None, "seed", conn=conn)
    store.insert_case_outcome(case_id, label_id, action, None, result, None, None, None, conn=conn)
    return case_id


def test_product_item_roundtrip(fresh_db):
    with store.get_conn() as conn:
        store.upsert_product_master(
            {"product_name": "PX", "family_product": "F", "product_type": "PMIC"}, conn=conn)
        item_id = store.upsert_item_master("vref", "VREF", "vref", None, "NON_TRIM", None,
                                           "V", "V", conn=conn)
        store.upsert_item_alias("VREF", item_id, conn=conn)
        assert store.resolve_item_id("VREF", conn=conn) == item_id
        # upsert 멱등 — 같은 canonical 재삽입 시 동일 id
        item_id2 = store.upsert_item_master("vref", "VREF", "vref", None, "NON_TRIM", None,
                                            "V", "V", conn=conn)
        assert item_id2 == item_id


def test_make_case_id_deterministic():
    a = store.make_case_id("P", "L", "W", 1, 18, "EVT0")
    b = store.make_case_id("P", "L", "W", 1, 18, "EVT0")
    c = store.make_case_id("P", "L", "W", 1, 19, "EVT0")
    assert a == b
    assert a != c


def test_search_precedents_matches_similar_name(fresh_db):
    with store.get_conn() as conn:
        _seed_precedent(conn, item_raw="VREF_TRIM", item_canon="vref_trim")
    # 동일 bin/value_type + 유사 이름(vref_trim vs vref_trim_p2)
    res = store.search_precedents(18, "V", "vref_trim_p2")
    assert len(res) >= 1
    assert res[0]["action"] == "retest"
    assert res[0]["result"] == "recovered_normal"
    assert res[0]["similarity"] >= 0.70


def test_search_precedents_excludes_dissimilar_name(fresh_db):
    with store.get_conn() as conn:
        _seed_precedent(conn, item_raw="VREF_TRIM", item_canon="vref_trim")
    # 전혀 다른 이름 → 유사도 < 0.70 → 제외
    res = store.search_precedents(18, "V", "iddq_leakage_current_xyz")
    assert res == []


def test_search_precedents_excludes_self(fresh_db):
    with store.get_conn() as conn:
        case_id = _seed_precedent(conn, item_canon="vref_trim")
    res_all = store.search_precedents(18, "V", "vref_trim")
    assert len(res_all) == 1
    res_excl = store.search_precedents(18, "V", "vref_trim", exclude_case_id=case_id)
    assert res_excl == []


def test_search_precedents_dedup_latest_label(fresh_db):
    with store.get_conn() as conn:
        case_id = _seed_precedent(conn, comment="첫 라벨")
        # 같은 case 에 최신 label + outcome 추가 → label×outcome 곱 대신 case 당 1행(최신 기준)
        lbl2 = store.insert_label(case_id, None, "MINOR", "spec", None, 0, 0,
                                  "최신 라벨", "seed", None, "seed", conn=conn)
        store.insert_case_outcome(case_id, lbl2, "spec_release", None, "improved",
                                  None, None, None, conn=conn)
    res = store.search_precedents(18, "V", "vref_trim")
    assert len(res) == 1
    assert res[0]["human_comment"] == "최신 라벨"
    assert res[0]["action"] == "spec_release"


def test_search_precedents_value_type_filter(fresh_db):
    with store.get_conn() as conn:
        _seed_precedent(conn, item_canon="vref_trim", value_type="V")
    # 같은 이름이지만 value_type 다름 → 후보에서 제외
    assert store.search_precedents(18, "A", "vref_trim") == []
