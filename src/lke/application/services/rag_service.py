"""Application service for Retrieval-Augmented Generation."""

from lke.config.models import RAGConfig
from lke.domain.exceptions import DomainError
from lke.domain.models.rag import RAGResponse
from lke.domain.protocols.ai_provider import AIProvider
from lke.application.services.search_service import SearchService


class RAGService:
    """Application service for performing RAG queries."""

    def __init__(
        self,
        search_service: SearchService,
        ai_provider: AIProvider,
        config: RAGConfig,
    ) -> None:
        """Initialize the RAG service.

        Args:
            search_service: Service to retrieve relevant documents.
            ai_provider: Provider to generate answers.
            config: Configuration for RAG.
        """
        self._search = search_service
        self._provider = ai_provider
        self._config = config

    def ask(self, query: str) -> RAGResponse:
        """Ask a question and get a synthesized answer based on the vault.

        Args:
            query: The user's natural language question.

        Returns:
            A RAGResponse containing the synthesized answer and the sources used.

        Raises:
            DomainError: If the query is empty.
        """
        if not query or not query.strip():
            raise DomainError("Query cannot be empty or whitespace.")

        # 1. Retrieve relevant contexts
        top_k = self._config.top_k
        sources = self._search.search(query, top_k=top_k)

        # 2. Check if we have context
        if not sources:
            return RAGResponse(
                answer="I don't know. I couldn't find any relevant information in the provided context.",
                sources=[]
            )

        # 3. Build the context string
        context_parts = []
        for i, hit in enumerate(sources, 1):
            source_id = f"Source [{i}]: {hit.metadata.get('title') or hit.document_id}"
            content = hit.content
            context_parts.append(f"--- {source_id} ---\n{content}")

        context_str = "\n\n".join(context_parts)

        # 3. Construct the prompt
        prompt = (
            f"Context:\n{context_str}\n\n"
            f"Question: {query}\n\n"
            f"Answer:"
        )

        # 4. Generate the answer
        try:
            answer = self._provider.generate_text(
                prompt=prompt,
                system_prompt=self._config.system_prompt
            )
        except Exception as e:
            raise DomainError(f"Failed to generate answer: {e}") from e

        return RAGResponse(
            answer=answer.strip(),
            sources=sources
        )
