#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import io
import logging
import os

from google import genai
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools import (
    AgentTool,
    BaseTool,
    ToolContext,
    google_search,  # built-in Google Search tool
)
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = os.getenv("MODEL", "gemini-2.5-flash")
STORE_NAME = os.getenv("STORE_NAME") 
logger.info(f"Using model: {model}, Store: {STORE_NAME}")

# Note: file_search_stores is currently exclusive to the Gemini Developer API.
# Initializing with vertexai=True will cause store management to fail.
genai_client = genai.Client()

# Max file size information: https://ai.google.dev/gemini-api/docs/file-search#limitations
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit for Gemini File Search direct upload


def get_store_name(display_name: str) -> str | None:
    """Resolve display name to resource name."""
    if not display_name:
        return None
    try:
        for store in genai_client.file_search_stores.list():
            if store.display_name == display_name:
                return store.name
    except Exception as e:
        logger.error(f"Error resolving store name: {e}")
    return None


# Resolve the store name at startup
RESOLVED_STORE_NAME = get_store_name(STORE_NAME)
if not RESOLVED_STORE_NAME:
    logger.warning(f"RagInitialization: Could not resolve store name for '{STORE_NAME}'. RAG features may fail.")
else:
    logger.info(f"RagInitialization: Successfully resolved '{STORE_NAME}' to '{RESOLVED_STORE_NAME}'")

"""
Note: Sub-agents are wrapped in 'AgentTool' and passed via the 'tools' parameter rather
than the 'sub_agents' list. This is a required workaround in the ADK to support the use
of built-in tools (like google_search) within the agent hierarchy, which avoids the
"Tool use with function calling is unsupported" error. This is the "Agent-as-a-Tool"
pattern.
"""

