import streamlit as st

from kakeibo.db import connect_db, get_categories
from kakeibo.views.sidebar import render_sidebar
from kakeibo.pages import add_page, edit_page, categories_page, graphs_page, dev_page


def main():
    view_category = render_sidebar()

    engine = connect_db()
    main_categories, sub_categories = get_categories(engine)
    main_category = st.selectbox("カテゴリ", [cat[1] for cat in main_categories])
    main_category_id = next(cat[0] for cat in main_categories if cat[1] == main_category)

    if view_category == "追加":
        add_page.render(main_category_id, sub_categories)
    elif view_category == "編集":
        edit_page.render(main_category_id, sub_categories)
    elif view_category == "カテゴリー追加・編集":
        categories_page.render(main_category_id, sub_categories)
    elif view_category == "グラフ":
        graphs_page.render()
    elif view_category == "開発者オプション":
        dev_page.render()
    else:
        st.info("ページを選択してください")


if __name__ == "__main__":
    main()
