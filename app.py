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


def fetch_from_bazaarvoice(item_id: str):
    """方式一：通过 Bazaarvoice API 获取"""
    api_url = "https://api.bazaarvoice.com/data/batch.json"
    params = {
        "passkey": "ca3E98M1vS4N6oF1e5P5k349",
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

    res = requests.get(api_url, params=params, headers=headers, timeout=8)
    if res.status_code != 200:
        return None, None

    data = res.json()
    results = data.get("BatchedResults", {}).get("q0", {}).get("Results", [])
    if not results:
        return None, None

    prod_data = results[0]
    review_stats = prod_data.get("ReviewStatistics", {})
    total_reviews = review_stats.get("TotalReviewCount", 0)

    rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for dist in review_stats.get("RatingDistribution", []):
        val = dist.get("RatingValue")
        count = dist.get("Count")
        if val in rating_counts:
            rating_counts[val] = count

    return total_reviews, rating_counts


def fetch_from_thd_graphql(item_id: str):
    """方式二：备用 - 通过 Home Depot 官方 GraphQL 接口获取"""
    url = "https://www.homedepot.com/graphql"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "x-experience-name": "responsive",
    }
    query = """
    query GetProductReviews($itemId: String!) {
        product(itemId: $itemId) {
            reviews {
                ratingsReviews {
                    aggregate {
                        reviewCount
                        ratingDistribution {
                            rating
                            count
                        }
                    }
                }
            }
        }
    }
    """
    try:
        res = requests.post(
            url,
            json={"query": query, "variables": {"itemId": item_id}},
            headers=headers,
            timeout=8,
        )
        if res.status_code == 200:
            data = res.json()
            agg = (
                data.get("data", {})
                .get("product", {})
                .get("reviews", {})
                .get("ratingsReviews", {})
                .get("aggregate", {})
            )
            total = agg.get("reviewCount", 0)
            dist_list = agg.get("ratingDistribution", [])

            rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            for item in dist_list:
                r = item.get("rating")
                c = item.get("count", 0)
                if r in rating_counts:
                    rating_counts[r] = c

            return total, rating_counts
    except Exception:
        pass
    return None, None


# --- Streamlit UI 界面 ---
st.title("🛍️ Home Depot 评论星级抓取工具")
st.markdown("输入 Home Depot 商品链接，快速查询 1~5 星评论分布数据。")

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
            with st.spinner("正在查询数据中..."):
                # 先尝试 Bazaarvoice API
                total_reviews, rating_counts = fetch_from_bazaarvoice(item_id)

                # 如果 Bazaarvoice 未查到，尝试官方 GraphQL API
                if total_reviews is None:
                    total_reviews, rating_counts = fetch_from_thd_graphql(
                        item_id
                    )

                # 结果显示逻辑
                if total_reviews is None:
                    st.error("无法获取该商品数据，请确认链接是否正确。")
                elif total_reviews == 0:
                    st.info(
                        f"解析成功（商品 ID: `{item_id}`），但该商品当前**暂无任何买家评论**。"
                    )
                else:
                    st.success(f"解析成功！商品 ID: `{item_id}`")
                    st.metric("总评论数", f"{total_reviews} 条")

                    st.subheader("📊 星级分布明细")

                    cols = st.columns(5)
                    stars = [5, 4, 3, 2, 1]
                    for idx, star in enumerate(stars):
                        cols[idx].metric(
                            f"{star} 星", f"{rating_counts[star]} 条"
                        )

                    chart_data = {
                        "星级": [f"{i} 星" for i in range(1, 6)],
                        "评论数": [rating_counts[i] for i in range(1, 6)],
                    }
                    st.bar_chart(data=chart_data, x="星级", y="评论数")
