"""RAG plumbing with a deterministic fake embedder (no network): chunking, ingest, search,
the search_knowledge tool and chat sources. Real-model threshold tuning is done by hand."""

import hashlib
import json
import math
import re
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.integrations.embeddings.dependencies import get_embedding_client
from app.integrations.llm.dependencies import get_llm_client
from app.integrations.llm.types import LLMReply, ToolCallRequest
from app.modules.knowledge.chunking import parse_markdown
from tests.conftest import MakeUser
from tests.test_chat import FakeLLM

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
STOPWORDS = {"the", "a", "an", "is", "of", "to", "and", "in", "do", "i", "my", "what", "how", "for"}


class FakeEmbeddings:
    """Hashed bag-of-words vectors: texts sharing words have a positive cosine similarity."""

    def __init__(self, model: str = "fake-bow", dim: int = 768) -> None:
        self.model = model
        self.dim = dim
        self.calls = 0

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in re.findall(r"\w+", text.lower()):
            if word in STOPWORDS:
                continue
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture
async def fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FakeEmbeddings]:
    from app.main import app

    fake = FakeEmbeddings()
    app.dependency_overrides[get_embedding_client] = lambda: fake
    # Bag-of-words scores are much lower than a real model's, so lower the cut-off.
    monkeypatch.setattr(get_settings(), "RAG_MIN_SCORE", 0.2)
    yield fake
    app.dependency_overrides.pop(get_embedding_client, None)


@pytest.fixture
async def ingested(fake_embeddings: FakeEmbeddings) -> FakeEmbeddings:
    from app.core.database import SessionLocal
    from app.modules.knowledge.dependencies import build_knowledge_service

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        async with SessionLocal() as session:
            service = build_knowledge_service(session, fake_embeddings)  # type: ignore[arg-type]
            await service.ingest(f"knowledge/{path.name}", path.read_text(), path.stem)
    return fake_embeddings


# ---- chunking -------------------------------------------------------------------------


def test_chunks_keep_heading_and_size_limit() -> None:
    long_section = " ".join(f"Sentence number {i} about the generator." for i in range(80))
    doc = parse_markdown(f"# Guide\n\nIntro text.\n\n## Generator\n\n{long_section}\n", "fallback")
    assert doc.title == "Guide"
    assert doc.chunks[0] == "Guide\nIntro text."
    generator_chunks = doc.chunks[1:]
    assert len(generator_chunks) > 1
    assert all(c.startswith("Guide — Generator\n") for c in generator_chunks)
    assert all(len(c) <= 800 for c in doc.chunks)
    # consecutive pieces overlap a little, so a fact cut at the boundary is not lost
    first_tail = generator_chunks[0].split("\n", 1)[1][-60:].split(".")[-2]
    assert first_tail.strip() in generator_chunks[1]


def test_title_falls_back_to_file_name() -> None:
    assert parse_markdown("## Only a section\n\nText here.", "My File").title == "My File"


def test_every_knowledge_file_has_a_title_and_chunks() -> None:
    files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    assert len(files) == 6
    for path in files:
        doc = parse_markdown(path.read_text(), path.stem)
        assert doc.title != path.stem and len(doc.chunks) >= 5


# ---- ingest + search ------------------------------------------------------------------


async def test_ingest_is_idempotent(fake_embeddings: FakeEmbeddings) -> None:
    from app.core.database import SessionLocal
    from app.modules.knowledge.dependencies import build_knowledge_service
    from app.modules.knowledge.services import IngestOutcome

    path = KNOWLEDGE_DIR / "house-rules.md"

    async def run(embedder: FakeEmbeddings, text: str | None = None, force: bool = False):  # type: ignore[no-untyped-def]
        async with SessionLocal() as session:
            service = build_knowledge_service(session, embedder)  # type: ignore[arg-type]
            return await service.ingest(
                "knowledge/house-rules.md", text or path.read_text(), "x", force=force
            )

    first = await run(fake_embeddings)
    assert first.outcome in (IngestOutcome.CREATED, IngestOutcome.UPDATED) and first.chunks > 0
    assert (await run(fake_embeddings)).outcome == IngestOutcome.SKIPPED
    assert (await run(fake_embeddings, force=True)).outcome == IngestOutcome.UPDATED
    # edited file -> re-embedded
    edited = path.read_text() + "\n## Laundry\n\nThe washing area is on the roof.\n"
    assert (await run(fake_embeddings, edited)).chunks == first.chunks + 1
    # a different embedding model must re-embed even unchanged text
    assert (await run(FakeEmbeddings(model="other-model"), edited)).outcome == IngestOutcome.UPDATED
    await run(fake_embeddings, force=True)  # restore for the other tests


