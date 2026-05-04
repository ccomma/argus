from __future__ import annotations

"""工作合同核心模型模块。

定义了工作合同的完整数据模型，包括：
- 合同字段常量配置
- 澄清问题与提问策略
- 完整性评分
- 合同实体与会话管理
- 合同构建器

工作合同是 Argus 系统的核心概念——它是 AI 和人类之间的
一份结构化协议，定义了工作目标、约束条件、验收标准等关键维度。
"""

from dataclasses import asdict, dataclass, field
from hashlib import sha1
from time import time
from typing import Any
from uuid import uuid4


# ── 合同字段常量 ──

CONTRACT_FIELDS = (
    "goal",
    "context",
    "inputs",
    "outputs",
    "constraints",
    "risks",
    "acceptance_criteria",
)

# 按业务重要性排序的提问优先级：先问目标、输出、验收标准，
# 再问上下文、约束、输入和风险——因为前者直接影响交付物方向
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


# ── 澄清问题模型 ──

@dataclass(frozen=True)
class ClarifyingQuestion:
    """单个澄清问题。

    每个问题关联到合同的特定字段，用于在合同起草阶段
    引导用户逐步提供必要信息。

    Attributes:
        field: 对应的合同字段名
        question: 问题的文本描述
    """

    field: str
    question: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


# ── 提问策略模型 ──

@dataclass(frozen=True)
class QuestionStrategy:
    """合同提问策略。

    定义了在不同模式下（quick/standard/strict）的提问行为参数，
    包括必须收集的字段、决策节点、跟进规则、问题预算和完成阈值。

    三种模式对比：
    - quick: 最少问题（3个），低阈值（0.65），适合快速原型
    - standard: 标准问题（7个），中阈值（0.85），生产默认
    - strict: 最多问题（9个），高阈值（0.95），高风险场景
    """

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
        """快速模式：仅需目标、输出和验收标准，问题预算 3，阈值 0.65。"""
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
        """标准模式：需要全部合同字段，问题预算 7，阈值 0.85。"""
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
        """严格模式：需要全部字段加风险审查，问题预算 9，阈值 0.95。"""
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
        """根据模式字符串返回对应的策略实例。

        quick 和 strict 模式需要精准匹配，其余均回退到 standard。
        """
        if mode == "quick":
            return cls.quick()
        if mode == "strict":
            return cls.strict()
        return cls.standard()


# ── 完整性评分模型 ──

@dataclass
class CompletenessScore:
    """合同完整性评分。

    对合同的七个核心维度分别评分（0-1 区间），并计算综合得分。
    同时指出缺失字段和评分理由，帮助用户了解合同是否已准备好执行。

    Attributes:
        overall_score: 综合得分（0-1）
        missing_fields: 尚未填写的必填字段列表
        rationale: 评分原因的文字说明
    """

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


# ── 工作合同实体 ──

@dataclass
class WorkContract:
    """工作合同的核心数据实体。

    这是 Argus 系统中承载"人机工作协议"的数据对象。
    包含工作的意图、目标、上下文、输入输出、约束条件、风险、
    验收标准等关键维度，并记录版本的变更历史和执行的证据链。

    关键字段：
    - status: 'ready'（可执行）或 'clarifying'（需澄清）
    - completeness_score: 合同填写完整度的量化指标
    - change_history: 版本变更的审计记录
    - execution_evidence: 执行过程中的关键事件证据
    """

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


# ── 合同会话管理 ──


