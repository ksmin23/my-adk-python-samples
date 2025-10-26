#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from google.adk.cli import cli_tools_click
from google.adk.cli.service_registry import get_service_registry
from google.adk_community.sessions import redis_session_service


def redis_session_service_factory(uri: str, **kwargs):
  """Factory for creating a RedisSessionService."""
  kwargs_copy = kwargs.copy()
  kwargs_copy.pop("agents_dir", None)
  return redis_session_service.RedisSessionService(uri=uri, **kwargs_copy)


"""Registers custom services with the ADK global registry."""
registry = get_service_registry()
registry.register_session_service("redis", redis_session_service_factory)


if __name__ == '__main__':
  cli_tools_click.main()