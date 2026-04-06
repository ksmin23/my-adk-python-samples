#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"""
DEO (Direct Embedding Optimization) engine for negation-aware retrieval.

Adapts the DEO paper's gradient-based query embedding optimization
to work with Vertex AI embeddings and BigQuery Vector Store.

Reference: DEO: Training-Free Direct Embedding Optimization
           for Negation-Aware Retrieval (arXiv:2603.09185)
"""

import logging
from typing import List

import torch
import torch.nn.functional as F
from langchain_google_vertexai import VertexAIEmbeddings

logger = logging.getLogger(__name__)


class DEOOptimizer:
  """Optimizes query embeddings using DEO's contrastive loss.

  Takes a query and its positive/negative sub-query decomposition,
  then applies gradient descent to move the query embedding closer to
  positive intents and away from negative intents.
  """

  def __init__(self, embedding_model: VertexAIEmbeddings):
    self.embedding_model = embedding_model

  def _get_embedding(self, text: str) -> torch.Tensor:
    """Get a single query embedding from Vertex AI, returned as normalized tensor."""
    vector = self.embedding_model.embed_query(text)
    emb = torch.tensor([vector], dtype=torch.float32)  # (1, dim)
    return F.normalize(emb, p=2, dim=1)

  def _get_embeddings(self, texts: List[str]) -> torch.Tensor:
    """Get multiple embeddings from Vertex AI, returned as normalized tensors."""
    vectors = self.embedding_model.embed_documents(texts)
    embs = torch.tensor(vectors, dtype=torch.float32)  # (N, dim)
    return F.normalize(embs, p=2, dim=1)

  def optimize(
    self,
    query: str,
    positives: List[str],
    negatives: List[str],
    num_steps: int = 20,
    lr: float = 0.001,
    pos_weight: float = 1.0,
    neg_weight: float = 1.0,
    reg_weight: float = 0.2,
  ) -> List[float]:
    """Optimize query embedding using DEO's contrastive loss.

    Loss function (DEO paper Eq. 4):
      L(eu) = λp · mean(||eu - epi||) - λn · mean(||eu - enj||) + λo · ||eu - eo||

    Args:
      query: Original user query.
      positives: Positive sub-queries (aspects to include).
      negatives: Negative sub-queries (aspects to exclude).
      num_steps: Number of optimization steps (paper default: 20).
      lr: Learning rate for Adam optimizer.
      pos_weight: Weight for positive attraction loss (λp).
      neg_weight: Weight for negative repulsion loss (λn).
      reg_weight: Weight for consistency regularization loss (λo).

    Returns:
      Optimized embedding as list[float], compatible with
      BigQueryVectorStore.similarity_search_by_vector().
    """
    # Phase 1: Get all embeddings from Vertex AI
    orig_emb = self._get_embedding(query)  # (1, dim)

    pos_embs = None
    if positives:
      pos_embs = self._get_embeddings(positives)  # (K, dim)

    neg_embs = None
    if negatives:
      neg_embs = self._get_embeddings(negatives)  # (M, dim)

    # Phase 2: Initialize learnable embedding
    # Only this single vector is optimized — the encoder is never touched.
    updated_emb = orig_emb.clone().detach().requires_grad_(True)
    optimizer = torch.optim.Adam([updated_emb], lr=lr)

    # Phase 3: Optimization loop
    for step in range(num_steps):
      optimizer.zero_grad()

      # Positive attraction: pull toward positive sub-query embeddings
      pos_loss = torch.tensor(0.0)
      if pos_embs is not None and len(pos_embs) > 0:
        pos_loss = torch.norm(updated_emb - pos_embs, dim=1).mean()

      # Consistency regularization: don't drift too far from original
      dev_loss = torch.norm(updated_emb - orig_emb)

      # Negative repulsion: push away from negative sub-query embeddings
      neg_loss = torch.tensor(0.0)
      if neg_embs is not None and len(neg_embs) > 0:
        neg_loss = torch.norm(updated_emb - neg_embs, dim=1).mean()

      # Combined loss: minimize pos_loss and dev_loss, maximize neg_loss
      loss = pos_weight * pos_loss + reg_weight * dev_loss - neg_weight * neg_loss
      loss.backward()
      optimizer.step()

      # Re-project onto unit sphere (maintains cosine similarity compatibility)
      with torch.no_grad():
        updated_emb.data = F.normalize(updated_emb.data, p=2, dim=-1)

      if step == 0 or step == num_steps - 1:
        logger.info(
          f"  DEO step {step:3d} | loss={loss.item():.4f} "
          f"pos={pos_loss.item():.4f} reg={dev_loss.item():.4f} neg={neg_loss.item():.4f}"
        )

    # Phase 4: Return as list[float] for BigQuery compatibility
    return updated_emb.detach().squeeze().tolist()
