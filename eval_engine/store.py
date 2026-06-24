"""eval.db 스키마 + CRUD. eval_analyzer 가 자체 소유하는 SQLite DB.

DDL 은 docs/DB_SCHEMA.md 와 1:1. raw(per-DUT) 저장 안 함. JSON 컬럼 없음(정규화 child).
"""
import hashlib
import sqlite3
import time
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS product_master (
    product_name TEXT PRIMARY KEY, family_product TEXT, product_type TEXT, process TEXT,
    inch INTEGER, gross_die INTEGER, fab_line TEXT, tester TEXT, para TEXT, updated_at INTEGER
);
CREATE TABLE IF NOT EXISTS item_master (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT, item_name_raw TEXT NOT NULL,
    item_canonical TEXT NOT NULL, item_base TEXT, item_phase TEXT,
    category_major TEXT, category_mid TEXT, value_type TEXT, unit TEXT,
    UNIQUE(item_canonical)
);
CREATE TABLE IF NOT EXISTS item_alias (raw_name TEXT PRIMARY KEY, item_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS item_spec (
    item_id INTEGER NOT NULL, product_name TEXT NOT NULL, revision TEXT NOT NULL,
    lsl REAL, usl REAL, updated_at INTEGER,
    PRIMARY KEY (item_id, product_name, revision)
);
CREATE TABLE IF NOT EXISTS bin_taxonomy (
    product_type TEXT NOT NULL, bin_number INTEGER NOT NULL, bin_class TEXT,
    severity_bias REAL, description TEXT, updated_at INTEGER,
    PRIMARY KEY (product_type, bin_number)
);
CREATE TABLE IF NOT EXISTS ingest_run (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT, lot_id TEXT,
    wafer_number TEXT, source_file TEXT, analysis_key TEXT,
    temperature REAL, corner TEXT, ingested_by TEXT, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS run_case (
    run_id INTEGER NOT NULL, case_id TEXT NOT NULL, seen_at INTEGER NOT NULL,
    PRIMARY KEY (run_id, case_id)
);
CREATE TABLE IF NOT EXISTS fail_case (
    case_id TEXT PRIMARY KEY, product_name TEXT NOT NULL, lot_id TEXT, wafer_number TEXT,
    item_id INTEGER NOT NULL, bin INTEGER, revision TEXT, item_class TEXT,
    created_at INTEGER NOT NULL, updated_at INTEGER,
    UNIQUE(product_name, lot_id, wafer_number, item_id, bin, revision)
);
CREATE INDEX IF NOT EXISTS idx_fail_case_item_class ON fail_case(item_class);
CREATE INDEX IF NOT EXISTS idx_fail_case_product ON fail_case(product_name);
CREATE TABLE IF NOT EXISTS raw_metrics (
    case_id TEXT NOT NULL, run_id INTEGER NOT NULL,
    cpk REAL, cpl REAL, cpu REAL, cp REAL, mean REAL, stdev REAL, min REAL, max REAL,
    yield REAL, fail_count INTEGER, total_count INTEGER, bimodality REAL,
    created_at INTEGER NOT NULL, PRIMARY KEY (case_id, run_id)
);
CREATE TABLE IF NOT EXISTS features (
    case_id TEXT NOT NULL, run_id INTEGER NOT NULL, engine_version TEXT NOT NULL, computed_at INTEGER NOT NULL,
    spread_norm REAL, skewness REAL, kurtosis REAL, outlier_ratio REAL, modality TEXT,
    bimodality_score REAL, density_gap REAL, cdf_gap REAL,
    spec_margin_low REAL, spec_margin_high REAL, nearest_spec_side TEXT, limit_hit_ratio REAL,
    edge_fail_ratio REAL, center_fail_ratio REAL, radial_gradient REAL, quadrant_imbalance REAL,
    x_gradient REAL, y_gradient REAL, wafer_zone_signature TEXT,
    n_dut INTEGER, site_cpk_delta REAL, code_edge_hit REAL,
    PRIMARY KEY (case_id, run_id, engine_version)
);
CREATE TABLE IF NOT EXISTS evaluation (
    eval_id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, run_id INTEGER NOT NULL,
    engine_version TEXT NOT NULL, model_version TEXT, status TEXT, confidence REAL,
    data_completeness TEXT, comment TEXT, created_at INTEGER NOT NULL,
    UNIQUE(case_id, run_id, engine_version, model_version)
);
CREATE TABLE IF NOT EXISTS eval_evidence (
    eval_id INTEGER NOT NULL, signal_code TEXT NOT NULL, value REAL, weight REAL, note TEXT,
    PRIMARY KEY (eval_id, signal_code)
);
CREATE TABLE IF NOT EXISTS case_signature (
    eval_id INTEGER NOT NULL, signature TEXT NOT NULL, role TEXT NOT NULL, score REAL,
    PRIMARY KEY (eval_id, signature)
);
CREATE TABLE IF NOT EXISTS label (
    label_id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, eval_id INTEGER,
    human_status TEXT, root_cause_category TEXT, root_cause_detail TEXT,
    engine_comment_accepted INTEGER, comment_modified INTEGER, human_comment TEXT,
    labeler TEXT, reviewer TEXT, label_quality TEXT, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_label_case ON label(case_id);
CREATE TABLE IF NOT EXISTS case_outcome (
    outcome_id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, label_id INTEGER,
    action TEXT, condition TEXT, result TEXT, resolved_by TEXT, resolved_at INTEGER, note TEXT
);
CREATE INDEX IF NOT EXISTS idx_outcome_case ON case_outcome(case_id);
CREATE TABLE IF NOT EXISTS engine_version_registry (
    engine_version TEXT PRIMARY KEY, thresholds_ref TEXT, thresholds_hash TEXT,
    signatures_ref TEXT, signatures_hash TEXT, taxonomy_ref TEXT, taxonomy_hash TEXT,
    created_at INTEGER NOT NULL
);
"""


def _now():
    return int(time.time())


def make_case_id(product_name, lot_id, wafer_number, item_id, bin_, revision):
    """자연키 sha256 (재업로드 idempotent). docs/DB_SCHEMA §3."""
    key = "|".join(str(x) for x in (product_name, lot_id, wafer_number, item_id, bin_, revision))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(config.DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """eval.db 생성 + 스키마. (config.DATA_DIR 자동 생성)"""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ── CRUD (TODO: docs/DB_SCHEMA 기준으로 구현) ────────────────────────────────
# upsert_product_master / upsert_item_master / resolve_item_id(raw_name) /
# upsert_item_spec / upsert_bin_taxonomy /
# create_ingest_run(meta) -> run_id / link_run_case(run_id, case_id) /
# upsert_fail_case(...) -> case_id / save_raw_metrics(case_id, run_id, m) /
# save_features(case_id, run_id, engine_version, f) /
# save_evaluation(...) -> eval_id / save_eval_evidence / save_case_signature /
# insert_label / insert_case_outcome / upsert_engine_version_registry
#
# search_precedents(bin, value_type, item_canonical, family_product=None) -> list[dict]:
#   docs/DB_SCHEMA §9 SQL 로 후보 조회 후, item_canonical 유사도(SequenceMatcher.ratio)
#   >= config.PRECEDENT_NAME_SIMILARITY 인 행만 반환.
