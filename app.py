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


def fetch_via_thd_graphql(item_id: str):
    """方法 1：通过 Home Depot 官方 GraphQL 获取评价数据"""
    url = "https://www.homedepot.com/graphql"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
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
        response = requests.post(
            url,
            json={"query": query, "variables": {"itemId": item_id}},
            headers=headers,
            timeout=8,
        )
        if response.status_code == 200:
            data = response.json()
            product = data.get("data", {}).get("product")
            if not product:
                return None, "GraphQL 接口中未查询到此商品（可能商品 ID 无效或已下架）"

            agg = (
                product.get("reviews", {})
                .get("ratingsReviews", {})
                .get("aggregate", {})
            )
            total = agg.get("reviewCount", 0)
            dist_list = agg.get("ratingDistribution") or []

            rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            for item in dist_list:
                r = item.get("rating")
                c = item.get("count", 0)
                if r in rating_counts:
                    rating_counts[r] = c

            return {"total": total, "ratings": rating_counts}, None
    except Exception as e:
        return None, f"GraphQL 请求异常: {e}"

    return None, "GraphQL 查询失败"


def fetch_via_bazaarvoice(item_id: str):
    """方法 2：通过 Bazaarvoice API 获取评价数据（备用）"""
    url = "https://api.bazaarvoice.com/data/batch.json"
    params = {
        "passkey": "ca3E98M1vS4N6oF1e5P5k349",
        "apiversion": "5.5",
        "displaycode": "1360-en_us",
        "resource.q0": "products",
        "filter.q0": f"id:{item_id}",
        "stats.q0": "reviews",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.homedepot.com/",
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            results = (
                data.get("BatchedResults", {})
                .get("q0", {})
                .get("Results", [])
            )
            if results:
                review_stats = results[0].get("ReviewStatistics", {})
                total = review_stats.get("TotalReviewCount", 0)
                rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
                for dist in review_stats.get("RatingDistribution", []):
                    val = dist.get("RatingValue")
                    cnt = dist.get("Count", 0)
                    if val in rating_counts:
                        rating_counts[val] = cnt
                return {"total": total, "ratings": rating_counts}, None
    except Exception as e:
        return None, f"Bazaarvoice 请求异常: {e}"

    return None, "未找到数据"


# --- Streamlit UI ---
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
            st.error("无法提取商品 ID，请确认链接格式正确。")
        else:
            with st.spinner("正在查询数据中..."):
                # 优先尝试官方 GraphQL 接口
                data, err = fetch_via_thd_graphql(item_id)

                # 若 GraphQL 未查到，回退至 Bazaarvoice
                if not data:
                    data, err = fetch_via_bazaarvoice(item_id)

                if err and not data:
                    st.error(f"查询失败: {err}")
                elif data:
                    total = data["total"]
                    ratings = data["ratings"]

                    if total == 0:
                        st.info(f"解析成功！商品 ID: `{item_id}`，该商品当前**暂无任何买家评论 (0 条)**。")
                    else:
                        st.success(f"解析成功！商品 ID: `{item_id}`")
                        st.metric("总评论数", f"{total} 条")

                        st.subheader("📊 星级分布明细")

                        cols = st.columns(5)
                        stars = [5, 4, 3, 2, 1]
                        for idx, star in enumerate(stars):
                            cols[idx].metric(f"{star} 星", f"{ratings[star]} 条")

                        chart_data = {
                            "星级": [f"{i} 星" for i in range(1, 6)],
                            "评论数": [ratings[i] for i in range(1, 6)],
                        }
                        st.bar_chart(data=chart_data, x="星级", y="评论数")
