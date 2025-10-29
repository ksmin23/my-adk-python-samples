#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from urllib.parse import urlparse, parse_qs
from google.adk.cli import cli_tools_click
from google.adk.cli.service_registry import get_service_registry
from google.adk_community.sessions import redis_session_service
from google.adk_community.sessions import redis_session_service
from redis_memory_service.lib import redis_memory_service

def redis_session_service_factory(uri: str, **kwargs):
  """Factory for creating a RedisSessionService."""
  kwargs_copy = kwargs.copy()
  kwargs_copy.pop("agents_dir", None)
  return redis_session_service.RedisSessionService(uri=uri, **kwargs_copy)

def redis_memory_service_factory(uri: str, **kwargs):
  """Factory for creating a RedisMemoryService."""
  kwargs_copy = kwargs.copy()
  kwargs_copy.pop("agents_dir", None)
  parsed_uri = urlparse(uri)
  if parsed_uri.query:
    query_params = {
      k: v[0] for k, v in parse_qs(parsed_uri.query).items()
    }
    kwargs_copy.update(query_params)
  # Pass the URI without the query part to RedisMemoryService
  uri_without_query = parsed_uri._replace(query='').geturl()
  return redis_memory_service.RedisMemoryService(uri=uri_without_query, **kwargs_copy)

"""Registers custom services with the ADK global registry."""
registry = get_service_registry()
registry.register_session_service("redis", redis_session_service_factory)
registry.register_memory_service("redis", redis_memory_service_factory)

if __name__ == '__main__':
  cli_tools_click.main()