class ContractSession:
    """合同起草的交互式会话。

    管理一次合同起草过程中的问答流程。维护用户的意图、
    选定的提问策略和已收集到的答案。

    典型用法：
        session = ContractSession.start(intent, strategy)
        session.answer(goal="...", outputs="...")
        questions = session.next_questions()  # 获取追问
    """

    def __init__(self, intent: str, strategy: QuestionStrategy) -> None:
        self.intent = intent.strip()
        self.strategy = strategy
        self.answers: dict[str, str] = {}

    @classmethod
    def start(cls, intent: str, strategy: QuestionStrategy) -> ContractSession:
        """创建一个新的合同起草会话。

        Args:
            intent: 用户的工作意图
            strategy: 提问策略实例

        Returns:
            初始化好的 ContractSession
        """
        return cls(intent=intent, strategy=strategy)

    def answer(self, **answers: str) -> None:
        """接受用户对合同字段的回答。

        自动去除空白字符，忽略 None 值，避免脏数据写入合同。
        """
        for field_name, value in answers.items():
            if value is not None:
                self.answers[field_name] = str(value).strip()

    def next_questions(self) -> list[ClarifyingQuestion]:
        """获取下一批需要向用户提出的问题。

        流程：
        1. 找出所有必填字段中尚未回答的字段
        2. 按业务优先级（QUESTION_PRIORITY）排序
        3. 截取不超过策略设定的问题预算数

        这样确保最重要的字段（目标、输出、验收标准）最先被提问。
        """
        missing = [field_name for field_name in self.strategy.required_facts if not self.answers.get(field_name)]
        missing.sort(key=lambda field_name: QUESTION_PRIORITY.index(field_name))
        return [
            ClarifyingQuestion(field=field_name, question=QUESTION_TEXT[field_name])
            for field_name in missing[: self.strategy.question_budget]
        ]


# ── 合同构建器 ──


class WorkContractBuilder:
    """工作合同构建器。

    将合同会话（ContractSession）中的答案组装成完整的 WorkContract 对象。
    负责评分计算、状态判定、完成定义生成和版本初始化。
    """

    def build(self, session: ContractSession) -> WorkContract:
        """从会话构建完整的合同对象。

        流程：
        1. 对收集到的答案进行完整性评分
        2. 根据评分与阈值的比较判定合同状态（ready / clarifying）
        3. 基于意图的 SHA1 摘要生成唯一合同 ID
        4. 生成或提取完成定义（completion_definition）
        5. 组装所有字段为 WorkContract 实例
        """
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


# ── 评分函数 ──


def score_answers(answers: dict[str, str], strategy: QuestionStrategy) -> CompletenessScore:
    """对用户提交的答案进行完整性评分。

    流程：
    1. 对 CONTRACT_FIELDS 中的每个字段独立评分（0.0 / 0.5 / 1.0）
    2. 仅基于策略要求的必填字段计算综合得分
    3. 收集未达标（得分为 0）的必填字段
    4. 生成评分理由

    评分粒度：
    - 0.0: 字段为空
    - 0.5: 有内容但过短（< 12 字符）
    - 1.0: 有实质性内容
    """
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
    """对单个字段打分。

    - 空字符串 → 0.0（未填写）
    - 少于 12 字符 → 0.5（填写不充分）
    - 12 字符及以上 → 1.0（填写充分）
    12 字符的阈值是权衡了"有实质内容"和"不过分严格"的经验值。
    """
    text = value.strip()
    if not text:
        return 0.0
    if len(text) < 12:
        return 0.5
    return 1.0


def _contract_id(intent: str) -> str:
    """基于意图文本生成合同唯一 ID。

    使用 SHA1 摘要的前 10 位加 UUID 前 8 位，兼顾可追溯性和唯一性。
    """
    digest = sha1(intent.strip().encode("utf-8")).hexdigest()[:10]
    return f"contract-{digest}-{uuid4().hex[:8]}"


def _confirmation_points(answers: dict[str, str]) -> list[str]:
    """从答案中提取确认节点。

    如果用户明确提供了确认节点（分号分隔），直接解析；
    否则基于约束和验收标准自动生成合理的确认提示。
    """
    explicit = answers.get("confirmation_points", "").strip()
    if explicit:
        return [item.strip() for item in explicit.split(";") if item.strip()]
    points = []
    if answers.get("constraints"):
        points.append("Confirm constraints before execution.")
    if answers.get("acceptance_criteria"):
        points.append("Confirm acceptance criteria before final delivery.")
    return points
