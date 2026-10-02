# BOUNDARY — Health 의 경계 조사 · VerificationRecord 꼴 제안 (CMD-H1)

지시: baseline#9 CMD-H1 (보고 + 꼴 제안만, 코드 옮김 없음).
읽은 머리(모두 `claude/gracious-meitner-vp49xe`, 읽기 전용):

| 저장소 | 커밋 |
|---|---|
| baseline | `d6e52a2` (BD-98) |
| Sensor | `10bb7ad` (stage-1) |
| action | `443f8eb` |
| Telemetry | `d60d591` (CMD-T16) |
| DC | `1387318` |

이 문서는 **제안**이다. 상태 · 계약 · 파일 이동은 baseline 이 정한다.

---

## 1. ASSESS 표시 상태 여섯 — 어디에 두나

가르는 기준(지시 그대로):
- 규칙이 여러 실체 · 관계를 묶나
- 운영자 문턱이 있나

BASELINE §10.1 의 층 정의도 함께 대었다.
- **L1 Sensor** = MEASURE + ASSESS 의 **탐지 판독**(운영자 문턱이 있는 판독 · 사건).
- **Health** = ASSESS 의 **진단 · 격리** · VERIFY.

### 1.1 코드에서 뽑은 사실

`python3 eval/assess_inventory.py <Sensor 체크아웃>` 의 출력 그대로다.

| 상태 | 규칙 | 실체 | 근거 | 실체마다 | 설정 문턱 | 다른 상태 읽음 | 관계 읽음 |
|---|---|---|---|---|---|---|---|
| `execution_health` | `execution-health-v3@3` | agent | DEFINITIONAL | - | 없음 | 아니오 | 아니오 |
| `tool_execution_health` | `tool-execution-health-v2@2` | tool | DEFINITIONAL | 예 | 없음 | 아니오 | 아니오 |
| `runtime_reliability` | `runtime-reliability-v2@2` | runtime | DEFINITIONAL | - | 없음 | 아니오 | 아니오 |
| `execution_interruption` | `execution-interruption-v3@3` | agent | RUNTIME_DECLARED | - | 없음 | 아니오 | 아니오 |
| `liveness_state` | `liveness-state-v2@2` | task | DEFINITIONAL | - | liveness_timeout_ms (값별 OPERATOR_ASSUMED) | 아니오 | 아니오 |
| `dependency_fault` | `dependency-fault-v1@1` | dependency | RUNTIME_DECLARED | 예 | 없음 | 아니오 | 아니오 |

state-export `llmsensor.state-export/2` 의 함수는 `catalog` · `read` · `subjects` · `as_of` · `entity_ref` 다. **관계를 내보내는 함수는 없다.**

손으로도 확인했다(`llmsensor/state/engine.py`).
- 규칙의 입력은 모두 그 실행 원장(`L`)에서 계산한 지표다. 다른 상태(`E.current`)를 읽는 규칙 · 지표는 없다.
- 엔진은 관계 셋(`uses` · `executed_by` · `runs_on`)을 **쓰기만** 한다(`_relate`). 읽는 규칙은 없다.
- 관계 가운데 `observes` 는 없다. 의존 대상(`dependency:*`)으로 가는 간선도 없다.

### 1.2 판정

| 상태 | 판정 | 까닭 |
|---|---|---|
| `execution_health` | **(a) Sensor 에 남는다** | 한 실체(agent)의 원장에서 겨냥마다 마지막 결과를 본다. 정의에서 나온 탐지다. 문턱 · 관계 · 다른 상태를 쓰지 않는다 |
| `tool_execution_health` | **(a)** | 같은 규칙을 도구마다 따로 세운다. 도구끼리 묶지 않는다 |
| `runtime_reliability` | **(a)** | 런타임이 보고한 API 오류 · 잘린 생성을 그대로 읽는다. 이름에 "reliability" 가 있지만 진단이 아니다. 뜻은 "실패를 봤나" 다 |
| `execution_interruption` | **(a)** | 런타임이 선언한 시간 초과 · 중단과 그 처분이다 |
| `liveness_state` | **(a)**, 진단은 그 위에 따로 선다 | ACTIVE · STALLED 는 운영자 문턱(`liveness_timeout_ms`)이 있는 **탐지 판독**이다. §10.1 은 이것을 L1 에 둔다. 규칙이 스스로 "DEAD 는 내지 않는다 — 기록이 끊긴 것만으로는 대상이 죽은 것과 수집이 죽은 것을 가를 수 없다" 고 적었다. 그 **가르기**가 Health 의 일이다(§3 C1). 옮길 것은 없다 |
| `dependency_fault` | **(a)**, 진단은 그 위에 따로 선다 | 파일 머리에 "격리" 라고 적혀 있다. 하지만 하는 일은 의존 대상 **하나**의 마지막 호출이 선언된 원인으로 실패했는지다. "agent 의 미해결 실패가 이 의존 대상 때문인가" 처럼 상태 사이를 잇는 일은 하지 않는다. 그 잇기가 Health 의 일이다 |

