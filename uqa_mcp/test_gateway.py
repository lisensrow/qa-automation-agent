"""Mock-only checks; must not contact any U-Connect environment."""
import json
import unittest

import httpx

from uqa_mcp.gateway import ReadOnlyGateway, GatewayConfigurationError


def client_with(handler):
    return httpx.Client(
        base_url="https://uc.lab.local",
        transport=httpx.MockTransport(handler),
        trust_env=False,
        follow_redirects=False,
    )


class GatewayTests(unittest.TestCase):
    def test_exact_route_and_redaction(self):
        seen = []
        def handler(request):
            seen.append((request.method, request.url.path, request.url.query.decode()))
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"items": [{"id":"abc", "name":"test", "password":"LEAK",
                                  "access_token":"SECRET", "active":True}],
                      "total":1},
            )
        with client_with(handler) as client:
            gateway = ReadOnlyGateway("https://uc.lab.local", "/api/v1", client=client)
            result = gateway.list_resources("collections", limit=5)
        self.assertEqual(result["observation_status"], "observed")
        self.assertEqual(seen, [("GET", "/api/v1/ci-collection", "limit=5&offset=0")])
        self.assertEqual(result["items"], [{"id":"abc","name":"test","active":True}])
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertFalse(result["business_pass"])

    def test_unknown_tool_fails_before_network(self):
        with client_with(lambda _: self.fail("network reached")) as client:
            gateway = ReadOnlyGateway("https://uc.lab.local", "/api/v1", client=client)
            result = gateway.list_resources("delete_everything")
        self.assertEqual(result["reason"], "unregistered_business_operation")

    def test_bad_pagination_fails_before_network(self):
        with client_with(lambda _: self.fail("network reached")) as client:
            gateway = ReadOnlyGateway("https://uc.lab.local", "/api/v1", client=client)
            self.assertEqual(gateway.list_resources("collections", limit=True)["reason"],
                             "invalid_pagination")
            self.assertEqual(gateway.list_resources("policies", offset=-1)["reason"],
                             "invalid_pagination")

    def test_bad_operator_origin(self):
        for origin in ["http://uc.lab.local", "https://a.example/path",
                       "https://user:pass@uc.lab.local", "https://uc.lab.local?x=1"]:
            with self.subTest(origin=origin):
                with self.assertRaises(GatewayConfigurationError):
                    ReadOnlyGateway(origin, "/api/v1")

    def test_not_json_is_not_observed(self):
        with client_with(lambda _: httpx.Response(200, headers={"content-type":"text/html"},
                                                  text="<html/>")) as client:
            gateway = ReadOnlyGateway("https://uc.lab.local", "/api/v1", client=client)
            result = gateway.list_resources("procedures")
        self.assertEqual(result["reason"], "api_non_json_response")

    def test_http_errors_are_not_pass(self):
        with client_with(lambda _: httpx.Response(403)) as client:
            gateway = ReadOnlyGateway("https://uc.lab.local", "/api/v1", client=client)
            result = gateway.list_resources("policies")
        self.assertEqual(result["reason"], "api_authorization_failed")
        self.assertEqual(result["http_status"], 403)
        self.assertFalse(result["business_pass"])

    def test_redirect_refused(self):
        with client_with(lambda _: httpx.Response(302, headers={"location":"https://other.test/"})) as client:
            gateway = ReadOnlyGateway("https://uc.lab.local", "/api/v1", client=client)
            result = gateway.list_resources("collections")
        self.assertEqual(result["reason"], "api_redirect_refused")

    def test_response_budget(self):
        with client_with(lambda _: httpx.Response(200, headers={"content-type":"application/json"},
                                                  content=b" " * (256*1024+1))) as client:
            gateway = ReadOnlyGateway("https://uc.lab.local", "/api/v1", client=client)
            result = gateway.list_resources("collections")
        self.assertEqual(result["reason"], "api_response_too_large")


if __name__ == "__main__":
    unittest.main()
