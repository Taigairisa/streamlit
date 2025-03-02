import google.generativeai as genai
import streamlit as st
GEMINI_API_KEY = st.secrets.GEMINI_API.api_key

genai.configure(api_key=GEMINI_API_KEY)

# プロンプトの定義
prompt = "鯖の塩焼きの健康効果を教えてください。"

# モデルの選択とコンテンツの生成
model = genai.GenerativeModel("gemini-1.5-pro-002")
response = model.generate_content(prompt)

# レスポンスの表示
print(response.text)