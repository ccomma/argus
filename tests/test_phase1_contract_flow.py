import tempfile
import unittest

from argus.contracts import ContractSession, DeliverableContract, DeliverableEvaluator, DeliverableRenderer, QuestionStrategy, WorkContractBuilder
from argus.storage import ContractStorage


class Phase1ContractFlowTest(unittest.TestCase):
    def test_standard_strategy_asks_for_missing_work_contract_facts(self):
        strategy = QuestionStrategy.standard()
        session = ContractSession.start(
            intent="I want to build a tool that helps AI users work more efficiently.",
            strategy=strategy,
        )

        questions = session.next_questions()

        self.assertLessEqual(len(questions), strategy.question_budget)
        self.assertTrue(any("goal" in question.field for question in questions))
        self.assertTrue(any("outputs" in question.field for question in questions))
        self.assertTrue(any("acceptance" in question.field for question in questions))
        self.assertTrue(any("risks" in question.field for question in questions))

    def test_contract_ids_do_not_collide_for_repeated_intent(self):
        strategy = QuestionStrategy.quick()
        first = ContractSession.start("Repeatable intent.", strategy)
        second = ContractSession.start("Repeatable intent.", strategy)
        first.answer(goal="Create a plan.", outputs="Plan.", acceptance_criteria="Plan is useful.")
        second.answer(goal="Create a plan.", outputs="Plan.", acceptance_criteria="Plan is useful.")

        first_contract = WorkContractBuilder().build(first)
        second_contract = WorkContractBuilder().build(second)

        self.assertNotEqual(first_contract.id, second_contract.id)

    def test_builder_creates_ready_contract_with_explainable_completeness_score(self):
        strategy = QuestionStrategy.standard()
        session = ContractSession.start(
            intent="I want Argus to turn vague AI work requests into executable contracts.",
            strategy=strategy,
        )
        session.answer(
            goal="Validate a local-first work contract MVP for Argus.",
            context="Argus is entering Phase 1 after design planning.",
            inputs="Existing DESIGN.md, roadmap, PRD, and technical design.",
            outputs="A CLI-generated work contract and a phase plan deliverable.",
            constraints="No plugins, no app, no automatic capability installation.",
            risks="The MVP may over-ask questions or produce vague acceptance criteria.",
            acceptance_criteria="A contract includes goal, context, inputs, outputs, constraints, risks, and acceptance criteria.",
        )

        contract = WorkContractBuilder().build(session)

        self.assertEqual(contract.status, "ready")
        self.assertEqual(contract.version, 1)
        self.assertGreaterEqual(contract.completeness_score.overall_score, 0.85)
        self.assertEqual(contract.completeness_score.missing_fields, [])
        self.assertIn("ready", contract.completeness_score.rationale.lower())

    def test_deliverable_evaluator_flags_missing_acceptance_section(self):
        strategy = QuestionStrategy.standard()
        session = ContractSession.start(
            intent="Create a PRD for Argus Phase 1.",
            strategy=strategy,
        )
        session.answer(
            goal="Define Phase 1 MVP scope.",
            context="Argus needs to start implementation.",
            inputs="Roadmap and technical design.",
            outputs="PRD document.",
            constraints="Local CLI only.",
            risks="Scope creep.",
            acceptance_criteria="The PRD must include measurable success criteria.",
        )
        contract = WorkContractBuilder().build(session)
        deliverable_contract = DeliverableContract.prd()

        result = DeliverableEvaluator().evaluate(
            contract=contract,
            deliverable_contract=deliverable_contract,
            text="# PRD\n\n## Background\nArgus Phase 1.\n\n## Goals\nBuild CLI.",
        )

        self.assertEqual(result.status, "partial")
        self.assertIn("Success Criteria", result.missing_items)
        self.assertIn("Acceptance Criteria", result.missing_items)

    def test_storage_round_trips_contract_and_evaluation(self):
        strategy = QuestionStrategy.quick()
        session = ContractSession.start(
            intent="Plan a small research task.",
            strategy=strategy,
        )
        session.answer(
            goal="Create a research plan.",
            outputs="Research plan.",
            acceptance_criteria="Plan has questions, sources, and deliverables.",
        )
        contract = WorkContractBuilder().build(session)
        evaluation = DeliverableEvaluator().evaluate(
            contract=contract,
            deliverable_contract=DeliverableContract.research_plan(),
            text="# Research Plan\n\n## Questions\nWhat matters?\n\n## Sources\nDocs.\n\n## Deliverables\nSummary.",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ContractStorage(f"{tmpdir}/.argus")
            storage.save_contract(contract)
            storage.save_evaluation(contract.id, evaluation)

            loaded = storage.load_contract(contract.id)
            evaluations = storage.list_evaluations(contract.id)
            contract_markdown_exists = storage.contract_markdown_path(contract.id).exists()
            evidence = storage.list_evidence(contract.id)

        self.assertEqual(loaded.id, contract.id)
        self.assertEqual(loaded.intent, contract.intent)
        self.assertEqual(evaluations[0].status, "pass")
        self.assertTrue(contract_markdown_exists)
        self.assertEqual(evidence[0]["event_type"], "deliverable_evaluated")

    def test_renderer_outputs_prd_that_passes_prd_evaluation(self):
        strategy = QuestionStrategy.quick()
        session = ContractSession.start(
            intent="Create a PRD for a local work contract CLI.",
            strategy=strategy,
        )
        session.answer(
            goal="Define the local CLI MVP.",
            outputs="PRD.",
            acceptance_criteria="The PRD has all required sections.",
        )
        contract = WorkContractBuilder().build(session)
        deliverable_contract = DeliverableContract.prd()

        rendered = DeliverableRenderer().render(contract, deliverable_contract)
        evaluation = DeliverableEvaluator().evaluate(contract, deliverable_contract, rendered)

        self.assertIn("## Acceptance Criteria", rendered)
        self.assertEqual(evaluation.status, "pass")


if __name__ == "__main__":
    unittest.main()
