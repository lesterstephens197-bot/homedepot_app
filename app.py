import re
import requests
import streamlit as st

# 页面基础配置
st.set_page_config(
    page_title="Home Depot 评论星级分析", page_icon="🛍️", layout="centered"
)


def extract_item_id(url: str) -> str:
    """从 Home Depot 的商品链接中提取 itemId/productId"""
    match = re.search(r"/(\d{8,10})(?:\?|\#|$)", url)
    if match:
        return match.group(1)
    return None


def fetch_thd_reviews(item_id: str):
    """通过 Bazaarvoice API 获取评论星级数据"""
    api_url = "https://api.bazaarvoice.com/data/batch.json"
    params = {
        "passkey": "ca3E98M1vS4N6oF1e5P5k349",  # THD 现用公共 Passkey
        "apiversion": "5.5",
        "displaycode": "1360-en_us",
        "resource.q0": "products",
        "filter.q0": f"id:{item_id}",
        "stats.q0": "reviews",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.homedepot.com/",
    }

    response = requests.get(api_url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    results = (
        data.get("BatchedResults", {}).get("q0", {}).get("Results", [{}])[0]
    )
    review_stats = (
        results.get("ReviewStatistics", {}).get("RatingDistribution", [])
    )
    total_reviews = results.get("ReviewStatistics", {}).get("TotalReviewCount", 0)

    rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for dist in review_stats:
        val = dist.get("RatingValue")
        count = dist.get("Count")
        if val in rating_counts:
            rating_counts[val] = count

    return total_reviews, rating_counts


# --- Streamlit UI 界面设计 ---
st.title("🛍️ Home Depot 评论星级抓取工具")
st.markdown("输入 Home Depot 商品链接，快速查询 1~5 星评论分布数据。")

# 文本输入框
target_url = st.text_input(
    "商品链接 (Product URL):",
    placeholder="https://www.homedepot.com/p/...",
)

if st.button("开始查询", type="primary"):
    if not target_url:
        st.warning("请先输入商品链接！")
    else:
        item_id = extract_item_id(target_url)

        if not item_id:
            st.error("未能识别出有效的商品 ID，请检查链接格式。")
        else:
            with st.spinner("正在获取数据中..."):
                try:
                    total_reviews, rating_counts = fetch_thd_reviews(item_id)

                    st.success(f"解析成功！商品 ID: `{item_id}`")

                    # 显示核心指标
                    st.metric("总评论数", f"{total_reviews} 条")

                    st.subheader("📊 星级分布明细")

                    # 指标卡片排列 (5列)
                    cols = st.columns(5)
                    stars = [5, 4, 3, 2, 1]
                    for idx, star in enumerate(stars):
                        cols[idx].metric(f"{star} 星", f"{rating_counts[star]} 条")

                    # 可视化柱状图
                    chart_data = {
                        "星级": [f"{i} 星" for i in range(1, 6)],
                        "评论数": [rating_counts[i] for i in range(1, 6)],
                    }
                    st.bar_chart(data=chart_data, x="星级", y="评论数")

                except Exception as e:
                    st.error(f"获取失败，请重试。错误信息: {e}")