class RagAutoIngestor(BaseTool):
    """
    Middleware tool that automatically fixes MIME types and uploads attached 
    files to a File Search Store with session-based isolation (Strategy B).
    """

    def __init__(self, store_name: str):
        super().__init__(
            name="rag_auto_ingestor", description="Internal RAG auto-ingestion hook."
        )
        self.store_name = store_name
        logger.info(f"RagAutoIngestor: Initialized with store: {self.store_name}")

    def _guess_mime_type_from_bytes(self, data: bytes) -> str:
        if data.startswith(b"%PDF"):
            return "application/pdf"
        elif data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif data.startswith(b"GIF8"):
            return "image/gif"
        elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        return "text/plain"

    async def process_llm_request(
        self, *, tool_context: ToolContext, llm_request: LlmRequest
    ) -> None:
        logger.debug(f"RagAutoIngestor: process_llm_request called")
        logger.debug(f"RagAutoIngestor: llm_request: {llm_request}")

        invocation_context = getattr(tool_context, "_invocation_context", None)
        logger.debug(f"RagAutoIngestor: invocation_context: {invocation_context}")
        if not invocation_context:
            return

        session_id = invocation_context.session.id
        user_id = invocation_context.session.user_id

        # Save session_id to state for cross-agent synchronization (sync with sub-agents)
        tool_context.state['root_session_id'] = session_id
        tool_context.state['root_user_id'] = user_id

        # 1. Patch MIME types and Detect New Uploads
        parts_to_fix = []
        skipped_files = []
        if llm_request.contents:
            # 1. Detect New Uploads (Only check the latest content to avoid re-ingesting history)
            content = llm_request.contents[-1]
            logger.debug(f"RagAutoIngestor: checking latest content (role: {content.role})")
            
            # We only care about user uploads in the current turn
            if content.role == "user" or not content.role:
                for part in content.parts:
                    if part.inline_data:
                        # 1. Always ensure MIME type is present (Fix for 400 error)
                        if not part.inline_data.mime_type:
                            part.inline_data.mime_type = self._guess_mime_type_from_bytes(
                                part.inline_data.data
                            )
                            logger.info(f"RagAutoIngestor: Guessed MIME type: {part.inline_data.mime_type}")

                        # 2. Defense: Check file size limit (100MB)
                        data_size = len(part.inline_data.data)
                        if data_size > MAX_FILE_SIZE:
                            # Robust filename retrieval for warning
                            filename = (content.metadata.get("filename") if hasattr(content, "metadata") and content.metadata else None)
                            filename = filename or getattr(part, "name", None) or getattr(part.inline_data, "display_name", None) or getattr(part, "metadata", {}).get("filename") or "an unnamed file"
                            
                            logger.error(
                                f"RagAutoIngestor: File size ({data_size} bytes) exceeds the 100MB limit for Gemini File Search. Skipping ingestion."
                            )
                            skipped_files.append(f"'{filename}' ({data_size} bytes)")
                            continue

                        logger.info(f"RagAutoIngestor: Found inline_data (size: {data_size}) for ingestion")
                        parts_to_fix.append(part)
        else:
            logger.debug("RagAutoIngestor: No contents found in llm_request")

        # Surfacing: If files were skipped, add a system instruction to notify the user
        if skipped_files:
            warning_msg = (
                f"\n[IMPORTANT SYSTEM ALERT: FILE SKIPPED] The following user-uploaded files were NOT ingested into your internal knowledge base because they exceed the 100MB limit for 'file_search': "
                f"{', '.join(skipped_files)}. \n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. If the user asks about these specific files or their content, you MUST inform them that they were NOT ingested and cannot be searched.\n"
                "2. Do NOT try to use 'RagAgent' to search for information from these skipped files.\n"
                "3. You may proceed with 'RagAgent' only for other valid knowledge base information or use 'SearchAgent' for general knowledge, but ALWAYS acknowledge the skip if relevant."
            )
            # Use ADK's append_instructions for maximum priority and persistence in history
            llm_request.append_instructions([warning_msg])
            logger.info("RagAutoIngestor: Appended system instruction to the prompt.")

        # 2. Patch History
        events = invocation_context._get_events(current_invocation=True)
        for event in events:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if part.inline_data and not part.inline_data.mime_type:
                        part.inline_data.mime_type = self._guess_mime_type_from_bytes(
                            part.inline_data.data
                        )

        # 3. Auto-Ingestion to RAG Store (Strategy B)
        # We only upload if the store is resolved and we found inline_data in the current prompt
        if self.store_name and parts_to_fix:
            for part in parts_to_fix:
                try:
                    logger.info(f"RagAutoIngestor: Starting upload to {self.store_name} for session {session_id}")
                    bytes_file = io.BytesIO(part.inline_data.data)
                    # Robust filename retrieval: ADK Web UI often puts filename in Content metadata or Part
                    filename = (content.metadata.get("filename") if hasattr(content, "metadata") and content.metadata else None)
                    filename = filename or getattr(part, "name", None) or getattr(part.inline_data, "display_name", None) or getattr(part, "metadata", {}).get("filename") or "auto_uploaded_file"
                    # Strategy B: Upload to Store
                    await genai_client.aio.file_search_stores.upload_to_file_search_store(
                        file_search_store_name=self.store_name,
                        file=bytes_file,
                        config=types.UploadToFileSearchStoreConfig(
                            mime_type=part.inline_data.mime_type,
                            display_name=filename,
                            custom_metadata=[
                                {"key": "session_id", "string_value": session_id},
                                {"key": "user_id", "string_value": user_id},
                                {"key": "filename", "string_value": filename}
                            ]
                        )
                    )
                    logger.info(f"RagAutoIngestor: Upload complete for session {session_id} (user: {user_id})")

                    # 4. Mask the data after successful upload (FORCE TOOL CALL)
                    # By removing binary data and adding text, the model loses direct access
                    # and must call RagAgent to search.
                    part.inline_data = None
                    part.text = f"[FILE ATTACHED AND INDEXED: '{filename}'. For information about its content, you MUST use the 'RagAgent' tool.]"
                except Exception as e:
                    logger.error(f"RagAutoIngestor: Failed to auto-ingest file: {e}")

        # Surfacing: Reinforce tool usage if files were uploaded
        if parts_to_fix:
            info_msg = (
                "\n[SYSTEM NOTIFICATION] New files were uploaded and indexed. "
                "The binary data in this turn has been replaced by placeholders to save context and force tool usage. "
                "ALWAYS use 'RagAgent' to retrieve details from these files."
            )
            llm_request.append_instructions([info_msg])


