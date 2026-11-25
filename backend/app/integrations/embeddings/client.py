"""Text embeddings through any OpenAI-compatible /embeddings endpoint (Gemini by default).

Two entry points, because some models embed questions and documents differently:
`embed_documents` (chunks at ingest time) and `embed_query` (the user's question).
"""

import logging
import math

import openai
from openai import AsyncOpenAI

from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


class EmbeddingUnavailableError(ServiceUnavailableError):
    code = "embeddings_unavailable"
    default_message = "Document search is temporarily unavailable. Please try again later."


class EmbeddingClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        dim: int,
        *,
        batch_size: int = 32,
        timeout: float = 30.0,
    ) -> None:
        self._client = AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=2
        )
        self.model = model
        self.dim = dim
        self.batch_size = batch_size
        # e5 models were trained with these prefixes; without them retrieval gets much worse.
        self._is_e5 = "e5" in model.lower()
        self._send_dimensions = True

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefix = "passage: " if self._is_e5 else ""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = [prefix + text for text in texts[start : start + self.batch_size]]
            vectors.extend(await self._embed(batch))
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        prefix = "query: " if self._is_e5 else ""
        return (await self._embed([prefix + text]))[0]

    async def _embed(self, inputs: list[str]) -> list[list[float]]:
        try:
            response = await self._create(inputs)
        except openai.APIError as exc:
            logger.warning("Embedding call failed: %s: %s", type(exc).__name__, exc)
            raise EmbeddingUnavailableError() from exc

        data = sorted(response.data, key=lambda item: item.index)
        if len(data) != len(inputs):
            raise EmbeddingUnavailableError()
        return [self._fit(list(item.embedding)) for item in data]

    async def _create(self, inputs: list[str]):  # type: ignore[no-untyped-def]
        if self._send_dimensions and not self._is_e5:
            try:
                # Ask for exactly `dim` numbers (Matryoshka models such as gemini-embedding-001
                # support this). Some endpoints reject the parameter; then fall back once.
                return await self._client.embeddings.create(
                    model=self.model, input=inputs, dimensions=self.dim
                )
            except openai.BadRequestError as exc:
                if "dimension" not in str(exc).lower():
                    raise  # e.g. an invalid API key (Gemini answers those with 400 too)
                logger.info("Endpoint rejected `dimensions` (%s); truncating locally", exc)
                self._send_dimensions = False
        return await self._client.embeddings.create(model=self.model, input=inputs)

    def _fit(self, vector: list[float]) -> list[float]:
        """Make the vector exactly `dim` long and unit length."""
        if len(vector) < self.dim:
            raise RuntimeError(
                f"{self.model} returned {len(vector)} dimensions but EMBEDDING_DIM={self.dim}"
            )
        vector = vector[: self.dim]
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]
