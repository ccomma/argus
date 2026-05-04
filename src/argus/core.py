from __future__ import annotations

"""Argus 核心编排器模块。

提供 ArgusCore 类，作为 Phase 1 工作流的应用边界层，统一协调
合同起草、交付物渲染和交付物评估等核心操作的完整生命周期。
CLI、MCP 工具以及未来的适配器都应通过此层调用，而非直接
拼凑底层模块。
"""

from argus.contracts import (
    ContractSession,
    DeliverableContract,
    DeliverableEvaluation,
    DeliverableEvaluator,
    DeliverableRenderer,
    QuestionStrategy,
    WorkContract,
    WorkContractBuilder,
)
from argus.storage import ContractStorage


class ArgusCore:
    """Argus 中央编排器。

    负责协调工作合同的全生命周期管理，包括合同的起草、加载、
    交付物渲染和评估。作为应用层的外观（Facade），对外屏蔽
    内部各模块的协作细节。

    生命周期流程：draft_contract → render_deliverable → evaluate_deliverable
    """

    def __init__(self, storage: ContractStorage) -> None:
        """初始化编排器。

        Args:
            storage: 合同持久化存储实例，负责 JSON 文件的读写。
        """
        self.storage = storage

    def draft_contract(
        self,
        *,
        intent: str,
        mode: str,
        answers: dict[str, str],
    ) -> WorkContract:
        """起草一份新的工作合同。

        根据用户意图、提问模式和预设答案创建合同，并自动持久化。

        流程：
        1. 根据意图和模式启动合同会话（ContractSession）
        2. 填入用户预设的答案
        3. 通过 WorkContractBuilder 构建完整的合同对象
        4. 将合同保存到持久化存储

        Args:
            intent: 用户的工作意图描述
            mode: 提问模式（quick / standard / strict）
            answers: 用户对合同各字段的预设答案

        Returns:
            构建完成并已持久化的 WorkContract 实例
        """
        session = ContractSession.start(intent, QuestionStrategy.for_mode(mode))
        session.answer(**answers)
        contract = WorkContractBuilder().build(session)
        self.storage.save_contract(contract)
        return contract

    def load_contract(self, contract_id: str) -> WorkContract:
        """从持久化存储中加载已有合同。

        Args:
            contract_id: 合同的唯一标识符

        Returns:
            反序列化后的 WorkContract 实例
        """
        return self.storage.load_contract(contract_id)

    def render_deliverable(self, contract_id: str, deliverable_type: str) -> str:
        """根据合同内容渲染生成交付物文档。

        流程：
        1. 从存储加载合同
        2. 按交付物类型获取对应的交付物合约定义
        3. 调用渲染器将合同内容填充到交付物模板中
        4. 将渲染结果持久化为 .md 文件

        Args:
            contract_id: 合同 ID
            deliverable_type: 交付物类型（prd / roadmap / research_plan）

        Returns:
            渲染后的交付物 Markdown 文本
        """
        contract = self.storage.load_contract(contract_id)
        deliverable_contract = DeliverableContract.for_type(deliverable_type)
        rendered = DeliverableRenderer().render(contract, deliverable_contract)
        self.storage.save_deliverable(contract.id, deliverable_contract.deliverable_type, rendered)
        return rendered

    def evaluate_deliverable(
        self,
        *,
        contract_id: str,
        deliverable_type: str,
        text: str,
    ) -> DeliverableEvaluation:
        """评估交付物文本的完整性和质量。

        流程：
        1. 从存储加载合同
        2. 获取对应类型的交付物合约定义
        3. 检查交付物是否覆盖了所有必要章节和验收标准
        4. 将评估结果持久化

        Args:
            contract_id: 合同 ID
            deliverable_type: 交付物类型
            text: 待评估的交付物文本内容

        Returns:
            包含通过/部分通过/失败状态及缺失项列表的评估结果
        """
        contract = self.storage.load_contract(contract_id)
        result = DeliverableEvaluator().evaluate(
            contract=contract,
            deliverable_contract=DeliverableContract.for_type(deliverable_type),
            text=text,
        )
        self.storage.save_evaluation(contract.id, result)
        return result
