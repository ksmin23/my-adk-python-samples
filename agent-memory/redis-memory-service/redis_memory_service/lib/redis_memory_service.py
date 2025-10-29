#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from __future__ import annotations

"""A memory service that uses Redis for storage and retrieval."""

import datetime
from typing import TYPE_CHECKING

from google.genai import types
from langchain_redis.vectorstores import RedisVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from redisvl.query.filter import Tag
from typing_extensions import override

from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry

if TYPE_CHECKING:
  from google.adk.events.event import Event
  from google.adk.sessions.session import Session


class RedisMemoryService(BaseMemoryService):
  """A memory service that uses Redis for storage and retrieval."""

  def __init__(
      self,
      uri: str,
      index_name: str = "adk_app_memory",
      embedding_model_name: str = "gemini-embedding-001",
      similarity_top_k: int = 10,
      ttl: int = 3600
  ):
    """Initializes a RedisMemoryService.

    Args:
        uri: The URL for the Redis instance.
        index_name: The name of the Redis search index.
        embedding_model_name: The name of the embedding model to use.
        similarity_top_k: The number of contexts to retrieve.
    """
    self._redis_url = uri
    self._index_name = index_name
    self._embeddings = VertexAIEmbeddings(model_name=embedding_model_name)
    self._similarity_top_k = similarity_top_k
    self._ttl = ttl
    self._metadata_schema = [
      {"name": "app_name", "type": "tag"},
      {"name": "user_id", "type": "tag"},
      {"name": "session_id", "type": "tag"},
      {"name": "author", "type": "tag"},
      {"name": "timestamp", "type": "numeric"},
    ]
    self._redis_vector_store = RedisVectorStore(
      redis_url=self._redis_url,
      index_name=self._index_name,
      embeddings=self._embeddings,
      metadata_schema = self._metadata_schema,
    )

  @override
  async def add_session_to_memory(self, session: Session):
    """Adds a session to the Redis memory."""
    texts = []
    metadatas = []
    for event in session.events:
      if not event.content or not event.content.parts:
        continue
      text_parts = [
          part.text.replace("\n", " ")
          for part in event.content.parts
          if part.text
      ]
      if text_parts:
        text = ". ".join(text_parts)
        texts.append(text)
        metadatas.append({
          "app_name": session.app_name,
          "user_id": session.user_id,
          "session_id": session.id,
          "author": event.author,
          "timestamp": event.timestamp,
        })

    if texts:
      RedisVectorStore.from_texts(
        texts=texts,
        embedding=self._embeddings,
        metadatas=metadatas,
        index_name=self._index_name,
        metadata_schema=self._metadata_schema,
        ttl=self._ttl
      )

  @override
  async def search_memory(
      self, *, app_name: str, user_id: str, query: str
  ) -> SearchMemoryResponse:
    """Searches for sessions that match the query."""
    from google.adk.events.event import Event
    from collections import OrderedDict

    filter_by_app_name = Tag("app_name") == app_name
    filter_by_user_id = Tag("user_id") == user_id
    combined_filter = filter_by_app_name & filter_by_user_id
    results = self._redis_vector_store.similarity_search(
      query, k=self._similarity_top_k, filter=combined_filter
    )

    memory_results = []
    session_events_map = OrderedDict()
    for doc in results:
      metadata = doc.metadata
      session_id = metadata.get("session_id", "")
      if not session_id:
        continue

      text = metadata.get("text", doc.page_content)
      author = metadata.get("author", "")
      timestamp = float(metadata.get("timestamp", 0))

      content = types.Content(parts=[types.Part(text=text)])
      event = Event(
          author=author,
          timestamp=timestamp,
          content=content,
      )
      if session_id in session_events_map:
        session_events_map[session_id].append([event])
      else:
        session_events_map[session_id] = [[event]]

    # Remove overlap and combine events from the same session.
    for session_id, event_lists in session_events_map.items():
      for events in _merge_event_lists(event_lists):
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        memory_results.extend([
          MemoryEntry(
            author=event.author,
            content=event.content,
            timestamp=datetime.datetime.fromtimestamp(event.timestamp).strftime(
              "%Y-%m-%d %H:%M:%S"
            ),
          )
          for event in sorted_events
          if event.content
        ])
    return SearchMemoryResponse(memories=memory_results)

def _merge_event_lists(event_lists: list[list["Event"]]) -> list[list["Event"]]:
  """Merge event lists that have overlapping timestamps."""
  merged = []
  while event_lists:
    current = event_lists.pop(0)
    current_ts = {event.timestamp for event in current}
    merge_found = True

    # Keep merging until no new overlap is found.
    while merge_found:
      merge_found = False
      remaining = []
      for other in event_lists:
        other_ts = {event.timestamp for event in other}
        # Overlap exists, so we merge and use the merged list to check again
        if current_ts & other_ts:
          new_events = [e for e in other if e.timestamp not in current_ts]
          current.extend(new_events)
          current_ts.update(e.timestamp for e in new_events)
          merge_found = True
        else:
          remaining.append(other)
      event_lists = remaining
    merged.append(current)
  return merged