**결론: (b) · (c) 는 없다.** 여섯 모두 한 실체 · 한 원장에서 나오는 탐지다. Sensor 에 그대로 두는 것이 §10.1 과 맞다.

이 결론에서 셋이 따라 나온다(baseline 판단 필요 — §5).
1. BD-52 의 "`liveness_state` 는 Health 가 서면 옮긴다" 는 **옮기지 않는 쪽**이 맞다고 본다. 옮기면 DC 의 입력 경로(`SensorSource`)만 바뀌고 얻는 것이 없다.
2. Sensor 의 `owner_layer="ASSESS"` 표시는 "탐지" 와 "진단" 을 가르지 않는다.
   - 지금 상태 여섯은 탐지다. Health 가 지을 진단 상태도 ASSESS 다.
   - 표시를 `ASSESS/detect` 처럼 가르면 Health 와의 겹침이 이름에서 보인다.
   - 이것은 Sensor 파일이다 → 요청만 한다.
3. **Health 의 ASSESS 는 지금 아무 데도 없다.** 상태 · 관계를 읽어 고장의 원인과 범위를 가리는 층이다. Sensor 의 것을 옮겨 오는 것이 아니라 그 **위에** 새로 선다. 입력은 Sensor 원장이 아니라 **상태 + 관계**다.
   - 그런데 관계가 내보내지지 않는다.
   - 수집기 실체(`collector:*`)와 `observes` 간선도 없다.
   - → §4 의 틈 G1 · G2.

---

## 2. `VerificationRecord` 꼴 (제안 — `verification-record/1`)

근거:
- BD-31: ActionSpec 의 사후조건 · 검증 시간 창
- SCHEMA_PROPOSAL §2.6: Verification = State `action_state`
- SEMANTIC_MODEL: VERIFY 의 정의
- DATA_FLOW C11
- BD-90: 시간 기준을 섞지 않는다
- BD-96: `action-contract/1`

### 2.1 칸

action 꼴과 같은 방식으로 짓는다.
- 닫힌 꼴이다.
- `schema` 칸에 판본이 있다.
- 정준 JSON 과 내용 해시는 action `canonical.py` 의 규칙을 그대로 쓴다.

