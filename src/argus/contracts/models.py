from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha1
from time import time
from typing import Any
from uuid import uuid4


CONTRACT_FIELDS = (
    "goal",
    "context",
    "inputs",
    "outputs",
    "constraints",
    "risks",
    "acceptance_criteria",
)

QUESTION_PRIORITY = (
    "goal",
    "outputs",
    "acceptance_criteria",
    "context",
    "constraints",
    "inputs",
    "risks",
)


QUESTION_TEXT = {
    "goal": "What outcome should this work achieve?",
    "context": "What background or current situation should Argus know?",
    "inputs": "What source material or existing context is available?",
    "outputs": "What deliverable should be produced?",
    "constraints": "What constraints, boundaries, or non-goals should apply?",
    "risks": "What risks, assumptions, or unknowns matter?",
    "acceptance_criteria": "How will you know the result is good enough?",
}


@dataclass(frozen=True)
class ClarifyingQuestion:
    field: str
    question: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class QuestionStrategy:
    id: str
    name: str
    mode: str
    required_facts: tuple[str, ...]
    decision_points: tuple[str, ...]
    follow_up_rules: tuple[str, ...]
    question_budget: int
    completion_threshold: float

    @classmethod
    def quick(cls) -> QuestionStrategy:
        return cls(
            id="quick-work-contract",
            name="Quick Work Contract",
            mode="quick",
            required_facts=("goal", "outputs", "acceptance_criteria"),
            decision_points=("scope",),
            follow_up_rules=("ask_missing_required_facts",),
            question_budget=3,
            completion_threshold=0.65,
        )

    @classmethod
    def standard(cls) -> QuestionStrategy:
        return cls(
            id="standard-work-contract",
            name="Standard Work Contract",
            mode="standard",
            required_facts=CONTRACT_FIELDS,
            decision_points=("scope", "deliverable", "risk"),
            follow_up_rules=("ask_missing_required_facts", "ask_until_ready"),
            question_budget=7,
            completion_threshold=0.85,
        )

    @classmethod
    def strict(cls) -> QuestionStrategy:
        return cls(
            id="strict-work-contract",
            name="Strict Work Contract",
            mode="strict",
            required_facts=CONTRACT_FIELDS,
            decision_points=("scope", "deliverable", "risk", "review", "handoff"),
            follow_up_rules=("ask_missing_required_facts", "ask_until_ready", "require_risk_review"),
            question_budget=9,
            completion_threshold=0.95,
        )

    @classmethod
    def for_mode(cls, mode: str) -> QuestionStrategy:
        if mode == "quick":
            return cls.quick()
        if mode == "strict":
            return cls.strict()
        return cls.standard()


@dataclass
class CompletenessScore:
    goal_score: float
    context_score: float
    input_score: float
    output_score: float
    constraint_score: float
    risk_score: float
    acceptance_score: float
    overall_score: float
    missing_fields: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompletenessScore:
        return cls(**data)


@dataclass
class WorkContract:
    id: str
    version: int
    status: str
    intent: str
    questioning_mode: str
    goal: str = ""
    context: str = ""
    audience: str = ""
    inputs: str = ""
    outputs: str = ""
    non_goals: str = ""
    constraints: str = ""
    risks: str = ""
    confirmation_points: list[str] = field(default_factory=list)
    acceptance_criteria: str = ""
    completion_definition: str = ""
    role_or_work_mode: str = ""
    capability_pack_ref: str = ""
    completeness_score: CompletenessScore = field(default_factory=lambda: score_answers({}, QuestionStrategy.quick()))
    change_history: list[dict[str, Any]] = field(default_factory=list)
    execution_evidence: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["completeness_score"] = self.completeness_score.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkContract:
        copied = dict(data)
        copied["completeness_score"] = CompletenessScore.from_dict(copied["completeness_score"])
        return cls(**copied)


