from __future__ import annotations

"""合同持久化存储模块。

提供 ContractStorage 类，负责工作合同及其交付物、评估结果
和证据链的 JSON 文件持久化。所有数据以结构化目录形式保存
在本地的 .argus 目录下，支持版本管理和审计追溯。
"""

import json
from pathlib import Path

from argus.contracts import DeliverableEvaluation, WorkContract, deliverable_evaluated_event, deliverable_rendered_event


class ContractStorage:
    """工作合同的本地文件系统存储。

    在 .argus/contracts/ 目录下维护每个合同的完整生命周期数据：
    - contract.json / contract.md：合同正文
    - versions/：版本历史快照
    - evaluations/：交付物评估记录
    - deliverables/：渲染后的交付物文档
    - evidence.jsonl：证据链追加日志
    """

    def __init__(self, root: str | Path = ".argus") -> None:
        """初始化存储。

        Args:
            root: 存储根目录，默认为 `.argus`
        """
        self.root = Path(root)

    def save_contract(self, contract: WorkContract) -> None:
        """保存合同，同时生成 JSON、Markdown 和版本快照。

        流程：
        1. 创建或获取合同的目录结构
        2. 写入 contract.json（结构化数据）
        3. 写入 contract.md（可读的 Markdown 格式）
        4. 在 versions/ 目录下保存带版本号的快照

        这样可以同时满足机器读取、人类阅读和版本回溯三种需求。
        """
        contract_dir = self._contract_dir(contract.id)
        versions_dir = contract_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(contract_dir / "contract.json", contract.to_dict())
        (contract_dir / "contract.md").write_text(_contract_markdown(contract), encoding="utf-8")
        self._write_json(versions_dir / f"v{contract.version}.json", contract.to_dict())

    def load_contract(self, contract_id: str) -> WorkContract:
        """从文件系统加载合同。

        Args:
            contract_id: 合同唯一标识符

        Returns:
            反序列化后的 WorkContract 实例
        """
        path = self._contract_dir(contract_id) / "contract.json"
        return WorkContract.from_dict(self._read_json(path))

    def list_contracts(self) -> list[WorkContract]:
        """列出所有已保存的合同。

        Returns:
            所有合同的列表，按路径排序
        """
        contracts_dir = self.root / "contracts"
        if not contracts_dir.exists():
            return []
        contracts: list[WorkContract] = []
        for path in sorted(contracts_dir.glob("*/contract.json")):
            contracts.append(WorkContract.from_dict(self._read_json(path)))
        return contracts

    def save_evaluation(self, contract_id: str, evaluation: DeliverableEvaluation) -> None:
        """保存交付物评估结果。

        流程：
        1. 在合同目录的 evaluations/ 下创建带递增编号的 JSON 文件
        2. 将评估事件追加到证据链日志中
        这样保持评估历史完整可追溯，避免覆盖旧评估。
        """
        evaluations_dir = self._contract_dir(contract_id) / "evaluations"
        evaluations_dir.mkdir(parents=True, exist_ok=True)
        index = len(list(evaluations_dir.glob("*.json"))) + 1
        self._write_json(evaluations_dir / f"evaluation-{index}.json", evaluation.to_dict())
        self.append_evidence(contract_id, deliverable_evaluated_event(evaluation))

    def list_evaluations(self, contract_id: str) -> list[DeliverableEvaluation]:
        """列出某合同的所有历史评估记录。

        Args:
            contract_id: 合同 ID

        Returns:
            按时间排序的评估记录列表
        """
        evaluations_dir = self._contract_dir(contract_id) / "evaluations"
        if not evaluations_dir.exists():
            return []
        return [
            DeliverableEvaluation.from_dict(self._read_json(path))
            for path in sorted(evaluations_dir.glob("*.json"))
        ]

    def save_deliverable(self, contract_id: str, deliverable_type: str, text: str) -> Path:
        """保存渲染后的交付物文档。

        流程：
        1. 在合同目录的 deliverables/ 下写入 Markdown 文件
        2. 将渲染事件追加到证据链日志

        Args:
            contract_id: 合同 ID
            deliverable_type: 交付物类型
            text: 交付物 Markdown 内容

        Returns:
            保存的文件路径
        """
        deliverables_dir = self._contract_dir(contract_id) / "deliverables"
        deliverables_dir.mkdir(parents=True, exist_ok=True)
        path = deliverables_dir / f"{deliverable_type}.md"
        path.write_text(text, encoding="utf-8")
        self.append_evidence(contract_id, deliverable_rendered_event(deliverable_type, path))
        return path

    def append_evidence(self, contract_id: str, event: dict) -> None:
        """向证据链 JSONL 文件追加一条事件记录。

        采用追加模式（append），不会覆盖已有记录，确保审计完整性。
        """
        path = self._contract_dir(contract_id) / "evidence.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def save_contract_artifact(self, contract_id: str, name: str, data: dict) -> Path:
        """保存合同相关的任意工件（如绑定信息等）。

        Args:
            contract_id: 合同 ID
            name: 工件文件名
            data: 工件数据字典

        Returns:
            保存的文件路径
        """
        path = self._contract_dir(contract_id) / name
        self._write_json(path, data)
        return path

    def list_evidence(self, contract_id: str) -> list[dict]:
        """读取某合同的完整证据链。

        Returns:
            证据事件字典的列表，按追加顺序排列
        """
        path = self._contract_dir(contract_id) / "evidence.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def contract_markdown_path(self, contract_id: str) -> Path:
        """获取合同 Markdown 文件的路径。

        Args:
            contract_id: 合同 ID

        Returns:
            contract.md 文件的路径
        """
        return self._contract_dir(contract_id) / "contract.md"

    def _contract_dir(self, contract_id: str) -> Path:
        """获取合同在文件系统中的专属目录路径。

        所有合同数据统一存放在 .argus/contracts/<contract_id>/ 下。
        """
        return self.root / "contracts" / contract_id

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        """以美化格式写入 JSON 文件，自动创建父目录。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict:
        """从文件读取并解析 JSON。"""
        return json.loads(path.read_text(encoding="utf-8"))


def _contract_markdown(contract: WorkContract) -> str:
    """将 WorkContract 转换为人类可读的 Markdown 表示。

    输出的文档包含合同的所有关键维度，便于在编辑器中直接阅读和审查。
    """
    return "\n".join(
        [
            f"# Work Contract: {contract.id}",
            "",
            f"- Status: {contract.status}",
            f"- Version: {contract.version}",
            f"- Mode: {contract.questioning_mode}",
            "",
            "## Intent",
            contract.intent,
            "",
            "## Goal",
            contract.goal or "Not specified.",
            "",
            "## Context",
            contract.context or "Not specified.",
            "",
            "## Inputs",
            contract.inputs or "Not specified.",
            "",
            "## Outputs",
            contract.outputs or "Not specified.",
            "",
            "## Constraints",
            contract.constraints or "Not specified.",
            "",
            "## Risks",
            contract.risks or "Not specified.",
            "",
            "## Acceptance Criteria",
            contract.acceptance_criteria or "Not specified.",
            "",
            "## Completeness",
            f"{contract.completeness_score.overall_score}: {contract.completeness_score.rationale}",
            "",
        ]
    )