async def test_search_finds_relevant_chunk_and_ignores_off_topic(
    client: AsyncClient, make_user: MakeUser, ingested: FakeEmbeddings
) -> None:
    tenant = await make_user("tenant")
    res = await client.post(
        "/knowledge/search", json={"query": "Titas gas bill service charge"}, headers=tenant.headers
    )
    assert res.status_code == 200, res.text
    hits = res.json()
    assert hits and all("Titas" in h["content"] for h in hits[:2])
    assert any(h["title"].startswith("Utilities Guide") for h in hits)
    assert hits == sorted(hits, key=lambda h: h["score"], reverse=True)

    res = await client.post(
        "/knowledge/search",
        json={"query": "who won yesterday's cricket match"},
        headers=tenant.headers,
    )
    assert res.json() == []


async def test_min_score_override_is_admin_only(
    client: AsyncClient, make_user: MakeUser, ingested: FakeEmbeddings
) -> None:
    body = {"query": "cricket world cup", "min_score": 0.0, "top_k": 3}
    tenant = await make_user("tenant")
    admin = await make_user("admin")
    assert (await client.post("/knowledge/search", json=body, headers=tenant.headers)).json() == []
    admin_hits = (await client.post("/knowledge/search", json=body, headers=admin.headers)).json()
    assert len(admin_hits) == 3  # every score is visible for tuning


async def test_documents_list_is_admin_only(
    client: AsyncClient, make_user: MakeUser, ingested: FakeEmbeddings
) -> None:
    staff = await make_user("staff")
    admin = await make_user("admin")
    assert (await client.get("/knowledge/documents", headers=staff.headers)).status_code == 403
    docs = (await client.get("/knowledge/documents", headers=admin.headers)).json()
    assert len(docs) == 6
    assert all(d["chunk_count"] > 0 and d["source_path"].startswith("knowledge/") for d in docs)


# ---- chat + RAG -----------------------------------------------------------------------


def search_call(query: str) -> LLMReply:
    args = {"query": query}
    return LLMReply(
        content="",
        tool_calls=[
            ToolCallRequest(
                id="call_k", name="search_knowledge", arguments=args, raw_arguments=json.dumps(args)
            )
        ],
    )


@pytest.fixture
async def fake_llm() -> AsyncIterator[FakeLLM]:
    from app.main import app

    fake = FakeLLM([])
    app.dependency_overrides[get_llm_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_client, None)


async def test_chat_answers_from_documents_with_sources(
    client: AsyncClient, make_user: MakeUser, ingested: FakeEmbeddings, fake_llm: FakeLLM
) -> None:
    tenant = await make_user("tenant")
    fake_llm.replies = [
        search_call("Titas gas bill service charge"),
        LLMReply(content="The gas bill is included in your service charge."),
    ]
    res = await client.post(
        "/chat", json={"message": "Do I pay the gas bill?"}, headers=tenant.headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool_calls"][0]["name"] == "search_knowledge"
    titles = [source["title"] for source in body["sources"]]
    assert any(t.startswith("Utilities Guide") for t in titles)
    assert len(body["sources"][0]["snippet"]) <= 151
    # the tool result the model saw contains the document text
    tool_result = json.loads(fake_llm.calls[1][0][-1]["content"])
    assert any("Titas" in r["content"] for r in tool_result["results"])
    # the system prompt tells the model to always search for policy questions
    assert "ALWAYS call search_knowledge" in fake_llm.calls[0][0][0]["content"]


async def test_chat_off_topic_gets_empty_sources(
    client: AsyncClient, make_user: MakeUser, ingested: FakeEmbeddings, fake_llm: FakeLLM
) -> None:
    tenant = await make_user("tenant")
    fake_llm.replies = [
        search_call("cricket match result"),
        LLMReply(content="I couldn't find that in the building's documents."),
    ]
    res = await client.post(
        "/chat", json={"message": "Who won the cricket?"}, headers=tenant.headers
    )
    body = res.json()
    assert body["sources"] == []
    tool_result = json.loads(fake_llm.calls[1][0][-1]["content"])
    assert tool_result == {"results": [], "note": "nothing relevant found"}
