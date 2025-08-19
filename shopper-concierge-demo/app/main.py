#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import gradio as gr
import os
import pandas as pd
import vertexai
import uuid
import logging
from vertexai import agent_engines
from dotenv import load_dotenv

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# --- Vertex AI Agent Engine Configuration ---
# Get Vertex AI related information from environment variables
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")

# Check for required environment variables
if not all([PROJECT_ID, LOCATION, AGENT_ENGINE_ID]):
  raise ValueError(
    "Error: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and "
    "AGENT_ENGINE_ID environment variables must be set."
  )

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Load the deployed agent
try:
  remote_agent = agent_engines.get(AGENT_ENGINE_ID)
except Exception as e:
  raise RuntimeError(f"Failed to load Vertex AI Agent Engine: {e}")
# ------------------------------------

def query_vertex_agent(user_query, user_id, session_id):
  """Sends a query to the Vertex AI Agent Engine and parses the response."""
  logging.info(f"Querying Vertex AI agent for user '{user_id}' in session '{session_id}': '{user_query}'...")

  response_text = ""
  recommended_products = []

  # Use stream_query to receive responses in real-time
  for event in remote_agent.stream_query(
    user_id=user_id,
    session_id=session_id,
    message=user_query
  ):
    # Extract text response
    if event.get('content', {}).get('parts', [{}])[0].get('text'):
      response_text += event['content']['parts'][0]['text']

    # Extract recommended product information from the tool call result
    if 'content' in event and 'parts' in event['content']:
      for part in event['content']['parts']:
        if 'function_response' in part:
          function_response = part['function_response']
          # Check if the correct function was called
          if function_response.get('name') == 'find_shopping_items':
            try:
              # Extract the list of items from the response
              results = function_response.get('response', {}).get('result', [])
              recommended_products.extend(results)
            except Exception as e:
              logging.error(f"Error parsing items from function_response: {e}")

  logging.debug(f"Full response text: {response_text}")

  # Remove duplicate products based on ID
  unique_products = []
  seen_ids = set()
  for product in recommended_products:
    product_id = product.get('id')
    if product_id and product_id not in seen_ids:
      unique_products.append(product)
      seen_ids.add(product_id)

  logging.info(f"Recommended products: {len(unique_products)} items")

  return response_text, unique_products

def chat_with_agent(user_input, history, session_state):
  """
  Handles the conversation with the Vertex AI agent and returns the result.
  """
  history = history or []

  # Get user_id and session_id from the session state
  user_id = session_state.get("user_id")
  session_id = session_state.get("session_id")

  # If a session has not started, create a new one
  if not user_id:
    user_id = f"gradio_user_{uuid.uuid4()}"
    session_state["user_id"] = user_id
    logging.info(f"New user connected: {user_id}")

  if not session_id:
    session_id = remote_agent.create_session(user_id=user_id)["id"]
    session_state["session_id"] = session_id
    logging.info(f"New session created for user '{user_id}': {session_id}")

  # Call the Vertex AI agent
  response_output, _ = query_vertex_agent(user_input, user_id, session_id)

  # Add user input and the final response to the history
  history.append((user_input, response_output))

  return history, session_state

# Gradio UI Configuration
with gr.Blocks(theme=gr.themes.Soft(), title="AI Shopping Assistant") as demo:
  session_state = gr.State({})

  gr.Markdown(
    """
    # AI Shopping Assistant
    
    How can I help you? Feel free to ask about the products you're looking for.
    (e.g., "Recommend a light and long-lasting laptop")
    """
  )

  chatbot = gr.Chatbot(label="Chat")

  with gr.Row():
    txt = gr.Textbox(
      show_label=False,
      placeholder="Enter your question here...",
      container=False,
      scale=8
    )
    submit_btn = gr.Button("Send", variant="primary", scale=1)

  # Event Handlers
  txt.submit(
    chat_with_agent,
    [txt, chatbot, session_state],
    [chatbot, session_state]
  )
  submit_btn.click(
    chat_with_agent,
    [txt, chatbot, session_state],
    [chatbot, session_state]
  )

if __name__ == "__main__":
  logging.info(f"Connecting to Vertex AI Agent Engine: {AGENT_ENGINE_ID}")
  demo.launch(debug=True)
