import unittest
from unittest.mock import Mock, patch

from src.extractors.base_client import BaseClient, APIError


class BaseClientTests(unittest.TestCase):
    def test_client_init_headers(self):
        client = BaseClient(base_url="https://api.cvat.ai", token="test-token", auth_prefix="Token", org="vinai")
        self.assertEqual(client.session.headers.get("Authorization"), "Token test-token")
        self.assertEqual(client.session.headers.get("X-Organization"), "vinai")

    def test_unsafe_redirect_rejected(self):
        client = BaseClient(base_url="https://api.cvat.ai", token="test-token")
        with self.assertRaises(ValueError):
            client.get("https://malicious.site/api/jobs")

    def test_cvat_pagination(self):
        client = BaseClient(base_url="https://api.cvat.ai", token="test-token")
        with patch.object(client, "get") as mock_get:
            res1 = Mock()
            res1.json.return_value = {"results": [{"id": 1}], "next": "api/jobs?page=2"}
            res2 = Mock()
            res2.json.return_value = {"results": [{"id": 2}], "next": None}
            mock_get.side_effect = [res1, res2]

            items = client.listing("api/jobs")
            self.assertEqual(len(items), 2)
            self.assertEqual([i["id"] for i in items], [1, 2])

    def test_downgrade_rejected_before_request(self):
        client=BaseClient('https://cvat.test',token='secret')
        with patch.object(client.session,'get') as request:
            with self.assertRaises(ValueError): client.get('http://cvat.test/api/jobs')
            request.assert_not_called()

    def test_base_rejects_credentials_and_query(self):
        for url in ('https://user:password@cvat.test','https://cvat.test?token=secret','file:///tmp'):
            with self.subTest(url=url), self.assertRaises(ValueError): BaseClient(url)

    def test_http_error_contains_status_without_body_or_query(self):
        client=BaseClient('https://cvat.test')
        with patch.object(client.session,'get',return_value=Mock(status_code=403,text='secret')):
            with self.assertRaises(APIError) as caught: client.get('api/jobs?token=secret')
        self.assertEqual(caught.exception.status_code,403)
        self.assertNotIn('secret',str(caught.exception))

    def test_org_not_duplicated_in_next_url(self):
        client=BaseClient('https://cvat.test',org='team')
        with patch.object(client.session,'get',return_value=Mock(status_code=200)) as request:
            client.get('api/jobs?org=team&page=2')
            self.assertNotIn('org',request.call_args.kwargs['params'])

    def test_query_relative_pagination(self):
        client=BaseClient('https://cvat.test')
        with patch.object(client,'get') as request:
            request.side_effect=[Mock(json=lambda:{'results':[{'id':1}],'next':'?page=2'}),Mock(json=lambda:{'results':[{'id':2}],'next':None})]
            self.assertEqual(len(client.listing('api/jobs',{'page':1})),2)
            self.assertEqual(request.call_args_list[1].args[0],'https://cvat.test/api/jobs?page=2')

    def test_pagination_repeated_query_stops(self):
        client=BaseClient('https://cvat.test')
        with patch.object(client,'get',return_value=Mock(json=lambda:{'results':[],'next':'https://cvat.test/api/jobs?page=1'})) as request:
            with self.assertRaisesRegex(ValueError,'loop'): client.listing('api/jobs',{'page':1})
            self.assertEqual(request.call_count,1)

    def test_pagination_rejects_bad_next_and_rows(self):
        for payload in ({'results':[None],'next':None},{'results':[],'next':42},{'results':[],'next':'https://evil.test/api/jobs'}):
            client=BaseClient('https://cvat.test')
            with patch.object(client,'get',return_value=Mock(json=lambda:payload)), self.assertRaises(ValueError):
                client.listing('api/jobs')

    def test_pagination_page_limit(self):
        client=BaseClient('https://cvat.test',max_pages=1)
        with patch.object(client,'get',return_value=Mock(json=lambda:{'results':[],'next':'?page=2'})):
            with self.assertRaisesRegex(ValueError,'max_pages'): client.listing('api/jobs')

    def test_retry_only_get_and_no_redirects(self):
        client=BaseClient('https://cvat.test')
        retries=client.session.get_adapter('https://').max_retries
        self.assertEqual(retries.total,3)
        self.assertEqual(retries.allowed_methods,['GET'])
        with patch.object(client.session,'get',return_value=Mock(status_code=200)) as request:
            client.get('api/tasks/1')
            self.assertFalse(request.call_args.kwargs['allow_redirects'])


if __name__ == "__main__":
    unittest.main()
