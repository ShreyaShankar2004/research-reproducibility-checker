import os

from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel
from deepeval.models import DeepEvalBaseLLM


class GroqJudge(DeepEvalBaseLLM):
    def __init__(self, model_name="openai/gpt-oss-20b"):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY was not found in the environment.")

        self.model_name = model_name
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=60.0,
        )
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=60.0,
        )

    def load_model(self):
        return self.client

    def get_model_name(self):
        return f"Groq {self.model_name}"

    def generate(self, prompt: str, schema: BaseModel = None):
        kwargs = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }

        if schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__.lower(),
                    "strict": False,
                    "schema": schema.model_json_schema(),
                },
            }

        response = self.client.chat.completions.create(**kwargs)
        output = response.choices[0].message.content

        if not output:
            raise ValueError("Groq returned an empty response.")

        if schema is not None:
            return schema.model_validate_json(output)

        return output

    async def a_generate(self, prompt: str, schema: BaseModel = None):
        kwargs = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }

        if schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__.lower(),
                    "strict": False,
                    "schema": schema.model_json_schema(),
                },
            }

        response = await self.async_client.chat.completions.create(**kwargs)
        output = response.choices[0].message.content

        if not output:
            raise ValueError("Groq returned an empty response.")

        if schema is not None:
            return schema.model_validate_json(output)

        return output