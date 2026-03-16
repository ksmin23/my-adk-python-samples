#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import logging
import asyncio
from typing import List, Union, Dict, Optional
import numpy as np
from google.genai import types
from google.genai import Client

logger = logging.getLogger(__name__)

async def gemini_complete(
  prompt: str,
  system_prompt: Optional[str] = None,
  history_messages: List[Dict[str, str]] = [],
  keyword_extraction: bool = False,
  **kwargs,
) -> str:
  """
  Wrapper for Gemini completion to match PathRAG's llm_model_func interface.
  """
  try:
    # Extract model name from kwargs or env, default to gemini-2.5-flash
    # PathRAG passes hashing_kv request which contains global_config with llm_model_name
    model_name = "gemini-2.5-flash"
    if "hashing_kv" in kwargs and hasattr(kwargs["hashing_kv"], "global_config"):
       model_name = kwargs["hashing_kv"].global_config.get("llm_model_name", "gemini-2.5-flash")
    
    # Initialize Vertex AI Client (ADK style or direct)
    # Assuming environment variables GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are set
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    
    client = Client(vertexai=True, project=project, location=location)

    # Construct contents
    contents = []
    
    # Add history
    for msg in history_messages:
      role = msg.get("role")
      content = msg.get("content")
      if role == "user":
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
      elif role == "assistant":
        contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
      # System prompt is handled separately in config for Gemini 1.5/2.0
      
    # Add current prompt
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

    # Config
    config = types.GenerateContentConfig(
      system_instruction=system_prompt if system_prompt else None,
      temperature=kwargs.get("temperature", 0.0),
      max_output_tokens=kwargs.get("max_tokens", 8192),
    )

    if keyword_extraction:
      # PathRAG expects JSON for keyword extraction
      config.response_mime_type = "application/json"

    # Generate
    def _generate():
      response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config,
      )
      return response.text

    response_text = await asyncio.to_thread(_generate)
    
    return response_text

  except Exception as e:
    logger.error(f"Gemini completion failed: {e}")
    raise e


async def gemini_embedding(
  texts: List[str],
  model: str = "text-embedding-004",
  **kwargs,
) -> np.ndarray:
  """
  Wrapper for Gemini embedding to match PathRAG's embedding_func interface.
  """
  try:
    # Initialize Client
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    client = Client(vertexai=True, project=project, location=location)
    
    def _embed():
      response = client.models.embed_content(
        model=model,
        contents=texts,
      )
      return [e.values for e in response.embeddings]

    embeddings = await asyncio.to_thread(_embed)
    return np.array(embeddings)

  except Exception as e:
    logger.error(f"Gemini embedding failed: {e}")
    raise e
