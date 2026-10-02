"""CMD-H1 탐침 -- Sensor 의 ASSESS 표시 상태가 무엇을 읽고 무엇에 기대는지 코드에서 뽑는다(읽기 전용).

    python3 eval/assess_inventory.py ../cogito5170/sensor      # 옆에 Sensor 체크아웃(통합 브랜치)

가르는 기준(baseline#9 CMD-H1):
    여러 실체 · 관계를 묶나   규칙 · 지표 함수가 다른 상태(엔진 current) 나 관계(relationships)를 읽나
    운영자 문턱이 있나        규칙 함수가 설정(cfg.*)을 읽나 · 값의 근거에 OPERATOR_ASSUMED 가 있나
Sensor 파일은 고치지 않는다. 표준 라이브러리만.
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path


def main(sensor: str) -> int:
    root = Path(sensor).resolve()
    sys.path.insert(0, str(root))
    from llmsensor.state.registry import Registry          # noqa: E402
    from llmsensor.state import export                     # noqa: E402

    reg = Registry()
    rows = []
    for name, r in reg.rules.items():
        if r.owner_layer != "ASSESS":
            continue
        src = inspect.getsource(r.fn) if r.fn.__name__ != "fn" else inspect.getsource(r.fn.__code__)
        metrics = [reg.metrics[i] for i in r.inputs if i in reg.metrics]
        msrc = "".join(inspect.getsource(m.fn) for m in metrics if getattr(m.fn, "__code__", None))
        rows.append({
            "state": name, "rule": f"{r.id}@{r.version}", "entity": r.entity.value, "basis": r.basis.value,
            "inputs": list(r.inputs),
            "per_subject": r.subjects is not None or r.entity.value == "tool",   # 도구는 엔진이 도구마다 따로 세운다(TOOL_RULE)
            "cfg": sorted(set(re.findall(r"cfg\.(\w+)", src))),
            "operator_values": "OPERATOR_ASSUMED" in src,
            "reads_states": bool(re.search(r"\bcurrent\b|\bE\.view\b", src + msrc)),
            "reads_relations": "relationships" in src + msrc,
            "clock_values": list(r.clock_values),
        })
    print("| 상태 | 규칙 | 실체 | 근거 | 실체마다 | 설정 문턱 | 다른 상태 읽음 | 관계 읽음 |")
    print("|---|---|---|---|---|---|---|---|")
    for x in rows:
        thr = ", ".join(x["cfg"]) + (" (값별 OPERATOR_ASSUMED)" if x["operator_values"] else "") or "없음"
        print(f"| `{x['state']}` | `{x['rule']}` | {x['entity']} | {x['basis']} | {'예' if x['per_subject'] else '-'} | "
              f"{thr or '없음'} | {'예' if x['reads_states'] else '아니오'} | {'예' if x['reads_relations'] else '아니오'} |")
    exported = [n for n in ("catalog", "read", "subjects", "as_of", "entity_ref") if hasattr(export, n)]
    rel_out = any("relation" in n for n in dir(export))
    print(f"\nstate-export `{export.CONTRACT}` 의 함수: {exported} · 관계를 내보내는 함수: {'있음' if rel_out else '없음'}")
    print(f"ASSESS 표시 상태 수: {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "../cogito5170/sensor"))
