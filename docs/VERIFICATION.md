# VERIFICATION — `verification-record/1` 꼴과 판정 (VERIFY)

근거: baseline `claude/gracious-meitner-vp49xe` 의 다음 문서다.
- BD-31: ActionSpec 의 사후조건 · 검증 시간 창
- BD-99: H1 의 답
- BD-96: `action-contract/1`
- BD-32: 실체 id
- BD-33 · BD-90: 시간 기준
- DATA_FLOW C11 · §7
- 이슈 baseline#9 의 CMD-H2

코드: [`health/verification.py`](../health/verification.py) · [`health/predicate.py`](../health/predicate.py).
시험: [`tests/`](../tests) · 변이: [`eval/mutation.py`](../eval/mutation.py).

```
ActionCommand ─(issued_at · target)─┐
ActionSpec 사후조건 · 창 ────────────┼──► verify(...) ──► VerificationRecord ──► State action_state (실체 action:<run>:<command_id>)
Sensor state-export read · subjects ┘        ▲
ActionOutcome / L0 action.result ── 명령이 같은지만 본다. 판정에 쓰지 않는다
```

## 1. 꼴 `verification-record/1`

- **닫힌 꼴**이다. `from_dict` 는 다음을 거절한다(`action.ContractError`).
  - 모르는 칸 · 빠진 칸 · 다른 판본
  - id 위조
  - 서로 어긋난 칸(까닭 ↔ 결과, final, 닫힌 창의 PENDING …)
- id 는 **내용 해시**다. `ver-` + 정준 JSON 의 sha256 앞 16 hex 이고, 정준 JSON 은 `action.canonical` 그대로다.

| 칸 | 타입 | 뜻 |
|---|---|---|
| `verification_id` | `ver-` + 16 hex | 아래 칸 전부의 내용 해시 |
| `command_id` | `cmd-` + 16 hex | = ActionCommand.`command_id` = L0 `action.dispatch/result`.`action_ref` (CMD-T16) |
| `run` | str | 실행 id. `action_state` 의 실체 = `action:<run>:<command_id>` (BD-32 · BD-99) |
| `spec` | `"<ActionSpec 이름>@<판본>"` \| null | 어느 사후조건으로 판정했나. null 이면 `NO_SPEC` |
| `postcondition` | [절] | 논리곱. 절 = `{"entity": 지정, "pred": [상태, 연산, 값]}` (§2) |
| `window` | `{"start_ms", "end_ms", "time_base": "unix_ms"}` | `start_ms` = 명령 `issued_at`. `end_ms` = start + ActionSpec 의 창. 명령의 `deadline`(실행기의 기한)과는 다르다 |
| `outcome_ref` | str \| null | L0 `action.result` 사건 id. **판정에 쓰지 않는다** |
| `evidence` | [근거] | 절마다 하나: `{"clause", "entity", "state", "observed_at", "time_base"}` — **값은 싣지 않는다**(BD-99, PC-09 와 같은 원칙). 재생은 State 이력으로 한다 |
| `result` | `PENDING` · `VERIFIED` · `NOT_VERIFIED` · `UNKNOWN` | C11 |
| `reason` | 닫힌 낱말 | 아래 표 |
| `evaluated_at` | 수, unix_ms | 판정 시각. `start_ms` 보다 이를 수 없다 |
| `final` | bool | PENDING 만 false |
| `schema` | `verification-record/1` | |

