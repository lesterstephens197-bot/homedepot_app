import streamlit as st
import requests
import pandas as pd
import re


st.set_page_config(
    page_title="THD Review Monitor",
    layout="wide"
)


st.title("🏠 Home Depot Review Rating Monitor")


# 输入链接
urls = st.text_area(
    "请输入THD产品链接（一行一个）",
    """
https://www.homedepot.com/p/example/322658301
"""
)


def get_omsid(url):

    """
    从THD链接提取OMS ID
    """

    match = re.search(r"/(\d+)$", url)

    if match:
        return match.group(1)

    return None



def get_reviews(omsid):

    """
    获取THD评论数据

    """

    api = "https://serpapi.com/search"


    params = {

        "engine":
        "home_depot_product_reviews",

        "product_id":
        omsid,

        "api_key":
        "你的SERPAPI_KEY"

    }


    response = requests.get(
        api,
        params=params
    )


    data=response.json()


    return data



def analyze_review(data):


    result={

        "5星":0,
        "4星":0,
        "3星":0,
        "2星":0,
        "1星":0,
        "总评论":0

    }


    if "ratings" in data:


        for item in data["ratings"]:

            star=item["stars"]

            count=item["count"]


            result[f"{star}星"]=count



    result["总评论"]=data.get(
        "total_review",
        0
    )


    return result



if st.button("开始分析"):


    output=[]


    for url in urls.split("\n"):


        url=url.strip()


        if not url:
            continue


        omsid=get_omsid(url)


        if omsid:


            data=get_reviews(
                omsid
            )


            result=analyze_review(
                data
            )


            result["OMSID"]=omsid


            output.append(result)



    df=pd.DataFrame(output)


    df=df[
        [
        "OMSID",
        "5星",
        "4星",
        "3星",
        "2星",
        "1星",
        "总评论"
        ]
    ]


    st.dataframe(
        df,
        use_container_width=True
    )


    csv=df.to_csv(
        index=False
    )


    st.download_button(
        "下载CSV",
        csv,
        "THD_review_report.csv",
        "text/csv"
    )