| 칸 | 타입 | 뜻 |
|---|---|---|
| `verification_id` | `ver-` + 16 hex | 내용 해시(아래 칸 전부) |
| `command_id` | `cmd-` + 16 hex | 검증하는 명령. = ActionCommand.`command_id` = L0 `action.*`.`action_ref` (CMD-T16) |
| `spec` | `"<ActionSpec 이름>@<판본>"` | 어느 사후조건으로 판정했나. 명령의 `action` 과 이름이 같다 |
| `postcondition` | [절] | 모든 절이 성립해야 한다(논리곱). 절 = `{"entity": <실체 지정>, "state": <상태 이름>, "in": [<값>…]}`. 실체 지정은 셋 중 하나다: `"$target"`(명령의 겨냥) · `"$run.<역할>"`(state-export `subjects` 의 agent · task · runtime) · 실체 id 그대로. **코드 · 식은 받지 않는다** — 재생과 결정론 때문이다 |
| `window` | `{"start_ms", "end_ms", "time_base": "unix_ms"}` | `start_ms` = 명령 `issued_at`. `end_ms` = `start_ms` + ActionSpec 의 창. 명령의 `deadline` 과는 다르다(그것은 실행기의 기한) |
| `outcome_ref` | str \| null | L0 `action.result` 사건 id(`action_ref` = `command_id`). 못 봤으면 null. 내용은 복사하지 않는다 |
| `evidence` | [근거] | 절마다 하나: `{"clause", "entity", "state", "value", "status", "freshness", "observed_at", "time_base", "rule": "<id>@<판본>", "evidence_refs"}`. state-export `read` 의 칸을 줄인 것이다 |
| `result` | `PENDING` · `VERIFIED` · `NOT_VERIFIED` · `UNKNOWN` | C11 의 값 그대로 |
| `reason` | 닫힌 낱말 하나 | `MET` · `WINDOW_OPEN` · `UNMET_AT_CLOSE` · `NO_POST_OBSERVATION` · `NOT_USABLE` · `TIME_BASE_MISMATCH` · `NO_SPEC` |
| `evaluated_at` | 수, unix_ms | 판정 시각 |
| `final` | bool | PENDING 만 false |
| `schema` | `verification-record/1` | |

### 2.2 판정 규칙 (위에서부터 처음 맞는 것)

1. ActionSpec 이나 사후조건이 없다 → `UNKNOWN / NO_SPEC`, final.
   - 사후조건이 없는 행동을 NOT_VERIFIED 라 하지 않는다.
2. 절마다 근거가 **쓸 만한지** 본다. 셋을 모두 지켜야 쓸 만하다.
   - status 가 OBSERVED · DERIVED · INFERRED 가운데 하나다(UNKNOWN · STALE · INVALID · NOT_APPLICABLE 은 아니다).
   - freshness 가 FRESH 나 PERMANENT 다(UNTIMED 는 창과 견줄 수 없다).
   - `observed_at ≥ window.start_ms` 이고, 시각 기준이 `unix_ms` 다.
   - **명령 전에 관측된 상태는 효과의 근거가 아니다.** 실행 전부터 참이던 값이 "검증됨" 을 만들면 안 된다.
3. 모든 절이 쓸 만하고 값이 `in` 안에 있다 → `VERIFIED / MET`, final.
   - 창이 끝나기 전이어도 그렇다.
4. `evaluated_at < window.end_ms` → `PENDING / WINDOW_OPEN`.
5. 창이 닫혔다.
   - 모든 절이 쓸 만하고, 하나라도 값이 `in` 밖이다 → `NOT_VERIFIED / UNMET_AT_CLOSE`, final.
   - 아니면 `UNKNOWN`, final. reason 은 `NO_POST_OBSERVATION` · `NOT_USABLE` · `TIME_BASE_MISMATCH` 가운데 해당하는 것이다.
   - "관측이 없다" 는 "효과가 없다" 가 아니다.

**실행기의 결과(`action.result`)는 판정에 들어가지 않는다.** DATA_FLOW: "실행기의 '됐다' 는 관측일 뿐이다".
- `outcome_ref` 로 잇기만 한다.
- 창이 닫혔는데 `outcome_ref` 가 null 이고 결과가 UNKNOWN 이면, 그 짝은 C11 실행기 고장 **후보**다. 이것은 Health 진단의 입력이다(§3).
- `action_state` 의 값을 바꾸지는 않는다.

### 2.3 `action_state` 와의 관계

- State `action_state` 는 실체 `action:<scope>:<command_id>` 위에 선다.
  - SCHEMA §2.6 은 `action:<command_id>` 다. BD-32 의 `<유형>:<범위>:<지역>` 꼴로 맞추자고 제안한다 → §5.
- State 의 값 = 마지막 VerificationRecord 의 `result`.
- `evidence_refs` = [`verification_id`].
- 기록은 **값이 바뀔 때만** 남는다(DATA_FLOW §4). PENDING → 끝 값이 보통 둘이다.
- 끝 값(final)은 다시 열리지 않는다. 같은 입력이면 같은 기록이다(내용 해시).

### 2.4 이음 — action 계약 · L0

