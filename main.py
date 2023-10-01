import streamlit as st
import numpy as np
import pandas as pd
import time

st.title("Streamlit 超入門")

st.write("DataFrame")

df = pd.DataFrame({
    "1列目": [1,2,3,4],
    "2列目": [10,20,30,40]
})

if st.checkbox("Show Image"):
    st.dataframe(df, width=100,height=400)
    st.line_chart(df)

text = st.text_input(
    "あなたが好きな数字を教えてください")

"あなたの好きな数字は、", text, "です"

date = st.date_input("日付")
st.sidebar.write("ウィジェット")
left_column, right_column = st.columns(2)
button = left_column.button("左カラム")
text1 = right_column.text_input("右カラム")
expander = st.expander("問い合わせ")
expander.write("問い合わせ内容を書く")

st.write("プログレスバー")
"start!!"
latest_iteration = st.empty()
bar = st.progress(0)
for i in range(100):
    latest_iteration.text(f"iteration{i+1}")
    bar.progress(i+1)
    time.sleep(0.1)

from PIL import Image
 
categories = ["給与", "二人で遊ぶお金", "食費/消耗品", "耐久消耗品", "お小遣い", "楽天証券前月比", "その他"]
with st.form("my_form", clear_on_submit=True):
    date = st.date_input("日付*")
    category = st.selectbox(label='カテゴリ', options=categories)
    description = st.text_area('詳細')
    income = st.text_input("収入")
    expense = st.text_input("支出")
    submitted = st.form_submit_button("送信")
     
     
if submitted:
    with st.spinner("画像生成中です..."):
        time.sleep(3)
    income = int(income)
    expense = int(expense)
    # image = Image.open('キングスライム.jpg')
    # st.subheader(name)
    # st.image(image)
    # st.text(description)  
    # st.text(series)