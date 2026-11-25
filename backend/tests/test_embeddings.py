"""EmbeddingClient without network: dimensions fallback, truncation, e5 prefixes, errors."""

import math
from types import SimpleNamespace
from typing import Any

import httpx2
import openai
import pytest

from app.integrations.embeddings.client import EmbeddingClient, EmbeddingUnavailableError


class FakeEmbeddingsAPI:
    def __init__(
        self, size: int, reject_dimensions: bool = False, fail: bool = False, bad_key: bool = False
    ) -> None:
        self.bad_key = bad_key
        self.size = size
        self.reject_dimensions = reject_dimensions
        self.fail = fail
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(kwargs)
        request = httpx2.Request("POST", "http://test/embeddings")
        if self.fail:
            raise openai.APIConnectionError(request=request)
        if self.bad_key:
            raise openai.BadRequestError(
                "Please pass a valid API key",
                response=httpx2.Response(400, request=request),
                body=None,
            )
        if self.reject_dimensions and "dimensions" in kwargs:
            raise openai.BadRequestError(
                "Unknown parameter: dimensions",
                response=httpx2.Response(400, request=request),
                body=None,
            )
        size = kwargs.get("dimensions", self.size)
        data = [
            SimpleNamespace(index=i, embedding=[float(i + 1)] + [1.0] * (size - 1))
            for i in range(len(kwargs["input"]))
        ]
        return SimpleNamespace(data=list(reversed(data)))  # out of order on purpose


def client_with(api: FakeEmbeddingsAPI, model: str = "gemini-embedding-001", dim: int = 8):
    client = EmbeddingClient("http://test/v1", "key", model, dim, batch_size=3)
    client._client = SimpleNamespace(embeddings=api)  # type: ignore[assignment]
    return client


async def test_requests_exact_dimensions_and_batches() -> None:
    api = FakeEmbeddingsAPI(size=3072)
    client = client_with(api)
    vectors = await client.embed_documents(["a", "b", "c", "d", "e"])
    assert len(vectors) == 5 and all(len(v) == 8 for v in vectors)
    assert [len(r["input"]) for r in api.requests] == [3, 2]
    assert api.requests[0]["dimensions"] == 8
    # results come back in input order (first element grows with the index) and unit length
    assert vectors[0][0] < vectors[1][0] < vectors[2][0]
    assert math.isclose(sum(x * x for x in vectors[0]), 1.0)


async def test_falls_back_to_local_truncation() -> None:
    api = FakeEmbeddingsAPI(size=3072, reject_dimensions=True)
    client = client_with(api)
    vector = await client.embed_query("gas bill")
    assert len(vector) == 8 and math.isclose(sum(x * x for x in vector), 1.0)
    await client.embed_query("again")
    assert "dimensions" not in api.requests[-1]  # remembered, not retried every time


async def test_too_small_vectors_are_a_config_error() -> None:
    client = client_with(FakeEmbeddingsAPI(size=4, reject_dimensions=True), dim=8)
    with pytest.raises(RuntimeError, match="EMBEDDING_DIM"):
        await client.embed_query("x")


async def test_e5_models_get_prefixes_and_no_dimensions() -> None:
    api = FakeEmbeddingsAPI(size=8)
    client = client_with(api, model="intfloat/multilingual-e5-small")
    await client.embed_query("rent due date")
    await client.embed_documents(["Rent is due by the 7th."])
    assert api.requests[0]["input"] == ["query: rent due date"]
    assert api.requests[1]["input"] == ["passage: Rent is due by the 7th."]
    assert all("dimensions" not in r for r in api.requests)


async def test_provider_errors_become_503() -> None:
    client = client_with(FakeEmbeddingsAPI(size=8, fail=True))
    with pytest.raises(EmbeddingUnavailableError):
        await client.embed_query("x")


async def test_bad_key_does_not_disable_dimensions() -> None:
    api = FakeEmbeddingsAPI(size=8, bad_key=True)
    client = client_with(api)
    with pytest.raises(EmbeddingUnavailableError):
        await client.embed_query("x")
    assert len(api.requests) == 1 and client._send_dimensions
