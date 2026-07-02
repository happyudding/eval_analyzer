"""rules/*.yaml 공용 로더 — features/signatures 가 같은 임계값 병합 규칙을 공유.

스코프 우선순위: default → product_type override → item_class override (구체값 우선).
임계값은 여기(yaml)에서만 읽는다 — 코드에 숫자 하드코딩 금지(불변 규칙 5).
"""
import functools

import yaml

from .. import config


@functools.lru_cache(maxsize=4)
def load_yaml(path_str: str):
    with open(path_str, encoding="utf-8") as f:
        return yaml.safe_load(f)


def thresholds_for(case_ctx: dict) -> dict:
    """case 의 product_type/item_class 에 맞춰 병합된 임계값 dict 반환."""
    doc = load_yaml(str(config.THRESHOLDS_FILE))
    merged = dict(doc.get("default", {}))
    pt = doc.get("product_type", {}).get(case_ctx.get("product_type"))
    if pt:
        merged.update(pt)
    ic = doc.get("item_class", {}).get(case_ctx.get("item_class"))
    if ic:
        merged.update(ic)
    return merged


def signatures_doc() -> dict:
    return load_yaml(str(config.SIGNATURES_FILE))


def bin_taxonomy_for(product_type, bin_number):
    """rules/bin_taxonomy.yaml entries 에서 (product_type, bin_number) 매칭 1건. 없으면 None."""
    try:
        doc = load_yaml(str(config.BIN_TAXONOMY_FILE))
    except FileNotFoundError:
        return None
    for e in (doc or {}).get("entries") or []:
        if e.get("product_type") == product_type and e.get("bin_number") == bin_number:
            return e
    return None
