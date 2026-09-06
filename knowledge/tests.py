from unittest.mock import patch

from rest_framework.test import APITestCase

from .models import Chunk, Document

CONTENT_PLAN = {
    'queries': [
        {
            'sql': (
                "SELECT content FROM knowledge_chunk "
                "WHERE content ILIKE '%founded%' LIMIT 10;"
            ),
            'rationale': 'The founding date is a fact inside the document content.',
        }
    ]
}

METADATA_PLAN = {
    'queries': [
        {
            'sql': 'SELECT created_at FROM knowledge_document LIMIT 1;',
            'rationale': 'The question asks about the document row itself.',
        }
    ]
}


class AskViewRetrievalTests(APITestCase):
    def setUp(self):
        self.document = Document.objects.create(title='novadesk_overview.pdf', source='test')
        Chunk.objects.create(
            document=self.document,
            content='NovaDesk Technologies is a fictional software company founded in 2019.',
            order=0,
        )

    def test_content_question_returns_chunk_content_not_row_metadata(self):
        """Regression test: filtering on content must surface the content as evidence,
        not knowledge_document.created_at (the original reported bug)."""
        synthesis_answer = {
            'answer': 'NovaDesk Technologies was founded in 2019.',
            'citations': ['e0'],
        }

        with patch(
            'llm.client.OpenRouterClient.chat_json',
            side_effect=[CONTENT_PLAN, synthesis_answer],
        ):
            response = self.client.post(
                '/api/ask/', {'question': 'When was NovaDesk Technologies founded?'}, format='json'
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['answer'], 'NovaDesk Technologies was founded in 2019.')
        self.assertTrue(data['evidence'], 'expected at least one evidence row')
        self.assertIn('founded in 2019', data['evidence'][0]['text'])
        self.assertIn('content', data['evidence'][0]['row'])
        self.assertNotIn('created_at', data['evidence'][0]['row'])

    def test_metadata_question_uses_document_created_at(self):
        """When the question is explicitly about the document row, metadata retrieval
        must still work."""
        synthesis_answer = {
            'answer': f'The document was created at {self.document.created_at.isoformat()}.',
            'citations': ['e0'],
        }

        with patch(
            'llm.client.OpenRouterClient.chat_json',
            side_effect=[METADATA_PLAN, synthesis_answer],
        ):
            response = self.client.post(
                '/api/ask/', {'question': 'When was the knowledge document created?'}, format='json'
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('created_at', data['evidence'][0]['row'])
