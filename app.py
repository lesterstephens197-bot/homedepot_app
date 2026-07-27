import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Home Depot SKU Daily Sales Analytics", layout="wide")

st.title("📦 Home Depot 产品 SKU 深度日均销量看板")

# 1. 侧边栏文件上传与设置
uploaded_file = st.sidebar.file_uploader("上传 Home Depot 销售报表 (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_file:
    # 读取数据
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # 规范化列名与类型 (适应 Supplier Hub / Analytics 常见导出格式)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Units Sold'] = pd.to_numeric(df['Units Sold'], errors='coerce').fillna(0)
    df['Net Sales'] = pd.to_numeric(df['Net Sales'], errors='coerce').fillna(0)
    
    # 库存列 (若无则默认为 1 以防报错)
    if 'OnHand Inventory' not in df.columns:
        df['OnHand Inventory'] = 1
        
    # 渠道列 (如 Online / In-Store)
    if 'Channel' not in df.columns:
        df['Channel'] = 'All Channels'

    # 2. SKU 选择器
    sku_list = df['SKU'].unique()
    selected_sku = st.sidebar.selectbox("选择产品 SKU / Internet #", sku_list)
    
    # 时间范围
    min_date, max_date = df['Date'].min(), df['Date'].max()
    date_range = st.sidebar.date_input("分析区间", [min_date, max_date])
    
    # 过滤单 SKU 数据
    sku_data = df[(df['SKU'] == selected_sku) & 
                   (df['Date'] >= pd.to_datetime(date_range[0])) & 
                   (df['Date'] <= pd.to_datetime(date_range[1]))].sort_values('Date')
    
    if not sku_data.empty:
        # 按日期汇总（防止同一天多条渠道记录）
        daily_summary = sku_data.groupby('Date').agg({
            'Units Sold': 'sum',
            'Net Sales': 'sum',
            'OnHand Inventory': 'sum'
        }).reset_index()

        # 计算不同情况下的日均
        total_days = (daily_summary['Date'].max() - daily_summary['Date'].min()).days + 1
        total_units = daily_summary['Units Sold'].sum()
        
        # 剔除库存为0且无销量的断货天数 (OOS)
        in_stock_days_df = daily_summary[(daily_summary['OnHand Inventory'] > 0) | (daily_summary['Units Sold'] > 0)]
        in_stock_days = len(in_stock_days_df)
        
        overall_avg = total_units / total_days if total_days > 0 else 0
        instock_avg = total_units / in_stock_days if in_stock_days > 0 else 0

        # 计算滑动平均
        daily_summary['7D_Avg'] = daily_summary['Units Sold'].rolling(7, min_periods=1).mean()
        daily_summary['14D_Avg'] = daily_summary['Units Sold'].rolling(14, min_periods=1).mean()
        daily_summary['30D_Avg'] = daily_summary['Units Sold'].rolling(30, min_periods=1).mean()

        # 3. 核心指标卡片
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("累计总销量", f"{int(total_units):,} 件")
        col2.metric("全时段日均 (Overall)", f"{overall_avg:.1f} 件/天")
        col3.metric("在售无断货日均 (In-Stock Avg)", f"{instock_avg:.1f} 件/天", 
                    delta=f"{instock_avg - overall_avg:+.1f} (剔除断货干扰)", delta_color="normal")
        col4.metric("近 14 日动销日均", f"{daily_summary['14D_Avg'].iloc[-1]:.1f} 件/天")

        st.divider()

        # 4. 图表展示：日销量 + 断货区间 + 趋势线
        st.subheader("📈 产品 SKU 日销量走势与断货诊断")
        
        fig = go.Figure()

        # 原始日销量柱状图
        fig.add_trace(go.Bar(
            x=daily_summary['Date'],
            y=daily_summary['Units Sold'],
            name='单日销量',
            marker_color='#94A3B8'
        ))

        # 14日移动平均线
        fig.add_trace(go.Scatter(
            x=daily_summary['Date'],
            y=daily_summary['14D_Avg'],
            name='14日移动平均 (14D Avg)',
            line=dict(color='#2563EB', width=3)
        ))

        # 30日移动平均线
        fig.add_trace(go.Scatter(
            x=daily_summary['Date'],
            y=daily_summary['30D_Avg'],
            name='30日趋势线 (30D Avg)',
            line=dict(color='#DC2626', width=2, dash='dash')
        ))

        fig.update_layout(
            hovermode="x unified",
            xaxis_title="日期",
            yaxis_title="销量 (Units)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # 5. 渠道拆分与排查
        if 'Channel' in sku_data.columns and len(sku_data['Channel'].unique()) > 1:
            st.subheader("🏬 渠道销量构成分析")
            channel_df = sku_data.groupby(['Channel'])['Units Sold'].sum().reset_index()
            fig_pie = px.pie(channel_df, values='Units Sold', names='Channel', hole=0.4, title="渠道销量占比")
            st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.warning("所选时间段内该 SKU 无销售记录。")
else:
    st.info("请从 Supplier Hub 导出包含 `Date`, `SKU`, `Units Sold` 的报表并在此上传。")
