"""Health -- ASSESS 진단 · 격리 · VERIFY (baseline BD-22 · BD-99).

지금 있는 것: VERIFY 의 기록 꼴 `verification-record/1` 과 순수 판정 함수 `verify` (baseline#9 CMD-H2).
"""
from .predicate import check as check_predicate, holds
from .verification import (REASONS, RESULTS, SCHEMA, VerificationRecord, action_entity, verify)

__all__ = ["SCHEMA", "RESULTS", "REASONS", "VerificationRecord", "verify", "action_entity", "check_predicate", "holds"]
