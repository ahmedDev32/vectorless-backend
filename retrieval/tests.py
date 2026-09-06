from unittest.mock import patch

from django.test import SimpleTestCase

from llm.schemas import SQLQuery, SQLQueryPlan
from retrieval.planner import QueryPlanner, flag_metadata_confusion


class FlagMetadataConfusionTests(SimpleTestCase):
    def test_flags_content_filter_without_content_select(self):
        query = SQLQuery(
            sql=(
                "SELECT k.created_at FROM knowledge_document k "
                "JOIN knowledge_chunk kc ON k.id = kc.document_id "
                "WHERE kc.content ILIKE '%founded%' LIMIT 1;"
            )
        )
        issue = flag_metadata_confusion(query)
        self.assertIsNotNone(issue)
        self.assertIn('content', issue)

    def test_allows_content_filter_with_content_selected(self):
        query = SQLQuery(
            sql=(
                "SELECT kc.content FROM knowledge_chunk kc "
                "WHERE kc.content ILIKE '%founded%' LIMIT 10;"
            )
        )
        self.assertIsNone(flag_metadata_confusion(query))

    def test_allows_select_star(self):
        query = SQLQuery(sql="SELECT * FROM knowledge_chunk WHERE content ILIKE '%founded%' LIMIT 10;")
        self.assertIsNone(flag_metadata_confusion(query))

    def test_allows_pure_metadata_query(self):
        query = SQLQuery(sql='SELECT created_at FROM knowledge_document LIMIT 1;')
        self.assertIsNone(flag_metadata_confusion(query))


class QueryPlannerSelfCorrectionTests(SimpleTestCase):
    def test_corrects_metadata_only_plan(self):
        bad_plan = {
            'queries': [
                {
                    'sql': (
                        "SELECT k.created_at FROM knowledge_document k "
                        "JOIN knowledge_chunk kc ON k.id = kc.document_id "
                        "WHERE kc.content ILIKE '%founded%' LIMIT 1;"
                    ),
                    'rationale': 'find founding date',
                }
            ]
        }
        good_plan = {
            'queries': [
                {
                    'sql': (
                        "SELECT kc.content FROM knowledge_chunk kc "
                        "WHERE kc.content ILIKE '%founded%' LIMIT 10;"
                    ),
                    'rationale': 'find founding date in content',
                }
            ]
        }

        with patch(
            'retrieval.planner.OpenRouterClient.chat_json',
            side_effect=[bad_plan, good_plan],
        ) as mock_chat:
            planner = QueryPlanner()
            plan = planner.plan('When was NovaDesk Technologies founded?')

        self.assertEqual(mock_chat.call_count, 2)
        self.assertIsNone(flag_metadata_confusion(plan.queries[0]))
        self.assertIn('content', plan.queries[0].sql.lower())

    def test_no_correction_when_plan_is_already_correct(self):
        good_plan = {
            'queries': [
                {
                    'sql': "SELECT content FROM knowledge_chunk WHERE content ILIKE '%founded%' LIMIT 10;",
                    'rationale': 'find founding date in content',
                }
            ]
        }

        with patch('retrieval.planner.OpenRouterClient.chat_json', return_value=good_plan) as mock_chat:
            planner = QueryPlanner()
            plan = planner.plan('When was NovaDesk Technologies founded?')

        self.assertEqual(mock_chat.call_count, 1)
        self.assertIsInstance(plan, SQLQueryPlan)
