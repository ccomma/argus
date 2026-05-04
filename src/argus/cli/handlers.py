"""CLI 命令注册表 - 集中映射 (command, subcommand) 二元组到 handler 函数。

所有 handler 返回 int 退出码（0=成功，非0=错误）。
"""

from __future__ import annotations

from argus.cli.contracts import (
    handle_contract_bind_pack,
    handle_contract_draft,
    handle_contract_evaluate,
    handle_contract_list,
    handle_contract_render,
    handle_contract_score,
    handle_contract_show,
    handle_contract_start,
    handle_ledger_ingest_contract,
    handle_ledger_ingest_transcript,
    handle_ledger_list,
    handle_learning_extract,
    handle_learning_list,
    handle_learning_report,
)
from argus.cli.assets import (
    handle_assets_list,
    handle_assets_link_learnings,
    handle_assets_report,
    handle_assets_scan,
)
from argus.cli.packs import (
    handle_packs_advise,
    handle_packs_check,
    handle_packs_create,
    handle_packs_inspect,
    handle_packs_list,
    handle_packs_propose,
    handle_roles_check_pack,
    handle_roles_create_pack,
    handle_roles_inspect_pack,
    handle_roles_list,
)
from argus.cli.governance import handle_governance_report, handle_resolve_report, handle_resolve_run
from argus.cli.modification import (
    handle_modify_apply,
    handle_modify_audit_log,
    handle_modify_contract_apply,
    handle_modify_contract_preview,
    handle_modify_preview,
    handle_modify_report,
    handle_modify_rollback,
)
from argus.cli.query import handle_mcp_serve, handle_query_contract, handle_query_role
from argus.cli.dashboard import (
    handle_dashboard,
    handle_maintenance_report,
    handle_maintenance_run,
)
from argus.cli.workbench import (
    handle_feedback_list,
    handle_feedback_recommend,
    handle_feedback_record,
    handle_lifecycle_apply,
    handle_lifecycle_history,
    handle_lifecycle_show,
    handle_onboarding_generate,
    handle_playbook_create,
    handle_playbook_delete,
    handle_playbook_list,
    handle_playbook_show,
    handle_registry_add,
    handle_registry_list,
    handle_registry_search,
    handle_security_scan,
    handle_strategy_reset,
    handle_strategy_set_rule,
    handle_strategy_show,
    handle_team_add_member,
    handle_team_catalog,
    handle_team_create,
    handle_team_list,
    handle_team_policy_set,
    handle_team_policy_show,
    handle_team_remove_member,
    handle_team_show,
    handle_version_lock_list,
    handle_version_lock_lock,
    handle_version_lock_unlock,
    handle_web_serve,
)

# 全量 handler 注册表：顶层命令用字符串 key，二级命令用 (command, subcommand) 元组
HANDLERS: dict = {
    # Contract
    ("contract", "draft"): handle_contract_draft,
    ("contract", "start"): handle_contract_start,
    ("contract", "evaluate"): handle_contract_evaluate,
    ("contract", "show"): handle_contract_show,
    ("contract", "score"): handle_contract_score,
    ("contract", "render"): handle_contract_render,
    ("contract", "bind-pack"): handle_contract_bind_pack,
    ("contract", "list"): handle_contract_list,
    # Ledger
    ("ledger", "ingest-contract"): handle_ledger_ingest_contract,
    ("ledger", "ingest-transcript"): handle_ledger_ingest_transcript,
    ("ledger", "list"): handle_ledger_list,
    # Learning
    ("learning", "extract"): handle_learning_extract,
    ("learning", "list"): handle_learning_list,
    ("learning", "report"): handle_learning_report,
    # Assets
    ("assets", "scan"): handle_assets_scan,
    ("assets", "list"): handle_assets_list,
    ("assets", "report"): handle_assets_report,
    ("assets", "link-learnings"): handle_assets_link_learnings,
    # Packs
    ("packs", "propose"): handle_packs_propose,
    ("packs", "create"): handle_packs_create,
    ("packs", "inspect"): handle_packs_inspect,
    ("packs", "check"): handle_packs_check,
    ("packs", "advise"): handle_packs_advise,
    ("packs", "list"): handle_packs_list,
    # Roles
    ("roles", "create-pack"): handle_roles_create_pack,
    ("roles", "inspect-pack"): handle_roles_inspect_pack,
    ("roles", "check-pack"): handle_roles_check_pack,
    ("roles", "list"): handle_roles_list,
    # Governance + Resolution
    ("governance", "report"): handle_governance_report,
    ("resolve", "run"): handle_resolve_run,
    ("resolve", "report"): handle_resolve_report,
    # Modification
    ("modify", "preview"): handle_modify_preview,
    ("modify", "apply"): handle_modify_apply,
    ("modify", "contract-preview"): handle_modify_contract_preview,
    ("modify", "contract-apply"): handle_modify_contract_apply,
    ("modify", "rollback"): handle_modify_rollback,
    ("modify", "audit-log"): handle_modify_audit_log,
    ("modify", "report"): handle_modify_report,
    # Query + MCP
    ("query", "contract"): handle_query_contract,
    ("query", "role"): handle_query_role,
    "mcp_serve": handle_mcp_serve,
    # Dashboard + Maintenance
    "dashboard": handle_dashboard,
    ("maintenance", "run"): handle_maintenance_run,
    ("maintenance", "report"): handle_maintenance_report,
    # Workbench
    "web": handle_web_serve,
    ("strategy", "show"): handle_strategy_show,
    ("strategy", "set-rule"): handle_strategy_set_rule,
    ("strategy", "reset"): handle_strategy_reset,
    ("playbook", "create"): handle_playbook_create,
    ("playbook", "list"): handle_playbook_list,
    ("playbook", "show"): handle_playbook_show,
    ("playbook", "delete"): handle_playbook_delete,
    ("version-lock", "lock"): handle_version_lock_lock,
    ("version-lock", "unlock"): handle_version_lock_unlock,
    ("version-lock", "list"): handle_version_lock_list,
    ("security", "scan"): handle_security_scan,
    # Team + Onboarding
    ("team", "create"): handle_team_create,
    ("team", "add-member"): handle_team_add_member,
    ("team", "remove-member"): handle_team_remove_member,
    ("team", "show"): handle_team_show,
    ("team", "list"): handle_team_list,
    ("team", "catalog"): handle_team_catalog,
    ("team", "policy"): handle_team_policy_show,
    ("team", "set-policy"): handle_team_policy_set,
    ("onboarding", "generate"): handle_onboarding_generate,
    # OS
    ("lifecycle", "show"): handle_lifecycle_show,
    ("lifecycle", "apply"): handle_lifecycle_apply,
    ("lifecycle", "history"): handle_lifecycle_history,
    ("registry", "search"): handle_registry_search,
    ("registry", "add"): handle_registry_add,
    ("registry", "list"): handle_registry_list,
    ("feedback", "record"): handle_feedback_record,
    ("feedback", "list"): handle_feedback_list,
    ("feedback", "recommend"): handle_feedback_recommend,
}