| `reason` | `result` | 뜻 |
|---|---|---|
| `MET` | VERIFIED | 모든 절이 쓸 만한 근거로 참이다 |
| `WINDOW_OPEN` | PENDING | 아직 정할 수 없고, 창이 열려 있다 |
| `UNMET_AT_CLOSE` | NOT_VERIFIED | 창이 닫혔고, 쓸 만한 근거로 거짓인 절이 있다 |
| `NO_SPEC` | UNKNOWN | 사후조건이 없다 — 검증할 수 없는 행동을 NOT_VERIFIED 라 하지 않는다 |
| `UNRESOLVED_ENTITY` | UNKNOWN | 절의 실체를 풀 수 없다(겨냥 없는 명령의 `$target` · subjects 에 없는 역할) |
| `NO_POST_OBSERVATION` | UNKNOWN | 명령 **뒤의** 관측이 없다 |
| `TIME_BASE_MISMATCH` | UNKNOWN | 근거의 시각 기준이 `unix_ms` 가 아니다 — 창과 견주지 않는다(BD-90) |
| `NOT_USABLE` | UNKNOWN | 관측은 있지만 쓸 수 없다(유효성 · 신선도 · 판정 시각보다 늦음) |

## 2. 사후조건 절

- `pred` 는 **MS `ms/predicate.py` 의 술어 꼴 그대로**다: `[상태, 연산, 값]`. 연산은 `== != < <= > >= in not_in` · `exists missing`.
  - 사전조건 · 파생 상태 · 질의가 이미 이 꼴을 쓴다. 새 꼴을 짓지 않는다.
  - 옆에 MS 가 있으면 시험이 같은 뜻인지 대조한다.
- **다른 점 하나**: 값 자리의 속성 참조(`{"prop", "mul"}`)는 받지 않는다. 절은 한 실체의 한 상태만 본다.
- `entity` 의 지정은 셋 중 하나다.

| 지정 | 풀리는 곳 |
|---|---|
| `"$target"` | 명령의 `target`. L0 의 target 은 해시뿐이라 **명령에서** 푼다 |
| `"$run.agent"` · `"$run.task"` · `"$run.runtime"` | Sensor state-export `subjects(E, run)` |
| 그 밖의 문자열(`$` 로 시작하지 않음) | 실체 id 그대로 |

- 식 · 코드는 받지 않는다. 재생과 결정론 때문이다.

## 3. 판정 `verify(...)`

순수 함수다. 같은 입력이면 같은 기록(같은 id)이 나온다.

**근거가 쓸 만한가.** 절마다 차례로 보고, 처음 걸린 것이 그 절의 까닭이 된다.
1. 실체를 풀 수 있다 → 아니면 `UNRESOLVED_ENTITY`
2. 관측 시각이 있다 → 아니면 `NO_POST_OBSERVATION`
3. 시각 기준이 `unix_ms` 다 → 아니면 `TIME_BASE_MISMATCH`
4. **관측 시각 ≥ 명령 발행 시각** → 아니면 `NO_POST_OBSERVATION`.
   - 명령 전부터 참이던 값은 효과의 근거가 아니다(BD-99).
5. 관측 시각 ≤ 판정 시각 → 아니면 `NOT_USABLE`
6. 유효성이 OBSERVED · DERIVED · INFERRED 가운데 하나이고, 신선도가 FRESH · PERMANENT 다 → 아니면 `NOT_USABLE`

**술어는 쓸 만한 값에만 적용한다.** MS `holds` 는 값이 없으면 거짓이다. 그대로 쓰면 '모름' 이 NOT_VERIFIED 로 간다.

**결과.** 위에서부터 처음 맞는 것이다.

| # | 조건 | 결과 |
|---|---|---|
| 1 | `spec` 이 null 이거나 절이 없다 | UNKNOWN / NO_SPEC |
| 2 | 모든 절이 참이다 | VERIFIED / MET — 창이 열려 있어도 |
| 3 | 판정 시각 < `end_ms` | PENDING / WINDOW_OPEN |
| 4 | 쓸 만한 근거로 거짓인 절이 하나라도 있다 | NOT_VERIFIED / UNMET_AT_CLOSE |
| 5 | 나머지 | UNKNOWN / 차례상 첫 모자란 절의 까닭 |

**실행기의 결과는 판정에 들어가지 않는다**(DATA_FLOW §7: "됐다" 는 관측일 뿐).
- `outcome`(ActionOutcome)을 받는 까닭은 하나다. 명령과 같은 것을 가리키는지 확인한다. 다르면 거절한다.
- 기록에는 `outcome_ref` 만 남는다.

