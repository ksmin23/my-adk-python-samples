#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
from google.adk.runtime import Runtime
from .agent import root_agent

def main():
  # ADK runtime to run the agent locally
  runtime = Runtime()
  
  print("="*50)
  print("AI Search Agent is ready!")
  print("Ask me anything with advanced filtering (e.g., site:..., filetype:...)")
  print("="*50)
  
  # Note: In a real app, you would use adk chat or a UI.
  # This main.py is for demonstration of programmatic invocation.
  response = root_agent.run("최근 1주일 내의 GCP 관련 뉴스 검색해줘 (site:cloud.google.com)")
  print(f"\n[Agent Response]:\n{response.text}")

if __name__ == "__main__":
  main()
