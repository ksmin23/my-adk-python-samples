#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag
from .prompt import instruction

load_dotenv()

# 1. Create the specialized RAG retrieval tool
ask_vertex_retrieval = VertexAiRagRetrieval(
  name='retrieve_rag_documentation',
  description=(
    'Use this tool to retrieve documentation and reference materials for the question from the RAG corpus,'
  ),
  rag_resources=[
    rag.RagResource(
      rag_corpus=os.environ.get("RAG_CORPUS")
    )
  ],
  similarity_top_k=10,
  vector_distance_threshold=0.6,
)

# 2. Create the Agent, providing the instruction and the retrieval tool
root_agent = Agent(
  model='gemini-2.5-flash',
  name='ask_rag_agent',
  instruction=instruction,
  tools=[
    ask_vertex_retrieval,
  ]
)