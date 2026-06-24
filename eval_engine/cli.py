"""얇은 테스트/보정 CLI (서버 아님).

용도:
  python -m eval_engine.cli init                 # eval.db 생성
  python -m eval_engine.cli run <sample.csv>     # 샘플 raw 1개로 evaluate() 단독 검증
  python -m eval_engine.cli calibrate            # thresholds.yaml 재산출
  python -m eval_engine.cli seed <background.csv> # 과거 라벨 seed 적재 (label/case_outcome)
seed/background_seed_example.csv 형식 참고.
"""
import sys
from . import store


def main(argv=None):
    argv = argv or sys.argv[1:]
    cmd = argv[0] if argv else "help"
    if cmd == "init":
        store.init_db()
        print(f"initialized {store.config.DB_PATH}")
    else:
        # TODO: run / calibrate / seed 구현
        print(__doc__)


if __name__ == "__main__":
    main()
