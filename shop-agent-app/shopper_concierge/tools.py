#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import json
import requests
from typing import Any, Dict, List

def call_vector_search(url: str, query: str, rows: int | None = None) -> Dict | None:
  """
  Calls the Vector Search backend for querying.

  Args:
    url: The URL of the search endpoint.
    query: The query string.
    rows: The number of result rows to return. Defaults to None.

  Returns:
    The JSON response from the API, or None if an error occurs. The JSON
    response is expected to have a 'result' key, which contains a list of
    item objects. Each item object includes details such as 'id', 'name',
    'description', 'img_url', and various search relevance scores.
  """
  # Build HTTP headers and a payload
  headers = {"Content-Type": "application/json"}
  payload = {
    "query": query,
    "rows": rows,
    "dataset_id": "mercari3m_mm",  # Use Mercari 3M multimodal index
    "use_dense": True,  # Use multimodal search
    "use_sparse": True,  # Use keyword search too
    "rrf_alpha": 0.5,  # Both results are merged with the same weights
    "use_rerank": True,  # Use Ranking API for reranking
  }

  # Send an HTTP request to the search endpoint
  try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()  # Raise an exception for bad status codes
    return response.json()
  except requests.exceptions.RequestException as e:
    print(f"Error calling the API: {e}")
    return None


def find_shopping_items(queries: List[str]) -> List[Dict[str, Any]]:
  """
  Find shopping items from the e-commerce site with the specified list of
  queries. This function calls a Vector Search backend to find items.

  Args:
    queries: the list of queries to run.
  Returns:
    A list of item objects found on the e-commerce site. Each object is a
    dictionary containing details like 'id', 'name', 'description',
    and 'img_url'.
  """
  url = "https://www.ac0.cloudadvocacyorg.joonix.net/api/query"

  items = []
  for query in queries:
    result = call_vector_search(
      url=url,
      query=query,
      rows=3,
    )
    if result and "items" in result:
      items.extend(result["items"])

  print("-----")
  print(f"User queries: {queries}")
  print(f"Found: {len(items)} items")
  print("-----")

  return items