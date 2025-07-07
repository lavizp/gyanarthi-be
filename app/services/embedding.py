from openai import OpenAI

from app.config import settings

class OpenAIEmbedder:
    def __init__(self,  model: str = "text-embedding-3-small"):
        api_key = settings.OPENAI_KEY
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def get_embedding(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