class ContractSession:
    def __init__(self, intent: str, strategy: QuestionStrategy) -> None:
        self.intent = intent.strip()
        self.strategy = strategy
        self.answers: dict[str, str] = {}

    @classmethod
    def start(cls, intent: str, strategy: QuestionStrategy) -> ContractSession:
        return cls(intent=intent, strategy=strategy)

    def answer(self, **answers: str) -> None:
        for field_name, value in answers.items():
            if value is not None:
                self.answers[field_name] = str(value).strip()

    def next_questions(self) -> list[ClarifyingQuestion]:
        missing = [field_name for field_name in self.strategy.required_facts if not self.answers.get(field_name)]
        missing.sort(key=lambda field_name: QUESTION_PRIORITY.index(field_name))
        return [
            ClarifyingQuestion(field=field_name, question=QUESTION_TEXT[field_name])
            for field_name in missing[: self.strategy.question_budget]
        ]


class WorkContractBuilder:
    def build(self, session: ContractSession) -> WorkContract:
        score = score_answers(session.answers, session.strategy)
        status = "ready" if score.overall_score >= session.strategy.completion_threshold else "clarifying"
        contract_id = _contract_id(session.intent)
        completion_definition = session.answers.get(
            "completion_definition",
            f"Done when acceptance criteria are satisfied: {session.answers.get('acceptance_criteria', '').strip()}",
        ).strip()
        return WorkContract(
            id=contract_id,
            version=1,
            status=status,
            intent=session.intent,
            questioning_mode=session.strategy.mode,
            goal=session.answers.get("goal", ""),
            context=session.answers.get("context", ""),
            audience=session.answers.get("audience", ""),
            inputs=session.answers.get("inputs", ""),
            outputs=session.answers.get("outputs", ""),
            non_goals=session.answers.get("non_goals", ""),
            constraints=session.answers.get("constraints", ""),
            risks=session.answers.get("risks", ""),
            confirmation_points=_confirmation_points(session.answers),
            acceptance_criteria=session.answers.get("acceptance_criteria", ""),
            completion_definition=completion_definition,
            role_or_work_mode=session.answers.get("role_or_work_mode", ""),
            completeness_score=score,
            change_history=[{"version": 1, "reason": "initial_contract", "timestamp": int(time())}],
            execution_evidence=[],
        )


def score_answers(answers: dict[str, str], strategy: QuestionStrategy) -> CompletenessScore:
    field_scores = {field_name: _field_score(answers.get(field_name, "")) for field_name in CONTRACT_FIELDS}
    required = strategy.required_facts
    missing = [field_name for field_name in required if field_scores[field_name] == 0.0]
    overall = round(sum(field_scores[field_name] for field_name in required) / len(required), 2)
    if missing:
        rationale = f"Missing required fields: {', '.join(missing)}."
    else:
        rationale = "Ready: all required work contract facts are present."
    return CompletenessScore(
        goal_score=field_scores["goal"],
        context_score=field_scores["context"],
        input_score=field_scores["inputs"],
        output_score=field_scores["outputs"],
        constraint_score=field_scores["constraints"],
        risk_score=field_scores["risks"],
        acceptance_score=field_scores["acceptance_criteria"],
        overall_score=overall,
        missing_fields=missing,
        rationale=rationale,
    )


def _field_score(value: str) -> float:
    text = value.strip()
    if not text:
        return 0.0
    if len(text) < 12:
        return 0.5
    return 1.0


def _contract_id(intent: str) -> str:
    digest = sha1(intent.strip().encode("utf-8")).hexdigest()[:10]
    return f"contract-{digest}-{uuid4().hex[:8]}"


def _confirmation_points(answers: dict[str, str]) -> list[str]:
    explicit = answers.get("confirmation_points", "").strip()
    if explicit:
        return [item.strip() for item in explicit.split(";") if item.strip()]
    points = []
    if answers.get("constraints"):
        points.append("Confirm constraints before execution.")
    if answers.get("acceptance_criteria"):
        points.append("Confirm acceptance criteria before final delivery.")
    return points
