import json
import re
import requests
import streamlit as st

st.set_page_config(
    page_title="Home Depot 评论星级抓取工具", page_icon="🛍️", layout="centered"
)


def extract_item_id(url: str) -> str:
    """从 Home Depot 的商品链接中提取 itemId/productId"""
    match = re.search(r"/(\d{8,10})(?:\?|\#|$)", url)
    if match:
        return match.group(1)
    return None


def fetch_bazaarvoice_data(item_id: str):
    """请求 Bazaarvoice API (针对 THD 的标准评价数据源)"""
    url = "https://api.bazaarvoice.com/data/batch.json"
    params = {
        "passkey": "ca3E98M1vS4N6oF1e5P5k349",
        "apiversion": "5.5",
        "displaycode": "1360-en_us",
        "resource.q0": "products",
        "filter.q0": f"id:{item_id}",
        "stats.q0": "reviews",
    }

    # 模拟真实浏览器 Header
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.homedepot.com/",
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code != 200:
            return None, f"HTTP Error {res.status_code}"

        data = res.json()
        results = (
            data.get("BatchedResults", {})
            .get("q0", {})
            .get("Results", [])
        )

        if not results:
            return None, "未找到该商品的评价数据"

        prod_info = results[0]
        review_stats = prod_info.get("ReviewStatistics", {})
        total_count = review_stats.get("TotalReviewCount", 0)

        # 提取 1-5 星分布
        rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        distribution = review_stats.get("RatingDistribution", [])

        for item in distribution:
            val = item.get("RatingValue")
            cnt = item.get("Count", 0)
            if val in rating_counts:
                rating_counts[val] = cnt

        return {"total": total_count, "ratings": rating_counts}, None

    except Exception as e:
        return None, str(e)


# --- UI 界面 ---
st.title("🛍️ Home Depot 评论星级抓取工具")
st.markdown("输入 Home Depot 商品链接，查询 1~5 星评论分布数据。")

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
            st.error("无法识别出有效的商品 ID，请检查链接格式是否包含数字 ID（如 336986711）。")
        else:
            with st.spinner("正在获取数据中..."):
                result, error = fetch_bazaarvoice_data(item_id)

                if error:
                    st.error(f"查询失败: {error}")
                elif result["total"] == 0:
                    st.info(f"解析成功（商品 ID: `{item_id}`），但 API 返回该商品**评论总数为 0**。请检查该商品在官网页面上是否真的有买家评价。")
                else:
                    st.success(f"解析成功！商品 ID: `{item_id}`")
                    st.metric("总评论数", f"{result['total']} 条")

                    st.subheader("📊 星级分布明细")

                    # 显示 5 列指标
                    cols = st.columns(5)
                    stars = [5, 4, 3, 2, 1]
                    for idx, star in enumerate(stars):
                        cols[idx].metric(f"{star} 星", f"{result['ratings'][star]} 条")

                    # 图表显示
                    chart_data = {
                        "星级": [f"{i} 星" for i in range(1, 6)],
                        "评论数": [result["ratings"][i] for i in range(1, 6)],
                    }
                    st.bar_chart(data=chart_data, x="星级", y="评论数")
