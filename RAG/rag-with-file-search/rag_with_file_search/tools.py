#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""
Note: Sub-agents are wrapped in 'AgentTool' and passed via the 'tools' parameter rather
than the 'sub_agents' list. This is a required workaround in the ADK to support the use
of built-in tools (like google_search) within the agent hierarchy, which avoids the
"Tool use with function calling is unsupported" error. This is the "Agent-as-a-Tool"
pattern.
"""

import io
import logging
from google.adk.tools import BaseTool, ToolContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types

logger = logging.getLogger(__name__)

# Max file size information: https://ai.google.dev/gemini-api/docs/file-search#limitations
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit for Gemini File Search direct upload

def get_store_name(genai_client, display_name: str) -> str | None:
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


class RagAutoIngestor(BaseTool):
    """
    Middleware tool that automatically fixes MIME types and uploads attached 
    files to a File Search Store with session-based isolation (Strategy B).
    """

    def __init__(self, genai_client, store_name: str):
        super().__init__(
            name="rag_auto_ingestor", description="Internal RAG auto-ingestion hook."
        )
        self.genai_client = genai_client
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
        content = None
        if llm_request.contents:
            # Detect New Uploads and Fix MIME types for ALL contents (History + Current Prompt)
            # This is critical because Gemini API validates the entire history.
            for i, content in enumerate(llm_request.contents):
                logger.debug(f"RagAutoIngestor: checking content {i} (role: {content.role})")
                
                # Patch MIME types for ANY content (user or model/assistant) that has inline_data
                for part in content.parts:
                    if part.inline_data:
                        # 1. Always ensure MIME type is present (Fix for 400 error)
                        if not part.inline_data.mime_type:
                            part.inline_data.mime_type = self._guess_mime_type_from_bytes(
                                part.inline_data.data
                            )
                            logger.info(f"RagAutoIngestor: Patched missing MIME type in content {i}: {part.inline_data.mime_type}")

                        # 2. Ingestion Logic (Only for the LATEST USER prompt)
                        if i == len(llm_request.contents) - 1 and (content.role == "user" or not content.role):
                            data_size = len(part.inline_data.data)
                            if data_size > MAX_FILE_SIZE:
                                # Robust filename retrieval
                                filename = (content.metadata.get("filename") if hasattr(content, "metadata") and content.metadata else None)
                                filename = filename or getattr(part, "name", None) or getattr(part.inline_data, "display_name", None) or getattr(part, "metadata", {}).get("filename") or "an unnamed file"
                                
                                logger.error(
                                    f"RagAutoIngestor: File size ({data_size} bytes) exceeds the 100MB limit. Skipping ingestion."
                                )
                                skipped_files.append(f"'{filename}' ({data_size} bytes)")
                                continue

                            logger.info(f"RagAutoIngestor: Found inline_data (size: {data_size}) for ingestion in latest prompt")
                            parts_to_fix.append(part)
        else:
            logger.debug("RagAutoIngestor: No contents found in llm_request")

        if skipped_files:
            warning_msg = (
                f"\n[IMPORTANT SYSTEM ALERT: FILE SKIPPED] The following user-uploaded files were NOT ingested: "
                f"{', '.join(skipped_files)}. \n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. If the user asks about these specific files or their content, you MUST inform them that they were NOT ingested.\n"
                "2. Do NOT try to use 'RagAgent' for these skipped files.\n"
            )
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

        # 3. Auto-Ingestion to RAG Store
        if self.store_name and parts_to_fix:
            for part in parts_to_fix:
                try:
                    bytes_file = io.BytesIO(part.inline_data.data)

                    # Robust filename retrieval
                    latest_content = llm_request.contents[-1]
                    filename = (latest_content.metadata.get("filename") if latest_content and hasattr(latest_content, "metadata") and latest_content.metadata else None)
                    filename = filename or getattr(part, "name", None) or getattr(part.inline_data, "display_name", None) or getattr(part, "metadata", {}).get("filename") or "auto_uploaded_file"
                    
                    await self.genai_client.aio.file_search_stores.upload_to_file_search_store(
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

    async def process_llm_request(
        self, *, tool_context: ToolContext, llm_request: LlmRequest
    ) -> None:
        if not self.store_name:
            return

        invocation_context = getattr(tool_context, "_invocation_context", None)

        # Strategy: Use root_session_id from state if available (Sync across agents)
        # AgentTool automatically propagates parent state to child sessions.
        session_id = tool_context.state.get('root_session_id') or (invocation_context.session.id if invocation_context else "unknown")
        user_id = tool_context.state.get('root_user_id', "unknown")
        
        llm_request.config = llm_request.config or types.GenerateContentConfig()
        llm_request.config.tools = llm_request.config.tools or []

        # Strategy: Apply metadata_filter for the current session and user
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
