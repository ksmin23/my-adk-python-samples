#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import json
import logging
import asyncio
from dataclasses import dataclass, field
from typing import List, Union, Any, cast, Set
import numpy as np
import networkx as nx
from google.cloud import spanner
from google.cloud.spanner_v1 import param_types

from PathRAG.base import BaseKVStorage, BaseVectorStorage, BaseGraphStorage, StorageNameSpace
from PathRAG.utils import EmbeddingFunc

logger = logging.getLogger(__name__)

# Helper to get Spanner client
def get_spanner_database():
  project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
  instance_id = os.environ.get("SPANNER_INSTANCE")
  database_id = os.environ.get("SPANNER_DATABASE")
  
  if not all([project_id, instance_id, database_id]):
     raise ValueError("Missing Spanner environment variables")
     
  client = spanner.Client(project=project_id)
  instance = client.instance(instance_id)
  return instance.database(database_id)

@dataclass
class SpannerKVStorage(BaseKVStorage):
  def __post_init__(self):
    self.db = get_spanner_database()

  async def all_keys(self) -> list[str]:
    # Using sync API in default executor for async compatibility
    def _get_keys():
      with self.db.snapshot() as snapshot:
        results = snapshot.execute_sql(
          "SELECT key FROM PathRagKV WHERE namespace = @namespace",
          params={"namespace": self.namespace},
          param_types={"namespace": param_types.STRING}
        )
        return [row[0] for row in results]
    return await asyncio.to_thread(_get_keys)

  async def get_by_id(self, id: str) -> Union[dict, None]:
    def _get():
      with self.db.snapshot() as snapshot:
        results = snapshot.execute_sql(
          "SELECT value FROM PathRagKV WHERE namespace = @namespace AND key = @key",
          params={"namespace": self.namespace, "key": id},
          param_types={"namespace": param_types.STRING, "key": param_types.STRING}
        )
        for row in results:
          return row[0] # Returns JSON object/dict
      return None
    return await asyncio.to_thread(_get)

  async def get_by_ids(self, ids: list[str], fields: Union[set[str], None] = None) -> list[Union[dict, None]]:
    # Naive implementation: select all and filter in memory or select *
    # Spanner limits 'IN' clause size, better to batch if ids are many.
    # For simplicity, we loop or use IN with checking length.
    
    async def _fetch(id):
      return await self.get_by_id(id)

    # Helper to fetch one by one concurrently (optimize later with batch read)
    tasks = [_fetch(id) for id in ids]
    results = await asyncio.gather(*tasks)
    
    if fields:
      filtered_results = []
      for res in results:
        if res:
          filtered_results.append({k: v for k, v in res.items() if k in fields})
        else:
          filtered_results.append(None)
      return filtered_results
    return results

  async def filter_keys(self, data: list[str]) -> set[str]:
    # Return keys from 'data' that are NOT in DB
    existing_keys = set(await self.all_keys())
    return set([k for k in data if k not in existing_keys])

  async def upsert(self, data: dict[str, dict]):
    def _upsert():
      with self.db.batch() as batch:
        batch.insert_or_update(
          table="PathRagKV",
          columns=("namespace", "key", "value"),
          values=[(self.namespace, k, v) for k, v in data.items()]
        )
    await asyncio.to_thread(_upsert)
    return data

  async def drop(self):
    # Delete all for namespace
    def _drop():
      with self.db.batch() as batch:
        # DML DELETE
        batch.execute_update(
          "DELETE FROM PathRagKV WHERE namespace = @namespace",
          params={"namespace": self.namespace},
          param_types={"namespace": param_types.STRING}
        )
    await asyncio.to_thread(_drop)

@dataclass
class SpannerVectorStorage(BaseVectorStorage):
  def __post_init__(self):
    self.db = get_spanner_database()
    
  async def upsert(self, data: dict[str, dict]):
    if not data:
      return
      
    # Generate embeddings
    # Assuming embedding_func returns np.ndarray
    keys = list(data.keys())
    contents = [v["content"] for v in data.values()]
    
    embeddings = await self.embedding_func(contents)
    
    # Prepare rows
    rows = []
    for i, key in enumerate(keys):
      row = (
        self.namespace,
        key,
        contents[i],
        [float(x) for x in embeddings[i]] # Spanner needs float list
      )
      rows.append(row)
      
    def _upsert():
      with self.db.batch() as batch:
         batch.insert_or_update(
          table="PathRagVector",
          columns=("namespace", "id", "content", "embedding"),
          values=rows
        )
    await asyncio.to_thread(_upsert)

  async def query(self, query: str, top_k: int) -> list[dict]:
    # Generate query embedding
    embedding = await self.embedding_func([query])
    query_vector = [float(x) for x in embedding[0]]
    
    # Spanner Vector Search (Cosine Distance)
    # Using COSINE_DISTANCE function
    def _query():
      sql = """
        SELECT id, content, COSINE_DISTANCE(embedding, @query_vector) as distance
        FROM PathRagVector
        WHERE namespace = @namespace
        ORDER BY distance
        LIMIT @top_k
      """
      with self.db.snapshot() as snapshot:
        results = snapshot.execute_sql(
          sql,
          params={
            "namespace": self.namespace,
            "query_vector": query_vector,
            "top_k": top_k
          },
          param_types={
            "namespace": param_types.STRING,
            "query_vector": param_types.ARRAY(param_types.FLOAT64),
            "top_k": param_types.INT64
          }
        )
        
        return [
          {
            "id": row[0],
            "content": row[1],
            "distance": row[2]
          }
          for row in results
        ]
    return await asyncio.to_thread(_query)
    
  async def delete_entity(self, entity_name: str):
     pass
     
  async def delete_relation(self, entity_name: str):
     pass

