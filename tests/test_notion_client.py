import httpx

from knowledge_architect.connectors.notion.client import NotionClient


def test_search_paginates() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, json={"results": [{"id": "1"}], "has_more": True, "next_cursor": "c"})
        return httpx.Response(200, json={"results": [{"id": "2"}], "has_more": False})

    client = NotionClient("token", base_url="https://test.local/v1")
    client._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://test.local/v1")
    try:
        assert [item["id"] for item in client.search()] == ["1", "2"]
    finally:
        client.close()
