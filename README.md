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
| BD-99 | ASSESS 표시 상태 여섯은 모두 Sensor 의 탐지다. Health 는 Sensor state-export(+ 관계)만 읽는다. VERIFY 근거는 값 없이 참조 · 실체 `action:<run>:<command_id>` · 사후조건의 집은 **보류**(BD-100 — 실행기를 지을 때 행동 명세 통합과 함께) · 사후조건 절은 MS 술어 꼴(BD-100) · S6 = 실행됐나, VERIFY = 효과가 났나 |
| BD-46 | MS 가 제안한 `outcome_confidence` · `false_success_risk` · `loop_risk` · `cost_anomaly` 는 Sensor(L1 · L2) 또는 Health 의 일 |
| BD-52 → BD-99 | `liveness_state` 는 Sensor 에 남는다(BD-99 가 "옮긴다" 를 거둠). "대상이 죽었나 · 수집이 죽었나" 를 가르는 진단이 Health 몫 |
| BD-31 · BD-97 | VERIFY: ActionSpec 사후조건 · 시간 창을 그 뒤의 State 와 견줘 `action_state` 를 낸다. 입력 이름은 L0 `action.*`. 실행기가 선 뒤 |
| DATA_FLOW §6.4 | 공통 원인 먼저(`observes` · `runs_on` · `uses`). 복구는 하나씩 검증한다 |

## 지금 있는 것

- `health/verification.py` — VERIFY 기록 꼴 `verification-record/1` 과 순수 판정 함수 `verify` (CMD-H2). 계약: [`docs/VERIFICATION.md`](docs/VERIFICATION.md)
- `health/predicate.py` — 사후조건 술어. MS `ms/predicate.py` 꼴 그대로(속성 참조 제외)
- 의존: action 계약(`action-contract/1`) — 커밋 sha 고정, 필수. 그 밖에는 표준 라이브러리만

```
pip install -e .                       # action 계약을 고정 sha 로 받는다
python3 -m unittest                    # 옆에 MS 가 있으면(../MS · MS_REPO) 술어 대조도 돈다
python3 eval/mutation.py               # 변이가 모두 RED 여야 한다
```

## 문서

- [`docs/BOUNDARY.md`](docs/BOUNDARY.md) — CMD-H1: ASSESS 표시 상태 여섯의 자리 · `VerificationRecord` 꼴 제안 · FDIR 줄. 제안이다
- [`eval/assess_inventory.py`](eval/assess_inventory.py) — 위 판정의 근거를 Sensor 코드에서 뽑는 탐침(읽기 전용)

## 아직 하지 않은 것

- ASSESS(진단 · 격리) — 입력(관계 export · `observes`)이 서면 baseline 지시로 짓는다(BD-99).
- `action_state` 를 State 로 내보내는 일 · 실데이터 VERIFY — 실행기 · ActionSpec 사후조건이 선 뒤.
- 다른 저장소의 파일(Sensor · DC · MS · Telemetry · action)은 고치지 않는다. 필요하면 baseline 이슈에 `요청:` 으로 적는다.

## 통로

baseline 이슈 `[Health] 보고 · baseline 지시` 에 댓글로 보고한다 (baseline PROTOCOL §1). 보고와 커밋 머리에 `<health>` 를 붙인다.