@dataclass
class SpannerGraphStorage(BaseGraphStorage):
  def __post_init__(self):
    self.db = get_spanner_database()

  async def has_node(self, node_id: str) -> bool:
    def _check():
      with self.db.snapshot() as snapshot:
        results = snapshot.execute_sql(
          "SELECT 1 FROM Nodes WHERE node_id = @node_id",
          params={"node_id": node_id},
          param_types={"node_id": param_types.STRING}
        )
        return any(results)
    return await asyncio.to_thread(_check)

  async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
    def _check():
      with self.db.snapshot() as snapshot:
        results = snapshot.execute_sql(
          "SELECT 1 FROM Edges WHERE source_node_id = @src AND target_node_id = @tgt",
          params={"src": source_node_id, "tgt": target_node_id},
          param_types={"src": param_types.STRING, "tgt": param_types.STRING}
        )
        return any(results)
    return await asyncio.to_thread(_check)

  async def node_degree(self, node_id: str) -> int:
    # GQL or SQL count
    def _count():
      sql = """
        SELECT count(*) FROM Edges 
        WHERE source_node_id = @node_id OR target_node_id = @node_id
      """
      with self.db.snapshot() as snapshot:
        res = snapshot.execute_sql(sql, params={"node_id": node_id}, param_types={"node_id": param_types.STRING})
        for row in res:
          return row[0]
      return 0
    return await asyncio.to_thread(_count)

  async def edge_degree(self, src_id: str, tgt_id: str) -> int:
    return (await self.node_degree(src_id)) + (await self.node_degree(tgt_id))

  async def get_node(self, node_id: str) -> Union[dict, None]:
    def _get():
      with self.db.snapshot() as snapshot:
        res = snapshot.execute_sql(
          "SELECT * FROM Nodes WHERE node_id = @node_id",
           params={"node_id": node_id},
           param_types={"node_id": param_types.STRING}
        )
        for row in res:
          # Map row to dict, need column names
          return {
            "node_id": row[0],
            "entity_type": row[1],
            "description": row[2],
            "source_id": row[3]
          }
      return None
    return await asyncio.to_thread(_get)

  async def get_edge(self, source_node_id: str, target_node_id: str) -> Union[dict, None]:
    def _get():
       with self.db.snapshot() as snapshot:
        res = snapshot.execute_sql(
          "SELECT * FROM Edges WHERE source_node_id = @src AND target_node_id = @tgt",
           params={"src": source_node_id, "tgt": target_node_id},
           param_types={"src": param_types.STRING, "tgt": param_types.STRING}
        )
        for row in res:
          return {
            "source_node_id": row[0],
            "target_node_id": row[1],
            "description": row[2],
            "keywords": row[3],
            "weight": row[4]
          }
    return await asyncio.to_thread(_get)

  async def get_node_edges(self, source_node_id: str) -> list[tuple[str, str]]:
    def _get():
      with self.db.snapshot() as snapshot:
        res = snapshot.execute_sql(
          "SELECT source_node_id, target_node_id FROM Edges WHERE source_node_id = @id",
          params={"id": source_node_id},
          param_types={"id": param_types.STRING}
        )
        return [(row[0], row[1]) for row in res]
    return await asyncio.to_thread(_get)
    
  async def get_node_in_edges(self, source_node_id: str) -> list[tuple[str, str]]:
    def _get():
      with self.db.snapshot() as snapshot:
        res = snapshot.execute_sql(
          "SELECT source_node_id, target_node_id FROM Edges WHERE target_node_id = @id",
          params={"id": source_node_id},
          param_types={"id": param_types.STRING}
        )
        return [(row[0], row[1]) for row in res]
    return await asyncio.to_thread(_get)
    
  async def get_node_out_edges(self, source_node_id: str) -> list[tuple[str, str]]:
    return await self.get_node_edges(source_node_id) # Same as get_node_edges for directed

  async def upsert_node(self, node_id: str, node_data: dict[str, str]):
    def _upsert():
      with self.db.batch() as batch:
        batch.insert_or_update(
          table="Nodes",
          columns=("node_id", "entity_type", "description", "source_id"),
          values=[(
            node_id, 
            node_data.get("entity_type"), 
            node_data.get("description"), 
            node_data.get("source_id")
          )]
        )
    await asyncio.to_thread(_upsert)

  async def upsert_edge(self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]):
    def _upsert():
      with self.db.batch() as batch:
        batch.insert_or_update(
          table="Edges",
          columns=("source_node_id", "target_node_id", "description", "keywords", "weight"),
          values=[(
            source_node_id,
            target_node_id,
            edge_data.get("description"),
            edge_data.get("keywords"),
            float(edge_data.get("weight", 1.0))
          )]
        )
    await asyncio.to_thread(_upsert)
    
  async def delete_node(self, node_id: str):
     pass
     
  async def embed_nodes(self, algorithm: str) -> tuple[np.ndarray, list[str]]:
    return np.array([]), []

  async def get_pagerank(self, node_id: str) -> float:
    # TODO: Implement PageRank using Spanner Graph or GQL
    # For now return default 1.0 or similar
    return 1.0

from PathRAG.PathRAG import PathRAG

@dataclass
class SpannerPathRAG(PathRAG):
  def _get_storage_class(self):
    storage_classes = super()._get_storage_class()
    storage_classes.update({
      "SpannerKVStorage": SpannerKVStorage,
      "SpannerVectorStorage": SpannerVectorStorage,
      "SpannerGraphStorage": SpannerGraphStorage,
    })
    return storage_classes
