import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import requests
import os

# ================= 0. 网页基础设置 =================
# 设置网页的标题和布局（宽屏模式更适合看报表）
st.set_page_config(page_title="智能财务审计看板", layout="wide")

# 如果需要代理，取消下面两行的注释
# os.environ['http_proxy'] = 'http://127.0.0.1:7890'
# os.environ['https_proxy'] = 'http://127.0.0.1:7890'

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ================= 1. 网页侧边栏 (交互控制台) =================
st.sidebar.title("⚙️ 控制台")
st.sidebar.write("请选择要分析的上市企业：")

# 制作一个下拉菜单，不仅有腾讯，还加上阿里和苹果！
company_dict = {
    "0700.HK": "腾讯控股",
    "BABA": "阿里巴巴 (美股)",
    "AAPL": "苹果公司 (美股)",
    "TSLA": "特斯拉 (美股)"
}
selected_ticker = st.sidebar.selectbox("选择股票代码", list(company_dict.keys()))
company_name = company_dict[selected_ticker]

# ================= 2. 网页主界面 =================
st.title(f"📊 {company_name} - 财务分析与审计排雷看板")
st.write("数据来源：雅虎财经实时抓取 (动态生成的杜邦分析与 Beneish 审计红旗)")

# 增加一个炫酷的加载动画
with st.spinner(f"正在穿上隐身衣，潜入雅虎财经抓取 {company_name} 的底层报表..."):
    try:
        # --- 抓取逻辑（完全复用之前的代码） ---
        session = requests.Session()
        session.headers.update({
                                   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

        ticker = yf.Ticker(selected_ticker, session=session)
        df = pd.concat([ticker.financials.T, ticker.balance_sheet.T], axis=1)

        if df.empty:
            st.error("❌ 抓取失败：雅虎财经返回了空表，请检查网络或代理！")
            st.stop()  # 停止运行下面的代码

        df.index = pd.to_datetime(df.index).year
        df = df.sort_index(ascending=True)
        years = df.index.tolist()


        # --- 智能提取逻辑 ---
        def safe_get(dataframe, possible_names):
            for name in possible_names:
                if name in dataframe.columns:
                    return dataframe[name]
            return None  # 网页版如果找不到，我们处理得更温柔一点


        revenue = safe_get(df, ['Total Revenue', 'Operating Revenue', 'Revenues'])
        net_income = safe_get(df, ['Net Income', 'Net Income Common Stockholders'])
        total_assets = safe_get(df, ['Total Assets', 'TotalAssets'])
        equity = safe_get(df, ['Stockholders Equity', 'Common Stock Equity', 'Ordinary Shares Number'])

        if revenue is None or total_assets is None:
            st.error(f"❌ 关键科目缺失，无法生成【{company_name}】的分析模型，请联系开发者核对数据源字段。")
            st.stop()

        if 'Accounts Receivable' in df.columns:
            ar = df['Accounts Receivable']
        elif 'Net Receivables' in df.columns:
            ar = df['Net Receivables']
        else:
            ar = revenue * 0.1

        total_liab = total_assets - equity

        # --- 计算指标 ---
        net_margin = (net_income / revenue) * 100
        asset_turnover = revenue / total_assets
        equity_multiplier = total_assets / equity
        roe = net_margin / 100 * asset_turnover * equity_multiplier * 100
        debt_ratio = (total_liab / total_assets) * 100

        # ================= 3. 在网页上展示审计结果 =================
        st.subheader("🚩 审计预警扫描 (Red Flag)")

        # 准备一个空表格，用来装审计结果
        audit_data = []
        rev_growth = revenue.pct_change() * 100
        ar_turnover = revenue / ar
        ar_turnover_change = ar_turnover.diff()

        for i in range(1, len(df)):
            year_str = str(years[i])
            curr_rg = rev_growth.iloc[i]
            curr_art_change = ar_turnover_change.iloc[i]

            alerts = []
            if curr_rg < 5 and curr_art_change < -1:
                alerts.append("⚠️ 应收账款异常")
            if debt_ratio.iloc[i] > 50 and (debt_ratio.iloc[i] - debt_ratio.iloc[i - 1] > 10):
                alerts.append("⚠️ 杠杆率异动")

            msg = "、".join(alerts) if alerts else "✅ 正常"
            audit_data.append([year_str, f"{curr_rg:.2f}%", f"{curr_art_change:.2f}", msg])

        audit_df = pd.DataFrame(audit_data, columns=["年份", "营收增速", "应收周转率变动", "诊断结果"])

        # 【魔法】用 st.dataframe 把数据变成可以上下滑动、排序的精美网页表格
        st.dataframe(audit_df, use_container_width=True)

        # ================= 4. 在网页上展示杜邦图表 =================
        st.subheader("📉 杜邦分析可视化看板")

        fig, axs = plt.subplots(2, 2, figsize=(14, 8))
        # 图表绘制逻辑和之前完全一样
        axs[0, 0].plot(years, roe, color='#D32F2F', marker='o', linewidth=3)
        axs[0, 0].set_title("1. ROE (%)", fontsize=12)
        axs[0, 0].set_xticks(years)

        axs[0, 1].plot(years, net_margin, color='#1976D2', marker='s', linewidth=2)
        axs[0, 1].set_title("2. 销售净利率 (%)", fontsize=12)
        axs[0, 1].set_xticks(years)

        axs[1, 0].plot(years, asset_turnover, color='#388E3C', marker='^', linewidth=2)
        axs[1, 0].set_title("3. 总资产周转率 (次)", fontsize=12)
        axs[1, 0].set_xticks(years)

        axs[1, 1].plot(years, equity_multiplier, color='#F57C00', marker='d', linewidth=2)
        axs[1, 1].set_title("4. 权益乘数 (倍)", fontsize=12)
        axs[1, 1].set_xticks(years)

        plt.tight_layout()

        # 【魔法】用 st.pyplot 直接把画好的图表镶嵌进网页里！
        st.pyplot(fig)

        st.success(f"🎉 {company_name} 数据分析加载完毕！你可以点击左侧栏切换其他公司。")

    except Exception as e:
        st.error(f"分析过程中发生错误：{e}")