class FileSearchTool(BaseTool):
    """
    Custom ADK tool that enables Gemini File Search with session-based filtering.
    """

    def __init__(self, store_name: str):
        # We rename the tool to an internal name to avoid collision with Gemini's built-in 'file_search'.
        # This custom tool acts as a middleware to configure the built-in tool.
        super().__init__(name="internal_file_search_connector", description="Configurations for retrieval.")
        self.store_name = store_name
        logger.info(f"FileSearchTool: Initialized with store: {self.store_name}")

    async def process_llm_request(
        self, *, tool_context: ToolContext, llm_request: "LlmRequest"
    ) -> None:
        if not self.store_name:
            return

        invocation_context = getattr(tool_context, "_invocation_context", None)
        
        # Strategy: Use root_session_id from state if available (Sync across agents)
        # AgentTool automatically propagates parent state to child sessions.
        session_id = tool_context.state.get('root_session_id') or (invocation_context.session.id if invocation_context else "unknown")
        
        logger.info(f"FileSearchTool: Preparing search with session_id: {session_id}")

        llm_request.config = llm_request.config or types.GenerateContentConfig()
        llm_request.config.tools = llm_request.config.tools or []

        # Strategy B: Apply metadata_filter for the current session and user
        user_id = tool_context.state.get('root_user_id', "unknown")
        metadata_filter = f'session_id = "{session_id}" AND user_id = "{user_id}"'
        
        llm_request.config.tools.append(
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[self.store_name],
                    metadata_filter=metadata_filter
                )
            )
        )
        logger.info(f"FileSearchTool: Attached built-in file_search to store '{self.store_name}' with filter: {metadata_filter}")


# Specialized RagAgent for retrieval only
rag_agent = Agent(
    model=model,
    name="RagAgent",
    description="Agent specialized in searching the internal knowledge base",
    instruction="""You are a retrieval specialist. 
    Use the 'file_search' tool to find answers in the internal knowledge base based on the user's query.
    Return the information clearly and concisely.""",
    tools=[FileSearchTool(store_name=RESOLVED_STORE_NAME)],
)

search_agent = Agent(
    model=model,
    name="SearchAgent",
    description="Agent to perform Google Search",
    instruction="You're a specialist in Google Search. Only perform one search. Fail fast if no relevant results are found.",
    tools=[google_search],
)

root_agent = Agent(
    name="basic_agent_adk",
    description="Helpful AI assistant with automatic RAG ingestion.",
    model=Gemini(
        model=model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a helpful AI assistant. 

    1. RAG AUTO-INGESTION: If the user attaches a file, it is automatically processed via RagAutoIngestor.
    2. CHECK SYSTEM ALERTS: If you receive a [SYSTEM ALERT] about SKIPPED files (e.g., due to size limits), you MUST acknowledge this skip and inform the user.
    3. RETRIEVAL (RagAgent): Use 'RagAgent' for any question about attached files (look for [FILE ATTACHED] placeholders) or general internal knowledge. Do NOT search for skipped files in RagAgent.
    4. NO DIRECT READING: If you see a placeholder like [FILE ATTACHED AND INDEXED], it means the file content is NOT in your context. You MUST use 'RagAgent' to access it.
    5. FALLBACK (SearchAgent): If RagAgent doesn't provide the answer, use 'SearchAgent' for a Google search.
    6. FAIL FAST: If information is not found in either the knowledge base or Google Search, state that clearly in the requested language (English/Korean).""",
    # instruction="""You are a helpful AI assistant. 
    # 1. If the user attaches a file, it is automatically stored in your internal knowledge base via RagAutoIngestor.
    # 2. For any question about attached files or internal knowledge, use the 'RagAgent'.
    # 3. If the RagAgent doesn't provide the answer, use the 'SearchAgent' for a Google search.
    # 4. Provide answers in the requested language (English/Korean).
    # 5. FAIL FAST: If information is not found in either the knowledge base or Google Search, state that clearly.""",
    tools=[
        RagAutoIngestor(store_name=RESOLVED_STORE_NAME),
        AgentTool(agent=rag_agent),
        AgentTool(agent=search_agent),
    ],
)
