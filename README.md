# health

ASSESS 의 **진단 · 격리** 와 **VERIFY** 의 집이다 (baseline BD-22 · BD-43).
아직 코드는 없다. 이 문서는 이 저장소의 자리와, baseline 이 이미 정한 것만 적는다.
판단은 baseline(`cogito5170/baseline`, 통합 브랜치 `claude/gracious-meitner-vp49xe`)이 한다.

## 자리

```
L0 Telemetry ─► L1 Sensor (MEASURE · 탐지 판독) ─► L2 State (ESTIMATE)
                                   │
                                   └──► Health: ASSESS 진단 · 격리 ──► 건강 · 고장 State ──► L3 DC ─► …
                                                                                              │
              … ─► Guard ─► Action 실행기 ─► L0 action.* ──► Health: VERIFY ──► action_state ─┘
```

- 층 번호는 새로 받지 않는다 — L1–L2 옆 (BD-43, BASELINE §10.1).
- 건강 · 고장 상태도 State 다. 소유 규칙이 ASSESS 에 있을 뿐이다 (BD-04).
- 판정을 하지 못하면 UNKNOWN 이다. `NO_FAILURE_OBSERVED` ≠ `HEALTHY` (BASELINE §9).

## 근거 (baseline 통합 브랜치의 문서)

| 결정 | 이 저장소에 주는 뜻 |
|---|---|
| BD-22 | Assess · Verify 의 집 = 새 Health 저장소. PC-06 의 ASSESS 부분이 이리로 온다 |
| BD-28 | 의존 방향: Telemetry ← Health. DC 는 아무것도 import 하지 않는다 |
| BD-35 | 건강 성격 상태(`execution_health` · `tool_execution_health` · `execution_interruption` · `runtime_reliability` · `answer_reliability` · `correction_rate`)는 이름 · 값 그대로, 소유 층 표시만 ASSESS |
| BD-36 | `confidence{kind: none · ordinal · calibrated}` — 보정 전 Q 는 ordinal, Guard · 정책의 문턱으로 못 쓴다 |
| BD-39 | 필수 예산이 빠진 배치는 ASSESS 의 설정 적합성 고장 상태 |
| BD-46 | MS 가 제안한 `outcome_confidence` · `false_success_risk` · `loop_risk` · `cost_anomaly` 는 Sensor(L1 · L2) 또는 Health 의 일 |
| BD-52 | `liveness_state` 는 지금 Sensor 에 있다. Health 가 서면 그때 옮긴다 |
| BD-31 · BD-97 | VERIFY: ActionSpec 사후조건 · 시간 창을 그 뒤의 State 와 견줘 `action_state` 를 낸다. 입력 이름은 L0 `action.*`. 실행기가 선 뒤 |
| DATA_FLOW §6.4 | 공통 원인 먼저(`observes` · `runs_on` · `uses`). 복구는 하나씩 검증한다 |

## 문서

- [`docs/BOUNDARY.md`](docs/BOUNDARY.md) — CMD-H1: ASSESS 표시 상태 여섯의 자리 · `VerificationRecord` 꼴 제안 · FDIR 줄. 제안이다
- [`eval/assess_inventory.py`](eval/assess_inventory.py) — 위 판정의 근거를 Sensor 코드에서 뽑는 탐침(읽기 전용)

## 아직 하지 않은 것

- 코드 · 시험 · 계약 — 없음. baseline 지시(CMD-H*)를 받은 뒤 짓는다.
- 다른 저장소의 파일(Sensor · DC · MS · Telemetry · action)은 고치지 않는다. 필요하면 baseline 이슈에 `요청:` 으로 적는다.

## 통로

baseline 이슈 `[Health] 보고 · baseline 지시` 에 댓글로 보고한다 (baseline PROTOCOL §1). 보고와 커밋 머리에 `<health>` 를 붙인다.
