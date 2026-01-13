"""
title: High-Fidelity PDF Loader (PyMuPDF4LLM)
author: Gemini
version: 1.2
description: Extracts clean Markdown text and detailed metadata from PDFs.
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field
import os

# Recommended: pip install pymupdf4llm langchain-openai
from langchain_community.document_loaders import PyMuPDF4LLMLoader
from langchain_openai import ChatOpenAI


class Pipeline:
    class Valves(BaseModel):
        OPENAI_API_BASE: str = Field(default="http://host.docker.internal:11434/v1")
        OPENAI_API_KEY: str = Field(default="ollama")
        MODEL_NAME: str = Field(default="llama3.2")

    def __init__(self):
        self.type = "pipe"
        self.id = "pymupdf_metadata_pipe"
        self.name = "PDF Expert (Markdown + Meta)"
        self.valves = self.Valves()

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        messages = body.get("messages", [])
        user_message = messages[-1].get("content", "")
        files = body.get("files", [])

        context_data = ""

        if files:
            for file in files:
                file_path = file.get("path")
                if file_path and file_path.lower().endswith(".pdf"):
                    try:
                        # PyMuPDF4LLM is the gold standard for LLM-ready text
                        loader = PyMuPDF4LLMLoader(file_path)
                        docs = loader.load()

                        # Extract Document-Wide Metadata
                        meta = docs[0].metadata
                        context_data += "\n--- DOCUMENT PROPERTIES ---\n"
                        context_data += f"Title: {meta.get('title', 'N/A')}\n"
                        context_data += f"Author: {meta.get('author', 'N/A')}\n"
                        context_data += f"Pages: {meta.get('total_pages', len(docs))}\n"
                        context_data += f"Creator: {meta.get('creator', 'N/A')}\n"
                        context_data += "---------------------------\n\n"

                        # Combine Markdown Content
                        full_text = "\n".join([doc.page_content for doc in docs])
                        context_data += (
                            f"--- CONTENT ---\n{full_text}\n--------------\n"
                        )

                    except Exception as e:
                        context_data += f"\n[Error: {str(e)}]\n"

        # Construct final prompt with clear separation
        system_instruction = "You are an assistant analyzing a PDF. Use the metadata and content provided below to answer."
        final_prompt = (
            f"{system_instruction}\n\n{context_data}\n\nUser Question: {user_message}"
        )

        llm = ChatOpenAI(
            base_url=self.valves.OPENAI_API_BASE,
            api_key=self.valves.OPENAI_API_KEY,
            model=self.valves.MODEL_NAME,
        )

        return llm.predict(final_prompt)