| VerificationRecord | ActionCommand (`action-command/1`) | L0 `action.dispatch` | L0 `action.result` | ActionOutcome (`action-outcome/1`) |
|---|---|---|---|---|
| `command_id` | `command_id` | `action_ref` | `action_ref` | `command_id` |
| `spec` 의 이름 | `action` | `action_type`(실제 실행한 이름) | — | — |
| `window.start_ms` | `issued_at` (unix_ms) | 봉투 `at` 은 쓰지 않는다 — 원천의 시각 기준이 다를 수 있다(BD-90) | — | — |
| `postcondition` · `$target` | `target` (평문) | `target` (#해시) — 평문이 없어 실체를 풀 수 없다 | — | — |
| `outcome_ref` | — | — | 사건 id | 같은 칸(판정에 쓰지 않음) |
| (거슬러 감) | `decision_ref` → MS DecisionRecord | `decision_ref` | — | — |

- `$target` 은 **명령에서** 풀어야 한다. L0 의 target 은 해시뿐이기 때문이다(action CONTRACT §4).
  - 그래서 VERIFY 는 L0 만으로는 서지 않는다. ActionCommand 를 읽을 길(실행기 원장 또는 action 꼴)이 있어야 한다.
- `decision_ref` 는 칸으로 두지 않는다. `command_id` 로 명령에서 거슬러 간다(이름 둘을 두지 않는다).

### 2.5 중복 위험 — Sensor S6

DATA_FLOW §7 · TELEMETRY.md: L1 `action_outcome` 팩(Sensor 소유)은 아직 없다. 이 팩은 dispatch/result 짝을 지어 STARTED · COMPLETED · FAILED · UNKNOWN 을 낸다.

VERIFY 가 L0 `action.*` 을 직접 짝지으면 같은 사실을 두 곳에서 계산한다. 경계를 이렇게 제안한다.
- **Sensor S6**: 실행됐나 · 끝났나. L0 짝짓기를 한다.
- **Health VERIFY**: 효과가 났나. 사후조건 상태를 본다.
- VERIFY 는 S6 상태를 state-export 로 읽는다. 그러면 `outcome_ref` 대신 S6 상태의 근거를 쓴다.

---

## 3. DATA_FLOW §5 FDIR — Health 가 맡을 줄

탐지(상태가 서는 것)는 Sensor · MS 가 이미 한다. 아래의 "Health 몫" 은 그 **위의** 진단 · 격리 · 확인이다.

| 줄 | Health 몫 | 그 입력 | 입력은 지금 어디서 오나 |
|---|---|---|---|
| C1 수집기 · 센서 어댑터 | **예 — 핵심.** "대상이 멈췄나, 수집이 멈췄나" 를 가른다. 수집기 하나 때문에 STALE · UNKNOWN 이 된 상태들을 고장 **하나**로 묶는다(공통 원인, §6.4-2) | `collector:*` liveness · `observes` 간선 · 실행의 `liveness_state` · 상태들의 STALE | **없음.** 수집기 실체 · `observes` 간선이 어디에도 없다. 기록 밖 채널(프로세스 확인 · 합성 점검)도 없다. `liveness_state` 만 Sensor state-export 에 있다 |
| C3 Provider | 일부 — 한 계정 한도(`rate_limit_state`)가 여러 실행을 막을 때 원인을 하나로 묶는다 | `rate_limit_state` · `runtime_reliability` · 실행 ↔ 계정 관계 | 상태는 Sensor export 에 있다. 계정 실체는 PC-20 / BD-32 가 진행 중이다. **관계는 내보내지 않는다** |
| C4 도구 | 일부 — 도구 실패(`tool_execution_health`)를 의존 대상 결함(`dependency_fault`)과 잇는다. 원인 있는 실패와 원인 없는 실패를 가른다 | 두 상태 · tool → dependency 간선 | 상태는 Sensor export 에 있다. **간선이 없다**(엔진 관계에 `dependency:*` 가 없다) |
| C5 상태 엔진 · 규칙 | 후보 — 재생 비교로 `state_engine.integrity` 를 낸다 | 기록 재생 결과 · 원장 | Sensor 엔진(재생 가능). 지금은 시험으로만 한다. 상태로 서지 않았다 |
| C11 실행기 | **예 — VERIFY.** `action_state` (§2). 창 안에 결과가 없으면 실행기 고장 후보를 낸다 | ActionCommand · ActionSpec 사후조건 · 그 뒤의 State · L0 `action.result` (또는 S6) | 명령: action 꼴이 동결됐고, 실행기는 **없다**. 사후조건: **없다**(DC `ActionSpec` = name · requires · meaning, MS `ToolSpec` 에도 없음). State: Sensor export. `action.result`: Telemetry Recorder(T16) |
| C13 사람 피드백 | 예(C1 의 일부) — `AWAITING_INPUT` 을 고장으로 세지 않게 한다 | `liveness_state` | Sensor export |

Health 몫이 아닌 줄:

| 줄 | 몫 |
|---|---|
| C2 ingest | MS 격리함 · 꼴 검증 |
| C6 계약 적합성 | 시퀀싱 |
| C7 DC 빌더 | DC |
| C8 정책 실행기 | MS usage-model 이 측정한 문턱으로 탐지한다 = 탐지 판독 |
| C9 · C10 | Guard 자신의 자기 관측 |
| C12 런타임 시계 | Runtime |

이 가운데 탐지 상태가 Health 진단의 **입력**이 될 수는 있다.

---

## 4. 틈 (지금 Health 가 서지 못하게 막는 것)

| # | 틈 | 막는 것 | 누구 파일 |
|---|---|---|---|
| G1 | state-export 가 관계를 내보내지 않는다. 엔진은 관계를 쓰지만 아무도 읽지 않는다 | Health ASSESS 전부(격리는 관계를 따라간다) | Sensor `state/export.py` = **DC 세션**(BD-56) · 엔진 = Sensor 세션 |
| G2 | `collector:*` 실체와 `observes` 간선이 없다 | C1 | L0 원천 정보(`source`) = Telemetry · 실체 id = BD-32 |
| G3 | tool → dependency 간선이 없다 | C4 의 원인 잇기 | Sensor 엔진 |
| G4 | ActionSpec 에 사후조건 · 창이 없다(BD-31 이 정했지만 짓지 않았다). ActionSpec 의 주인이 하나로 정해지지 않았다(DC `purpose.ActionSpec` · MS `ToolSpec`) | VERIFY 전부 | baseline 이 정할 일 |
| G5 | 실행기가 없다(§10.2) | VERIFY 의 실데이터 | Action |
| G6 | Sensor S6(`action_outcome`)이 없다 | §2.5 의 경계 | Sensor |
| G7 | L0 `action.dispatch.target` 은 해시뿐이다 | `$target` 을 L0 만으로 풀 수 없다. ActionCommand 를 읽어야 한다 | 설계상 맞다(평문 금지). 정보로만 적는다 |

---

## 5. baseline 에 묻는 것

1. **§1 판정**: 여섯 모두 Sensor 에 남는다. 그렇다면 BD-52 의 "옮긴다" 를 거두는가?
2. **표시**: Sensor `owner_layer` 를 탐지 · 진단으로 가를지(Sensor 세션의 일).
3. **Health 의 입력**: Health 는 Sensor state-export(+ 관계)**만** 읽는다. Sensor 원장 · 엔진을 import 하지 않는다. 이 원칙을 정할지. 그러면 G1(export 에 관계를 더함)이 Health 의 첫 의존이 된다.
4. **VerificationRecord**: §2 의 꼴을 받는가?
   - 특히 셋을 묻는다: `evidence` 에 값을 싣는 것, 실체 id 를 BD-32 꼴로 하는 것, 명령 전 관측을 근거에서 빼는 것.
   - `evidence` 에 값을 싣는 까닭: State 는 바뀌므로(M) 값 없이 재생할 수 없다. PC-09("근거에서 값 복사를 뺀다")와 부딪히는지 판단을 청한다.
5. **사후조건의 집(G4)**: ActionSpec 을 누가 갖나.
   - DC `purpose.ActionSpec` 을 넓힐까?
   - MS `ToolSpec` 을 쓸까?
   - baseline 계약으로 둘까?
6. **S6 과의 경계(§2.5)**: 받는가?
