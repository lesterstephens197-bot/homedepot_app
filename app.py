import pandas as pd
import streamlit as st
from scraper import get_reviews

# 页面标题
st.title("Home Depot Review Analyzer")

# 输入框：获取用户输入的商品链接
url = st.text_input("请输入 Home Depot 产品链接")

# 点击按钮触发分析
if st.button("开始分析"):
    if not url.strip():
        st.warning("⚠️ 请先输入产品链接！")
    else:
        # 显示加载状态动画
        with st.spinner("正在爬取并分析评论，请稍候..."):
            try:
                reviews = get_reviews(url)
            except Exception as e:
                st.error(f"❌ 爬取数据时发生错误: {e}")
                reviews = None

        # 检查是否获取到数据
        if reviews is not None and len(reviews) > 0:
            df = pd.DataFrame(reviews)

            # 检查是否有 rating 列
            if "rating" in df.columns:
                st.subheader("Review Rating Distribution")

                # 统计各评分数量（5星到1星降序排序）
                rating_count = (
                    df["rating"].value_counts().sort_index(ascending=False)
                )

                # 展示柱状图与数据表格
                st.bar_chart(rating_count)
                st.dataframe(rating_count)
            else:
                st.error("⚠️ 获取到的评论数据格式不匹配，缺失 'rating' 字段。")
        else:
            st.warning("⚠️ 未能获取到评论数据，请检查链接是否正确。")