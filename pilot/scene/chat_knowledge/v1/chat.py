from chromadb.errors import NoIndexException

from pilot.scene.base_chat import BaseChat
from pilot.scene.base import ChatScene
from pilot.configs.config import Config

from pilot.configs.model_config import (
    KNOWLEDGE_UPLOAD_ROOT_PATH,
    EMBEDDING_MODEL_CONFIG,
)

from pilot.scene.chat_knowledge.v1.prompt import prompt
from pilot.server.knowledge.service import KnowledgeService

CFG = Config()


class ChatKnowledge(BaseChat):
    chat_scene: str = ChatScene.ChatKnowledge.value()

    """Number of results to return from the query"""

    def __init__(self, chat_session_id, user_input, select_param: str = None):
        """ """
        from pilot.embedding_engine.embedding_engine import EmbeddingEngine

        self.knowledge_space = select_param
        super().__init__(
            chat_mode=ChatScene.ChatKnowledge,
            chat_session_id=chat_session_id,
            current_user_input=user_input,
        )
        self.space_context = self.get_space_context(self.knowledge_space)
        self.top_k = (
            CFG.KNOWLEDGE_SEARCH_TOP_SIZE
            if self.space_context is None
            else int(self.space_context["embedding"]["topk"])
        )
        # self.recall_score = CFG.KNOWLEDGE_SEARCH_TOP_SIZE if self.space_context is None else self.space_context["embedding"]["recall_score"]
        self.max_token = (
            CFG.KNOWLEDGE_SEARCH_MAX_TOKEN
            if self.space_context is None
            else int(self.space_context["prompt"]["max_token"])
        )
        vector_store_config = {
            "vector_store_name": self.knowledge_space,
            "vector_store_type": CFG.VECTOR_STORE_TYPE,
            "chroma_persist_path": KNOWLEDGE_UPLOAD_ROOT_PATH,
        }
        self.knowledge_embedding_client = EmbeddingEngine(
            model_name=EMBEDDING_MODEL_CONFIG[CFG.EMBEDDING_MODEL],
            vector_store_config=vector_store_config,
        )

    def generate_input_values(self):
        try:
            if self.space_context:
                self.prompt_template.template_define = self.space_context["prompt"][
                    "scene"
                ]
                self.prompt_template.template = self.space_context["prompt"]["template"]
            docs = self.knowledge_embedding_client.similar_search(
                self.current_user_input, self.top_k
            )
            context = [d.page_content for d in docs]
            context = context[: self.max_token]
            input_values = {"context": context, "question": self.current_user_input}
        except NoIndexException:
            raise ValueError(
                "you have no knowledge space, please add your knowledge space"
            )
        return input_values

    @property
    def chat_type(self) -> str:
        return ChatScene.ChatKnowledge.value()

    def get_space_context(self, space_name):
        service = KnowledgeService()
        return service.get_space_context(space_name)
