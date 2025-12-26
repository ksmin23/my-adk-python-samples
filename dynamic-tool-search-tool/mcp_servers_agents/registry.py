import inspect
from typing import Dict, List, Any
from rank_bm25 import BM25Okapi

class AdvancedToolRegistry:
  def __init__(self):
    self._tools: Dict[str, Any] = {}
    self._descriptions: List[str] = []
    self._tool_names: List[str] = []
    self._bm25 = None

  def register(self, tool: Any):
    """Registers an ADK BaseTool/MCPTool."""
    if hasattr(tool, 'name'):
      name = tool.name
      doc = getattr(tool, 'description', "") or ""
    else:
      name = tool.__name__
      doc = inspect.getdoc(tool) or ""
    
    # Index a combination of name and docstring for better retrieval
    description = f"{name} {doc}"
    self._tools[name] = tool
    self._tool_names.append(name)
    self._descriptions.append(description)
    
    # Re-build the BM25 index
    tokenized_corpus = [desc.lower().split(" ") for desc in self._descriptions]
    self._bm25 = BM25Okapi(tokenized_corpus)

  def search(self, query: str, n: int = 5) -> List[str]:
    """Returns lightweight summaries (Name + Docstring snippet)."""
    if not self._bm25:
      return []
    tokenized_query = query.lower().split(" ")
    top_docs = self._bm25.get_top_n(tokenized_query, self._descriptions, n=n)
    results = []
    for doc in top_docs:
      idx = self._descriptions.index(doc)
      name = self._tool_names[idx]
      summary = doc.split('\n')[0][:150]
      results.append(f"{name}: {summary}")
    return results

  def get_tool(self, name: str) -> Any:
    return self._tools.get(name)

registry = AdvancedToolRegistry()