## 4. 이음

| 이 꼴 | ActionCommand | L0 `action.dispatch` | L0 `action.result` | ActionOutcome | Sensor state-export/2 |
|---|---|---|---|---|---|
| `command_id` | `command_id` | `action_ref` | `action_ref` | `command_id` | — |
| `window.start_ms` | `issued_at` (unix_ms) | 봉투 `at` 은 쓰지 않는다(기준이 다를 수 있다) | — | — | — |
| `$target` | `target` (평문) | `target` (#해시 — 풀 수 없다) | — | — | — |
| `$run.<역할>` | — | — | — | — | `subjects(E, run)` |
| `evidence[i]` | — | — | — | — | `read` 의 `entity` · `name` · `observed_at` · `time_base` |
| 판정에 쓰는 값 | — | — | — | — | `read` 의 `value` · `status` · `freshness` (기록에는 남기지 않는다) |
| `outcome_ref` | — | — | 사건 id | (판정에 쓰지 않음) | — |

- **의존**: action 계약(`action-contract/1`)은 **필수 의존**이고, 커밋 `443f8eb810ce3cb9677cdc9f564ff79790f9c2ec` 에 고정한다(`pyproject.toml`).
- **Sensor 는 import 하지 않는다.** state-export `read` 의 결과(dict)만 받는다(BD-99 입력 원칙).
- S6(Sensor 의 "실행됐나")이 서면 그 상태도 같은 길로 읽는다(BD-99 의 6).

## 5. H1 제안과 다른 곳

| # | H1 제안 (docs/BOUNDARY.md §2) | 여기 | 까닭 |
|---|---|---|---|
| V1 | 근거에 값 · 유효성 · 규칙 판본을 싣는다 | **값 없이 참조**: 실체 · 상태 · `observed_at` · `time_base` | BD-99 의 결정. `time_base` 를 더한 까닭은 둘이다. `observed_at` 하나로는 어느 시계의 수인지 모른다(BD-33). `TIME_BASE_MISMATCH` 의 근거이기도 하다 |
| V2 | 창이 닫혔을 때 "**모든** 절이 쓸 만하고 하나라도 거짓" 이면 NOT_VERIFIED | 쓸 만한 근거로 **거짓인 절이 하나라도** 있으면 NOT_VERIFIED | 논리곱에서는 거짓 하나로 답이 정해진다(거짓 ∧ 모름 = 거짓). 다른 절이 모름이라는 까닭으로 UNKNOWN 을 내면, 알고 있는 실패를 가린다 |
| V3 | 까닭 낱말 일곱 | `UNRESOLVED_ENTITY` 를 더해 여덟 | 겨냥 없는 명령(STOP · ESCALATE)의 `$target` 은 풀 수 없다. 이것은 "관측 없음" 과 다르다 |
| V4 | `pred` 는 MS 술어 꼴 | 속성 참조(`{"prop"}`)는 받지 않는다 | 절은 한 실체의 한 상태다. 필요하면 판본을 올려 더한다 |
| V5 | `action_state` 실체 `action:<scope>:<command_id>` | `action:<run>:<command_id>` · 칸 `run` | BD-99 |

## 6. 범위

- **지었다**: 꼴 · 판정 함수 · 술어(MS 꼴, 일부).
- **짓지 않았다**
  - `action_state` State 를 내보내는 일 — State 꼴은 Sensor 와 같은 것을 쓴다. 이 기록을 State 로 옮기는 길은 소비자(DC `HealthSource`)와 함께 정한다.
  - C11 실행기 고장 후보 진단.
  - 실데이터 — 실행기 · ActionSpec 사후조건이 아직 없다.
- 사후조건은 시험의 고정값이다. 집은 DC `purpose.ActionSpec` 이다(BD-99). DC 에 넣는 일은 실행기와 함께 지시된다.
- 표준 라이브러리와 action 계약만 쓴다. 다른 저장소는 고치지 않았다.
