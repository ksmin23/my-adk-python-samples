# DEO: Paper Analysis, Code Walkthrough, and Agentic RAG Architecture

An in-depth analysis of the DEO (Direct Embedding Optimization) paper and its reference implementation, covering the core algorithm, code-paper correspondence, experimental evaluation, latency considerations, and a recommended agent architecture for production Agentic RAG using Google ADK.

- **Paper**: [DEO: Training-Free Direct Embedding Optimization for Negation-Aware Retrieval](https://arxiv.org/abs/2603.09185)
- **Code**: [:octocat: DEO-negation-aware-retrieval](https://github.com/taegyeong-lee/DEO-negation-aware-retrieval) (analyzed at commit [`d8efb22`](https://github.com/taegyeong-lee/DEO-negation-aware-retrieval/tree/d8efb22))

## Table of Contents

- [Paper Summary: DEO (Direct Embedding Optimization)](#paper-summary-deo-direct-embedding-optimization)
- [Code-Paper Mapping Analysis](#code-paper-mapping-analysis)
  - [1. Query Decomposition (Paper Section 3.1)](#1-query-decomposition-paper-section-31)
  - [2. Direct Embedding Optimization (Paper Section 3.2)](#2-direct-embedding-optimization-paper-section-32)
    - [Step-by-Step Embedding Optimization Analysis](#step-by-step-embedding-optimization-analysis)
    - [Geometric Interpretation of the Loss Function](#geometric-interpretation-of-the-loss-function)
  - [3. Embedding & Retrieval (Paper Section 3.3)](#3-embedding--retrieval-paper-section-33)
    - [Optimized Embedding → FAISS Search: Detailed Analysis](#optimized-embedding--faiss-search-detailed-analysis)
  - [4. Datasets (Paper Section 4.1)](#4-datasets-paper-section-41)
  - [5. Evaluation (Paper Section 4)](#5-evaluation-paper-section-4)
  - [6. Overall Pipeline](#6-overall-pipeline)
- [Optimized vs. Non-Optimized Embedding Comparison (Paper Section 4.3.3, 5.2)](#optimized-vs-non-optimized-embedding-comparison-paper-section-433-52)
  - [Comparison Structure in the Paper](#comparison-structure-in-the-paper)
  - [Branching Point in the Code](#branching-point-in-the-code)
  - [How to Run Comparative Experiments](#how-to-run-comparative-experiments)
- [Latency Analysis for Agentic RAG Applications](#latency-analysis-for-agentic-rag-applications)
  - [Actual Cost of the Optimization Loop](#actual-cost-of-the-optimization-loop)
  - [Per-Query Total Latency Breakdown](#per-query-total-latency-breakdown)
  - [Practicality Assessment for Agentic RAG](#practicality-assessment-for-agentic-rag)
  - [Latency Mitigation Through Caching in the Code](#latency-mitigation-through-caching-in-the-code)
  - [Additional Optimization Strategies (Not Implemented in Code)](#additional-optimization-strategies-not-implemented-in-code)
- [Recommended Google ADK-Based DEO Agentic RAG Agent Architecture](#recommended-google-adk-based-deo-agentic-rag-agent-architecture)
  - [Core Design Principles](#core-design-principles)
  - [Recommended Agent Structure](#recommended-agent-structure)
  - [Detailed Design for Each Agent](#detailed-design-for-each-agent)
  - [Execution Flow Example](#execution-flow-example)
  - [Alternative Architecture: Simplified Version](#alternative-architecture-simplified-version)
  - [Architecture Selection Guide](#architecture-selection-guide)
- [Additional Implementation Beyond the Paper](#additional-implementation-beyond-the-paper)
- [Summary](#summary)

---

## Paper Summary: DEO (Direct Embedding Optimization)

- **Title**: DEO: Training-Free Direct Embedding Optimization for Negation-Aware Retrieval
- **Authors**: Taegyeong Lee, Jiwon Park, Seunghyun Hwang, JooYoung Jang
- **arXiv**: [2603.09185](https://arxiv.org/abs/2603.09185)

**Core Idea**: A **training-free** approach that decomposes queries with negation/exclusion into positive/negative sub-queries using an LLM, then directly optimizes the query embedding via gradient descent.

**Loss Function (Eq. 4)**:

```
L(eu) = λp · mean(||eu - epi||) - λn · mean(||eu - enj||) + λo · ||eu - eo||
```

- **Attract** toward positive embeddings (attraction)
- **Repel** from negative embeddings (repulsion)
- **Regularize** to prevent drifting too far from the original query (consistency)

---

## Code-Paper Mapping Analysis

### 1. Query Decomposition (Paper Section 3.1)

**Code**: `src/llm.py` (`PolarityLLM.expand()`) + `prompts/v1.yaml`

- Uses an LLM (OpenAI API or local Qwen) to decompose queries into `{"positives": [...], "negatives": [...]}` format
- Supports both GPT-4.1-nano and Qwen2.5-1.5B-Instruct as described in the paper (`src/llm.py:34-56`)
- The prompt (`prompts/v1.yaml`) faithfully reflects the paper's decomposition intent: positives semantically expand the query, while negatives are generated minimally for explicitly excluded items only

### 2. Direct Embedding Optimization (Paper Section 3.2)

**Code**: `src/embedder.py:39-133` (`OptimizedEmbedder.optimize_embedding()`)

Exact correspondence between the paper's equations and the code:

| Paper | Code (`src/embedder.py`) |
|-------|--------------------------|
| `eo = E(q)` | `orig_emb = self.encode(query)` (line 67) |
| `eu ← eo` (learnable) | `updated_emb = orig_emb.clone().detach().requires_grad_(True)` (line 72) |
| `λp · mean(‖eu - epi‖)` | `pos_loss = torch.norm(updated_emb - pos_embs, dim=1).mean()` (line 85) |
| `λo · ‖eu - eo‖` | `dev_loss = torch.norm(updated_emb - orig_emb)` (line 87) |
| `-λn · mean(‖eu - enj‖)` | `neg_loss = torch.norm(updated_emb - neg_embs, dim=1).mean()` (line 91) |
| `L = λp·Lpos + λo·Lreg - λn·Lneg` | `loss = pos_weight * pos_loss + reg_weight * dev_loss - neg_weight * neg_loss` (line 93) |

- Optimizer: Adam (`src/embedder.py:73`) — matches the paper
- L2 normalization after every step: `F.normalize(updated_emb.data)` (`src/embedder.py:98`)
- Paper default hyperparameters `λp=1, λn=1, λo=0.2, steps=20` → code defaults (`src/config.py:27-31`): `pos_weight=1.0, neg_weight=1.0, reg_weight=0.2, optimization_steps=500` — **only steps differ** (paper uses 20)

#### Step-by-Step Embedding Optimization Analysis

##### Phase 1: Cache Lookup (line 48-64)

```python
if use_cache and self.checkpoint_manager:
    cached = self.checkpoint_manager.load_optimized_embedding(
        query, dataset, reg_weight, pos_weight, neg_weight,
        num_steps, lr, ...
    )
    if cached:
        emb, metadata = cached
        return torch.tensor(emb, device=self.device)
```

The cache key is a combination of `(query, dataset, reg_weight, pos_weight, neg_weight, num_steps, lr, embed_model, decompose_model, prompt_version)`. If the same conditions are found, optimization is skipped entirely.

##### Phase 2: Pre-compute Embeddings (line 67-70)

```python
orig_emb = self.encode(query, normalize=True)       # eo: original query embedding
pos_embs = self.encode(positives, normalize=True)    # epi: positive sub-query embeddings
neg_embs = self.encode(negatives, normalize=True)    # enj: negative sub-query embeddings
```

Internal workings of `encode()` (line 23-37):

```python
def encode(self, texts, normalize=True):
    inputs = self.tokenizer(texts, padding=True, truncation=True, max_length=512)
    with torch.no_grad():                              # encoder is completely frozen
        outputs = self.model(**inputs)
        embeddings = outputs.last_hidden_state[:, 0]   # extract CLS token only
        if normalize:
            embeddings = F.normalize(embeddings, p=2, dim=1)  # normalize to unit vectors
    return embeddings
```

Key points:
- Wrapped in `torch.no_grad()`, so **no gradients flow through the encoder parameters**
- `orig_emb`, `pos_embs`, `neg_embs` are all treated as **fixed constant vectors**
- Uses CLS token (`[:, 0]`) as the sentence representation (standard practice for BGE model family)

For example, with 3 positives and 2 negatives:

```
orig_emb:  shape (1, 1024)    — 1 original query
pos_embs:  shape (3, 1024)    — 3 positive sub-queries
neg_embs:  shape (2, 1024)    — 2 negative sub-queries
```

##### Phase 3: Initialize Learnable Embedding (line 72-73)

```python
updated_emb = orig_emb.clone().detach().requires_grad_(True)
optimizer = torch.optim.Adam([updated_emb], lr=lr)
```

These two lines encapsulate the core design of DEO:

- `.clone()`: creates a copy of the original embedding (preserving the original)
- `.detach()`: completely separates from the encoder's computation graph
- `.requires_grad_(True)`: designates this vector as the **sole learnable parameter**
- The Adam optimizer's parameter list is `[updated_emb]` alone — optimizing a single 1024-dimensional vector, not millions of model parameters

##### Phase 4: Optimization Loop (line 80-109)

```python
for step in range(num_steps):
    optimizer.zero_grad()
```

At each step, the gradient is reset and three loss terms are computed:

**(i) Positive Attraction Loss** (line 83-85):

```python
pos_loss = torch.tensor(0.0, device=self.device)
if pos_embs is not None and len(pos_embs) > 0:
    pos_loss = torch.norm(updated_emb - pos_embs, dim=1).mean()
```

Broadcasting between `updated_emb` (1, 1024) and `pos_embs` (K, 1024):

```
updated_emb - pos_embs → (K, 1024)    # difference vector with each positive
torch.norm(..., dim=1)  → (K,)        # L2 distance for each difference
.mean()                 → scalar      # average of K distances
```

As this value decreases, `updated_emb` moves toward the **centroid** of all positive embeddings.

**(ii) Consistency Regularization Loss** (line 87):

```python
dev_loss = torch.norm(updated_emb - orig_emb)
```

Simple L2 distance from the original embedding. This constrains the embedding from losing too much of the original meaning while being pulled toward positives. Unlike the positive loss, this computes a norm against a **single vector**, so the `dim` argument is omitted.

**(iii) Negative Repulsion Loss** (line 89-91):

```python
neg_loss = torch.tensor(0.0, device=self.device)
if neg_embs is not None and len(neg_embs) > 0:
    neg_loss = torch.norm(updated_emb - neg_embs, dim=1).mean()
```

Structurally identical to the positive loss, but with an **inverted sign** in the final loss summation.

**Loss Summation** (line 93):

```python
loss = pos_weight * pos_loss + reg_weight * dev_loss - neg_weight * neg_loss
```

Effect of the minus sign:

```
minimize(loss) → minimize(pos_loss)    → eu moves closer to positives
              → minimize(dev_loss)    → eu stays near the original
              → minimize(-neg_loss)   → neg_loss increases → eu moves away from negatives
```

**Backpropagation + Normalization** (line 94-98):

```python
loss.backward()          # compute gradient w.r.t. updated_emb
optimizer.step()         # update updated_emb via Adam

with torch.no_grad():
    updated_emb.data = F.normalize(updated_emb.data, p=2, dim=-1)
```

`F.normalize` is applied at the end of each step to **re-project `updated_emb` onto the unit sphere**. This is important because:
- Corpus embeddings are also L2-normalized
- FAISS IndexFlatIP uses inner product for search → inner product of normalized vectors = cosine similarity
- Without normalization, the vector magnitude could grow, causing mismatch with cosine similarity-based search

##### Phase 5: Save and Return Results (line 111-133)

```python
final_emb = updated_emb.detach()

if self.checkpoint_manager:
    metadata = {
        "embed_model": self.model_name,
        "num_steps": num_steps, "lr": lr,
        "final_loss": history["total_losses"][-1],
        "initial_loss": history["total_losses"][0],
        "positive_queries": positives,
        "negative_queries": negatives,
        "loss_history": history,       # full trajectory of 4 loss types
    }
    self.checkpoint_manager.save_optimized_embedding(...)

return final_emb
```

The loss history records four values (`total_losses`, `pos_losses`, `deviation_losses`, `neg_losses`) at every step, enabling later visualization of the convergence process via `plot_optimization_history()` in `src/analysis.py:116-184`.

##### End-to-End Concrete Example

Query: *"Show me the latest earnings forecast, but exclude 2024 results"*

```
1. encode("Show me the latest earnings forecast, but exclude 2024 results")
   → orig_emb: [0.023, -0.041, 0.018, ...]  (1×1024, fixed)

2. encode(["2025 earnings forecast", "financial statements"])
   → pos_embs: [[0.031, -0.038, ...],        (2×1024, fixed)
                 [0.027, -0.045, ...]]

3. encode(["2024 earnings", "2024 financial report"])
   → neg_embs: [[0.025, -0.039, ...],        (2×1024, fixed)
                 [0.022, -0.042, ...]]

4. updated_emb = orig_emb.clone()              (1×1024, learnable)

5. 20 steps of optimization:
   Step  0: loss=0.8234 | pos=0.412 | reg=0.000 | neg=0.389
   Step  5: loss=0.5121 | pos=0.298 | reg=0.045 | neg=0.421
   Step 10: loss=0.3847 | pos=0.231 | reg=0.061 | neg=0.448
   Step 15: loss=0.3312 | pos=0.198 | reg=0.072 | neg=0.467
   Step 19: loss=0.3105 | pos=0.187 | reg=0.078 | neg=0.475
                           ↓ decreasing  ↓ slight increase  ↓ increasing
                        (closer to pos)  (drifted slightly)  (farther from neg)

6. Final updated_emb → used for FAISS search
```

Throughout this process, **no encoder model parameters are modified** — only a single 1024-dimensional vector moves. This is what "Training-Free" in the paper's title means.

#### Geometric Interpretation of the Loss Function

```
loss = pos_weight * pos_loss + reg_weight * dev_loss - neg_weight * neg_loss
                  ↑                      ↑                      ↑
          Force pulling eu          Penalty when eu           Force pushing eu
          toward positives          drifts from original      away from negatives
          (minimize → closer)       (minimize → closer)       (minimize → farther)
```

The **minus sign** before `neg_loss` is the key. Minimizing `loss`:
- `pos_loss` → decreases → `eu` moves closer to positive embeddings
- `dev_loss` → decreases → `eu` stays near the original
- `-neg_loss` → to decrease, `neg_loss` must increase → `eu` moves away from negative embeddings

### 3. Embedding & Retrieval (Paper Section 3.3)

**Code**: `src/embedder.py:23-37` (encoding) + `src/indexer.py` (FAISS index)

- CLS token usage (`src/embedder.py:34`): `outputs.last_hidden_state[:, 0]` — matches the paper
- FAISS IndexFlatIP (inner product-based search; equivalent to cosine similarity with normalized vectors) (`src/indexer.py:79`) — matches the paper
- Default embedding model: `BAAI/bge-m3` (`src/config.py:22`) — one of the models used in the paper's experiments

#### Optimized Embedding → FAISS Search: Detailed Analysis

##### Step 1: Return Optimized Embedding

After optimization completes at `src/embedder.py:111`:

```python
final_emb = updated_emb.detach()   # detach from computation graph (no more gradients needed)
return final_emb                    # shape: (1, 1024), torch.Tensor, on GPU
```

This is received in `src/retriever.py:108-124` and converted to numpy:

```python
optimized_embedding = self.embedder.optimize_embedding(
    query=query, positives=positives, negatives=negatives, ...
)
return optimized_embedding.cpu().numpy().astype("float32")
```

- `.cpu()`: GPU tensor → CPU tensor (required when using FAISS CPU index)
- `.numpy()`: PyTorch tensor → NumPy array
- `.astype("float32")`: convert to the data type required by FAISS

##### Step 2: FAISS Search via the Retriever

`src/retriever.py:55-64`:

```python
for idx, (qid, qtext) in enumerate(queries.items(), 1):
    # Query text → optimized vector
    qvec = self._get_optimized_query_embedding(qtext)   # shape: (1024,) float32

    # Search FAISS index for top_k results
    hits = self.indexer.search(qvec, top_k=cfg.top_k)   # top_k default: 1000

    # Convert results to {doc_id: score} dictionary
    results[qid] = {doc_id: score for doc_id, score in hits}
```

##### Step 3: Inside the FAISS Index Search

`src/indexer.py:89-97`:

```python
def search(self, qvec: np.ndarray, top_k: int = 100) -> List[Tuple[str, float]]:
    q = qvec.astype("float32").reshape(1, -1)   # (1024,) → (1, 1024) reshape to 2D
    D, I = self.index.search(q, top_k)           # core FAISS search
    hits = []
    for score, idx in zip(D[0].tolist(), I[0].tolist()):
        if idx == -1:          # FAISS returns -1 when results are insufficient
            continue
        hits.append((self.doc_ids[idx], float(score)))
    return hits
```

Return values of `self.index.search(q, top_k)`:
- `D`: distances (scores) array, shape `(1, top_k)` — inner product values (higher = more similar)
- `I`: indices array, shape `(1, top_k)` — document indices in the corpus

`self.doc_ids[idx]` converts integer indices to actual document ID strings.

##### Step 4: How the FAISS Index Was Built

To understand search results, we need to see how the index was constructed.

`src/indexer.py:39-87`, `build_or_load()`:

```python
def build_or_load(self, dataset, corpus):
    # 1) Save document ID ordering
    self.doc_ids = list(corpus.keys())

    # 2) Convert each document's text to an embedding
    texts = [corpus[_id].get("text", "") or corpus[_id].get("title", "")
             for _id in self.doc_ids]

    # 3) Batch encoding (using the same encoder as queries)
    for i in range(0, len(texts), batch_size):     # batch_size = 64
        batch_embeddings = self.embedder.encode(batch_texts, normalize=True)
        all_embeddings.append(batch_embeddings.cpu().numpy())

    embeddings = np.vstack(all_embeddings).astype("float32")
    # shape: (num_docs, 1024), e.g., (N, 1024) for the nsir dataset

    # 4) Create FAISS Inner Product index
    cpu_index = faiss.IndexFlatIP(self.dim)    # dim = 1024
    cpu_index.add(embeddings)                   # add all document embeddings
```

Key points:
- `IndexFlatIP`: brute-force search based on **inner product**
- Since both query and document embeddings are L2-normalized, inner product = cosine similarity:

```
cos(a, b) = (a · b) / (||a|| · ||b||)
           = a · b        (when ||a|| = ||b|| = 1)
```

##### Step 5: What Search Scores Mean

The score returned by search represents:

```
score = dot(optimized_query_emb, doc_emb)
      = cos(optimized_query_emb, doc_emb)    (both are normalized)
      ∈ [-1, 1]
```

- `score ≈ 1`: query and document are semantically very similar
- `score ≈ 0`: unrelated
- `score < 0`: semantically opposite direction

How DEO optimization affects these scores:

```
Baseline:    score = dot(eo, doc_emb)          ← original query as-is
DEO:         score = dot(eu, doc_emb)          ← optimized query

eu moves toward positives → dot product with positive-related documents increases
eu moves away from negatives → dot product with negative-related documents decreases
```

##### Step 6: Search Results → Evaluation

After all query results are collected in `src/retriever.py:63-64`:

```python
results[qid] = {doc_id: score for doc_id, score in hits}
# e.g., {"doc_123": 0.8721, "doc_456": 0.8534, "doc_789": 0.8201, ...}
```

These are passed to the BEIR evaluator in `src/main.py:92-93`:

```python
evaluator = EvaluateRetrieval(retriever, score_function="dot")
ndcg, _map, recall, precision = evaluator.evaluate(qrels, results, [10, cfg.k_eval])
```

The evaluator **sorts documents by score in descending order** and computes metrics such as NDCG@10 by comparing against `qrels` (ground truth labels).

##### Before vs. After Optimization: Search Result Comparison

```
Query: "Show me the latest earnings forecast, but exclude 2024 results"

■ Baseline (search with eo as-is)
  rank 1: "Q3 2024 Earnings Report"          score=0.891  ← should be excluded!
  rank 2: "2025 Earnings Forecast Analysis"   score=0.887
  rank 3: "2024 Annual Financial Statements"  score=0.874  ← should be excluded!
  rank 4: "2025-2026 Earnings Prediction"     score=0.861

■ DEO (search with eu) — eu has moved away from "2024"-related embeddings
  rank 1: "2025 Earnings Forecast Analysis"   score=0.912  ← correct!
  rank 2: "2025-2026 Earnings Prediction"     score=0.898  ← correct!
  rank 3: "Latest Quarterly Earnings Trends"  score=0.871
  rank 4: "Q3 2024 Earnings Report"           score=0.743  ← demoted in ranking
```

The FAISS index itself remains unchanged — **only the query vector changed**, yet the search rankings differ. This is the core mechanism of DEO.

### 4. Datasets (Paper Section 4.1)

**Code**: `src/data_loader.py`

- **BEIR datasets**: automatic download support for nsir, scifact, arguana, etc. (`src/data_loader.py:35-43`)
- **NevIR**: loaded from HuggingFace, converted to BEIR-compatible format (`src/data_loader.py:48-80`)
- The **NegConstraint** dataset mentioned in the paper appears to be named `nsir` in the code (`beir/nsir/`)

### 5. Evaluation (Paper Section 4)

**Code**: `src/evaluator.py` + `src/main.py:92-106`

- Computes NDCG@10, MAP@K, Recall@K, Precision@K using the official BEIR evaluator — matches the paper
- NevIR **pairwise accuracy** evaluation (`src/evaluator.py:6-51`): both q1→doc1 and q2→doc2 must be correct for a positive — matches the paper
- Separate evaluation for neg group vs. pos-only group is also implemented in `src/analysis.py`

### 6. Overall Pipeline

**Code**: `src/retriever.py` (`OptimizedPolarityRetriever`)

```
Query → LLM Decomposition (positives/negatives) → Embedding Optimization → FAISS Search → Evaluation
```

The core flow resides in `_get_optimized_query_embedding()` at `src/retriever.py:90-124`:

1. If `use_optimization=False`: baseline (use original embedding as-is)
2. If `use_optimization=True`: LLM decomposition → gradient optimization → return optimized embedding

---

## Optimized vs. Non-Optimized Embedding Comparison (Paper Section 4.3.3, 5.2)

### Comparison Structure in the Paper

The paper compares multiple levels of embeddings for the **same query**:

#### 1. Baseline (Non-Optimized)

Search using the original embedding `eo = E(q)` obtained by passing the query directly to the embedding model. The original query vector is used as-is, without any decomposition or optimization.

#### 2. Only Decompose (Paper Table 6)

Variants that perform LLM decomposition but **no gradient optimization**:
- **AVG**: Simple average of positive/negative sub-query embeddings for search
- **RRF**: Individual search per sub-query, then Reciprocal Rank Fusion to merge

Paper results (NegConstraint, BGE-M3):

| Method | MAP | nDCG@10 |
|--------|-----|---------|
| Baseline | 0.6374 | 0.7250 |
| Only Decompose (AVG) | 0.6451 | 0.7312 |
| Only Decompose (RRF) | 0.6641 | 0.7417 |
| **Full DEO** | **0.7379** | **0.7946** |

Key finding: decomposition alone yields limited improvement; **most of the performance gain comes from embedding optimization**.

#### 3. Full DEO (Optimized)

Both decomposition and gradient-based contrastive optimization are applied.

### Branching Point in the Code

A single branch in `_get_optimized_query_embedding()` at `src/retriever.py:90-124` determines the path:

- **Baseline path** (`use_optimization=False`): `src/retriever.py:93-97`
  - `self.embedder.encode(query, normalize=True)` → returns original embedding
- **Optimized path** (`use_optimization=True`): `src/retriever.py:99-124`
  - `self.llm.expand(query)` → LLM decomposition
  - `self.embedder.optimize_embedding(...)` → gradient optimization

### How to Run Comparative Experiments

`run_experiments.py:31-43` runs baseline and optimized configurations sequentially on the same dataset:

```python
weight_experiments = [
    # Baseline: no optimization
    {"reg_weight": 0.0, "pos_weight": 0.0, "neg_weight": 0.0,
     "optimization_steps": 0, "use_optimization": False},
    # DEO: optimization enabled
    {"reg_weight": 0.2, "pos_weight": 1.0, "neg_weight": 1.0,
     "optimization_steps": 20, "use_optimization": True},
]
```

Result comparison is performed in `compare_weight_configs()` at `src/analysis.py:28-113`. It loads result JSONs from the `checkpoints/results/` directory and outputs NDCG@10, MAP@100 tables by weight config for the same dataset/model combination, calculating ΔMAP relative to baseline.

---

## Latency Analysis for Agentic RAG Applications

### Actual Cost of the Optimization Loop

Measurements reported directly in Paper Section 5.3:

| Environment | 20 steps | 50 steps |
|-------------|----------|----------|
| CPU (Ryzen 7 5800X) | **0.016s** (0.67ms/step) | 0.035s |
| GPU (RTX 3060) | **0.033s** (1.7ms/step) | 0.095s |

The optimization loop operates on a **single vector** (`updated_emb`) only. Since it performs gradient descent on a single 1024-dimensional vector (for BGE-M3), not training an entire model, the computational cost is extremely low.

Code reference (`src/embedder.py:72-73`):
```python
updated_emb = orig_emb.clone().detach().requires_grad_(True)  # single 1×d vector
optimizer = torch.optim.Adam([updated_emb], lr=lr)             # 1 parameter
```

### Per-Query Total Latency Breakdown

```
┌───────────────────────────────────────────────────────────────┐
│ 1. LLM Query Decomposition (llm.py:expand)                    │
│    - OpenAI API call: ~200-500ms (network round-trip)         │
│    - Local Qwen 1.5B: ~100-300ms (GPU inference)              │
│    ★ Largest bottleneck                                       │
├───────────────────────────────────────────────────────────────┤
│ 2. Sub-query Encoding (embedder.py:67-70)                     │
│    - orig_emb = encode(query)           ~5-10ms               │
│    - pos_embs = encode(positives)       ~10-30ms              │
│    - neg_embs = encode(negatives)       ~10-30ms              │
│    ★ Second bottleneck (3 encoder forward passes)             │
├───────────────────────────────────────────────────────────────┤
│ 3. Optimization Loop (embedder.py:80-98)                      │
│    - 20 steps × ~1ms/step               ~16-33ms              │
│    ★ Less than ~5% of total                                   │
├───────────────────────────────────────────────────────────────┤
│ 4. FAISS Search (indexer.py:89-97)                            │
│    - IndexFlatIP search                  ~1-5ms               │
└───────────────────────────────────────────────────────────────┘
  Total: ~300-800ms / query
```

### Practicality Assessment for Agentic RAG

Typical latency budget for a RAG pipeline:

| Stage | Standard RAG | With DEO |
|-------|-------------|----------|
| Query processing | ~10ms | ~300-500ms (including LLM decomposition) |
| Retrieval | ~5-50ms | ~5-50ms (same) |
| LLM response generation | ~1-3s | ~1-3s (same) |
| **Total** | **~1-3s** | **~1.3-3.5s** |

Since LLM response generation dominates the total time, the 300-500ms added by DEO is relatively small in terms of perceived end-to-end latency.

### Latency Mitigation Through Caching in the Code

**1) LLM Decomposition Result Caching** (`src/llm.py:110-117`):
```python
cached = self.checkpoint_manager.load_decomposition(query, dataset, ...)
if cached:
    return cached  # skip API call → ~0ms
```

**2) Optimized Embedding Caching** (`src/embedder.py:48-64`):
```python
cached = self.checkpoint_manager.load_optimized_embedding(query, dataset, ...)
if cached:
    return torch.tensor(emb, device=self.device)  # skip entire optimization → ~1ms
```

On cache hits, per-query latency drops to **a few milliseconds**.

### Additional Optimization Strategies (Not Implemented in Code)

For production Agentic RAG deployment:

1. **Asynchronous decomposition**: Process LLM decomposition asynchronously to parallelize with other tasks
2. **Batch optimization**: Group multiple queries' `updated_emb` vectors for batch optimization
3. **Reduce steps**: Paper Figure 2 shows that 5-10 steps capture most of the performance gain (convergence at 20 steps)
4. **Selective application**: Apply DEO only to queries with detected negation/exclusion expressions; use baseline for regular queries

---

## Recommended Google ADK-Based DEO Agentic RAG Agent Architecture

### Core Design Principles

When splitting the DEO pipeline into ADK agents, two factors must be considered:

1. **Selective DEO application**: Applying optimization to every query adds unnecessary latency. Only queries with negation/exclusion should be routed through the DEO path
2. **Stage independence**: LLM decomposition, embedding optimization, and retrieval can each be cached/reused independently

### Recommended Agent Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                       │
│              (Root Agent - overall flow control)            │
│                                                             │
│  Receive user query → route → synthesize results → respond  │
└─────────┬───────────────────────────────────────┬───────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────┐              ┌─────────────────────────┐
│  Intent Classifier  │              │   Answer Generator      │
│  (Sub-Agent 1)      │              │   (Sub-Agent 5)         │
│                     │              │                         │
│  Determine if query │              │  Search results +       │
│  has negation/      │              │  original query         │
│  exclusion intent   │              │  → generate response    │
└─────────┬───────────┘              └─────────────────────────┘
          │
          ├── No negation ──→ Baseline Retrieval (simple embedding search)
          │
          ▼ Has negation
┌─────────────────────┐
│  Query Decomposer   │
│  (Sub-Agent 2)      │
│                     │
│  Decompose query    │
│  into positive/     │
│  negative sub-      │
│  queries via LLM    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Embedding Optimizer│
│  (Sub-Agent 3)      │
│                     │
│  Optimize query     │
│  embedding via      │
│  contrastive loss   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Retriever          │
│  (Sub-Agent 4)      │
│                     │
│  FAISS search +     │
│  result post-       │
│  processing/rerank  │
└─────────────────────┘
```

### Detailed Design for Each Agent

#### 1. Orchestrator Agent (Root)

The root agent that controls the overall pipeline.

```python
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

orchestrator_agent = Agent(
    name="deo_rag_orchestrator",
    model="gemini-2.0-flash",
    description="RAG orchestrator that recognizes negation/exclusion expressions and selects the appropriate retrieval strategy for accurate answers",
    instruction="""
    You are an orchestrator that analyzes user queries to select the optimal retrieval strategy.

    Processing flow:
    1. Use intent_classifier to determine if the query contains negation/exclusion intent
    2-A. No negation → request direct search from retriever with the original query
    2-B. Has negation → process through query_decomposer → embedding_optimizer → retriever
    3. Pass search results to answer_generator for final response generation
    """,
    sub_agents=[
        intent_classifier,
        query_decomposer,
        embedding_optimizer,
        retriever,
        answer_generator,
    ],
)
```

#### 2. Intent Classifier (Sub-Agent 1)

A **routing agent** that decides whether to apply DEO. This agent prevents unnecessary latency for regular queries.

```python
intent_classifier = Agent(
    name="intent_classifier",
    model="gemini-2.0-flash",
    description="Determines whether a query contains negation/exclusion intent",
    instruction="""
    Analyze the user query to determine whether it contains negation/exclusion intent.

    Negation/exclusion signals:
    - Explicit: "exclude", "without", "except", "not", "other than", "aside from"
    - Implicit: "not including", "everything but", "anything other than"

    Output format: {"has_negation": true/false, "negation_phrases": ["..."]}
    """,
    # No tools needed — LLM judgment alone is sufficient (lightweight task)
)
```

#### 3. Query Decomposer (Sub-Agent 2)

Corresponds to `PolarityLLM.expand()` in the current code.

```python
from google.adk.tools import FunctionTool

def decompose_query(query: str) -> dict:
    """Decomposes a query into positive/negative sub-queries."""
    # Wraps the existing llm.py logic as a Tool
    # Cache check → LLM call → JSON parsing
    from src.llm import PolarityLLM
    result = polarity_llm.expand(query, dataset="production")
    return result  # {"positives": [...], "negatives": [...]}

query_decomposer = Agent(
    name="query_decomposer",
    model="gemini-2.0-flash",
    description="Decomposes queries into positive/negative sub-queries",
    instruction="""
    Analyze the user query and decompose it into retrieval-inclusive intent (positive)
    and retrieval-exclusive intent (negative).

    Rules:
    - positive: semantically expand the query's core intent (no repeating the original)
    - negative: generate minimally, only for explicitly excluded items
    - no concept leakage between positive and negative
    """,
    tools=[FunctionTool(decompose_query)],
)
```

#### 4. Embedding Optimizer (Sub-Agent 3)

Corresponds to `OptimizedEmbedder.optimize_embedding()` in the current code. Since this involves **numerical computation** rather than LLM reasoning, it is implemented as a Tool.

```python
def optimize_query_embedding(
    query: str,
    positives: list[str],
    negatives: list[str],
    num_steps: int = 20,
    reg_weight: float = 0.2,
    pos_weight: float = 1.0,
    neg_weight: float = 1.0,
) -> str:
    """Optimizes query embedding via contrastive loss and returns a cache key."""
    # Wraps the existing embedder.py logic as a Tool
    optimized = embedder.optimize_embedding(
        query=query, positives=positives, negatives=negatives,
        num_steps=num_steps, reg_weight=reg_weight,
        pos_weight=pos_weight, neg_weight=neg_weight, ...
    )
    # Store optimized embedding in memory/cache and return key
    cache_key = store_embedding(query, optimized)
    return cache_key

embedding_optimizer = Agent(
    name="embedding_optimizer",
    model="gemini-2.0-flash",
    description="Contrastive loss-based query embedding optimization",
    instruction="""
    Given decomposed positive/negative sub-queries,
    call the optimize_query_embedding tool.

    Hyperparameter guide:
    - General negation queries: reg=0.2, pos=1.0, neg=1.0, steps=20
    - Strong exclusion needed: increase neg_weight to 1.5-2.0
    """,
    tools=[FunctionTool(optimize_query_embedding)],
)
```

#### 5. Retriever (Sub-Agent 4)

Corresponds to `CorpusIndex.search()` in the current code.

```python
def search_documents(
    query: str,
    use_optimized: bool = False,
    top_k: int = 10,
) -> list[dict]:
    """Searches for documents in the FAISS index."""
    if use_optimized:
        # Load optimized embedding from cache
        qvec = load_cached_embedding(query)
    else:
        # Encode original query as-is (baseline)
        qvec = embedder.encode(query, normalize=True).cpu().numpy()

    hits = indexer.search(qvec, top_k=top_k)
    return [{"doc_id": doc_id, "score": score, "text": corpus[doc_id]["text"]}
            for doc_id, score in hits]

retriever = Agent(
    name="retriever",
    model="gemini-2.0-flash",
    description="FAISS index-based document retrieval",
    instruction="""
    Use the search tool to retrieve relevant documents.
    - If DEO optimization was applied: use_optimized=True
    - For regular queries: use_optimized=False
    """,
    tools=[FunctionTool(search_documents)],
)
```

#### 6. Answer Generator (Sub-Agent 5)

Generates the final answer based on search results.

```python
answer_generator = Agent(
    name="answer_generator",
    model="gemini-2.0-flash",
    description="Synthesizes search results to generate answers to user questions",
    instruction="""
    Provide an accurate answer to the user's question based on the retrieved documents.

    Important:
    - If there were negation/exclusion conditions, verify that excluded items do not appear in the answer
    - Do not generate content that is not supported by the search results
    - Cite source documents
    """,
)
```

### Execution Flow Example

```
User: "Tell me about deep learning image classification techniques, but exclude CNN"

1. Orchestrator → Intent Classifier
   → {"has_negation": true, "negation_phrases": ["exclude CNN"]}

2. Orchestrator → Query Decomposer
   → {"positives": ["Vision Transformer-based image classification",
                     "MLP-Mixer image recognition techniques",
                     "latest trends in deep learning image classification"],
       "negatives": ["CNN", "convolutional neural network", "convnet"]}

3. Orchestrator → Embedding Optimizer
   → optimize_query_embedding(query, positives, negatives)
   → optimized embedding stored, cache_key returned

4. Orchestrator → Retriever
   → search_documents(query, use_optimized=True, top_k=10)
   → [{"doc_id": "doc_42", "score": 0.91, "text": "ViT is..."},
      {"doc_id": "doc_87", "score": 0.88, "text": "MLP-Mixer is..."},
      ...]   ← CNN-related documents demoted in ranking

5. Orchestrator → Answer Generator
   → generate final answer based on search results (verify CNN content excluded)
```

### Alternative Architecture: Simplified Version

If the number of agents feels excessive, a **3-agent structure** offers a simpler approach:

```
┌──────────────────────────┐
│   Orchestrator Agent     │
│   (routing + intent      │
│    classification)       │
└─────────┬────────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌────────────────────┐
│Baseline│  │  DEO Retriever     │
│Search  │  │  (decompose +      │
│Tool    │  │   optimize + search│
│        │  │   unified Tool)    │
└────────┘  └────────────────────┘
```

In this case, the entire DEO pipeline is bundled into a single `FunctionTool`:

```python
def deo_search(query: str, top_k: int = 10) -> list[dict]:
    """Runs the full DEO pipeline as a single Tool"""
    # 1) Decompose
    expansion = polarity_llm.expand(query)
    # 2) Optimize
    optimized_emb = embedder.optimize_embedding(
        query, expansion["positives"], expansion["negatives"], ...
    )
    # 3) Search
    qvec = optimized_emb.cpu().numpy().astype("float32")
    hits = indexer.search(qvec, top_k=top_k)
    return [{"doc_id": did, "score": s, "text": corpus[did]["text"]}
            for did, s in hits]
```

### Architecture Selection Guide

| Criteria | 5-Agent (Detailed) | 3-Agent (Simplified) |
|----------|--------------------|----------------------|
| **Debuggability** | Can inspect I/O at each stage | Internal process hidden in Tool |
| **Flexibility** | Agent can dynamically adjust hyperparameters | Fixed configuration only |
| **Latency** | LLM call overhead between agents | Minimal LLM calls |
| **Best for** | Complex queries, research/experimentation | Production, simple negation queries |

**Recommendation**: Start with the **3-agent simplified version** for production, and expand to 5 agents when query analysis or dynamic hyperparameter tuning becomes necessary.

---

## Additional Implementation Beyond the Paper

| Feature | Code | Description |
|---------|------|-------------|
| **Checkpointing/Caching** | `src/checkpoint.py` | Caches decomposition results, optimized embeddings, and progress for resume support |
| **Weight sweep** | `run_experiments.py:31-43` | Runs multiple weight combinations sequentially and outputs comparison tables |
| **Analysis mode** | `src/analysis.py:187-381` | Fine-grained evaluation by neg group/pos-only group, saves to JSON/CSV |
| **Optimization history visualization** | `src/analysis.py:116-184` | Visualizes loss trajectories with matplotlib |
| **Quick test mode** | `src/main.py:61-68` | Limits data and steps for rapid testing |

---

## Summary

This project faithfully implements the **text retrieval portion** of the DEO paper. All core components — (1) LLM-based query decomposition, (2) direct embedding optimization via contrastive loss, and (3) FAISS-based retrieval — are accurately implemented, with additional tooling for experiment reproduction including caching, weight sweep, and analysis utilities. However, the paper's **multimodal (CLIP/COCO-Neg) experiments** are not included in this codebase.
