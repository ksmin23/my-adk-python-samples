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

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- Vertex AI Agent Engine 설정 ---
# 환경 변수에서 Vertex AI 관련 정보 가져오기
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")

# 필수 환경 변수 확인
if not all([PROJECT_ID, LOCATION, AGENT_ENGINE_ID]):
  raise ValueError(
    "Error: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and "
    "AGENT_ENGINE_ID environment variables must be set."
  )

# Vertex AI 초기화
vertexai.init(project=PROJECT_ID, location=LOCATION)

# 배포된 에이전트 로드
try:
  remote_agent = agent_engines.get(AGENT_ENGINE_ID)
except Exception as e:
  raise RuntimeError(f"Failed to load Vertex AI Agent Engine: {e}")
# ------------------------------------

def query_vertex_agent(user_query, user_id, session_id):
  """Vertex AI Agent Engine에 쿼리를 보내고 응답을 파싱하는 함수"""
  logging.info(f"Querying Vertex AI agent for user '{user_id}' in session '{session_id}': '{user_query}'...")

  response_text = ""
  recommended_products = []

  # stream_query를 사용하여 실시간으로 응답 받기
  for event in remote_agent.stream_query(
    user_id=user_id,
    session_id=session_id,
    message=user_query
  ):
    # 텍스트 응답 추출
    if event.get('content', {}).get('parts', [{}])[0].get('text'):
      response_text += event['content']['parts'][0]['text']

    # 도구 호출 결과에서 추천 상품 정보 추출
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

  # ID를 기준으로 중복 상품 제거
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
  사용자 입력에 대해 Vertex AI 에이전트와 대화하고 결과를 반환하는 함수
  """
  history = history or []

  # 세션 상태에서 user_id와 session_id 가져오기
  user_id = session_state.get("user_id")
  session_id = session_state.get("session_id")

  # 세션이 시작되지 않았다면 새로 생성
  if not user_id:
    user_id = f"gradio_user_{uuid.uuid4()}"
    session_state["user_id"] = user_id
    logging.info(f"New user connected: {user_id}")

  if not session_id:
    session_id = remote_agent.create_session(user_id=user_id)["id"]
    session_state["session_id"] = session_id
    logging.info(f"New session created for user '{user_id}': {session_id}")

  # Vertex AI 에이전트 호출
  response_output, recommended_products = query_vertex_agent(user_input, user_id, session_id)

  # 추천 상품이 있는 경우, 마크다운 형식으로 변환하여 답변에 추가
  if recommended_products:
    response_output += "\n\n--- \n**추천 상품:**"
    for product in recommended_products:
      product_name = product.get("name", "N/A")
      description = product.get("description", "No description available.")
      img_url = product.get("img_url")

      response_output += f"\n\n**{product_name}**\n"
      response_output += f"{description}\n"
      if img_url:
        # 마크다운 이미지 태그 추가
        response_output += f"![{product_name}]({img_url})\n"

  # 사용자 입력과 최종적으로 구성된 답변을 기록에 추가
  history.append((user_input, response_output))

  recommended_products_df = pd.DataFrame()
  if recommended_products:
    # API 응답에서 받은 상품 목록으로 데이터프레임 바로 생성
    recommended_products_df = pd.DataFrame(recommended_products)

  return history, recommended_products_df, session_state

# Gradio UI 구성
with gr.Blocks(theme=gr.themes.Soft(), title="AI Shopping Assistant") as demo:
  session_state = gr.State({})

  gr.Markdown(
    """
    # AI Shopping Assistant
    
    무엇을 도와드릴까요? 찾고 있는 상품에 대해 자유롭게 질문해주세요.
    (예: "가볍고 오래가는 노트북 추천해줘")
    """
  )

  chatbot = gr.Chatbot(label="채팅창")

  with gr.Row():
    txt = gr.Textbox(
      show_label=False,
      placeholder="궁금한 점을 입력하세요...",
      container=False,
      scale=8
    )
    submit_btn = gr.Button("전송", variant="primary", scale=1)

  gr.Markdown("### 추천 상품 목록")
  product_recommendations = gr.DataFrame(
    label="추천 상품"
  )

  # 이벤트 핸들러
  txt.submit(
    chat_with_agent,
    [txt, chatbot, session_state],
    [chatbot, product_recommendations, session_state]
  )
  submit_btn.click(
    chat_with_agent,
    [txt, chatbot, session_state],
    [chatbot, product_recommendations, session_state]
  )

if __name__ == "__main__":
  logging.info(f"Connecting to Vertex AI Agent Engine: {AGENT_ENGINE_ID}")
  demo.launch(debug=True)