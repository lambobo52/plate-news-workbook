import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random

# ---------- 配置 ----------
# 板块列表（可根据需要增删，建议10-20个）
PLATES = [
    "GPU", "光模块", "有色", "贵金属", "人型机器人",
    "宏观", "AI", "半导体", "新能源", "消费电子",
    "医药", "金融"
]
NOTES_COL = "备注"          # 备注列名
RECENT_DAYS = 10            # 表格显示最近10天

# ---------- 模拟新闻生成（可替换为真实抓取函数） ----------
def fetch_mock_news(plate, date):
    """
    模拟抓取：根据板块返回最多5条新闻，每条新闻占一行。
    实际使用时，可替换为调用新闻API或爬虫的代码。
    """
    # 各板块的新闻池（示例）
    news_pool = {
        "GPU": [
            "NVIDIA发布新一代AI芯片B200",
            "AMD显卡驱动更新提升性能",
            "GPU市场供不应求，价格高位运行",
            "国产GPU取得突破性进展",
            "数据中心GPU需求激增"
        ],
        "光模块": [
            "800G光模块开始量产",
            "LightCounting上调市场预测",
            "相干光模块技术获得突破",
            "华为发布新型光模块解决方案",
            "光模块需求旺盛，订单排至Q3"
        ],
        "有色": [
            "铜价持续上涨，库存低位",
            "铝社会库存下降",
            "稀土政策或影响供应",
            "锌精矿加工费走低",
            "镍价受新能源需求支撑"
        ],
        "贵金属": [
            "美联储降息预期推高金价",
            "白银工业需求增加",
            "铂金价格触底反弹",
            "央行连续增持黄金",
            "地缘政治风险支撑金价"
        ],
        "人型机器人": [
            "特斯拉Optimus最新演示视频发布",
            "Figure AI获得大额融资",
            "国内人形机器人政策支持加码",
            "核心零部件国产化加速",
            "AI大模型赋能机器人智能化"
        ],
        "宏观": [
            "中国央行维持利率不变",
            "美国非农数据超预期",
            "欧元区经济景气指数回升",
            "CPI同比上涨，PPI降幅收窄",
            "PMI数据显示制造业扩张"
        ],
        "AI": [
            "OpenAI发布新模型GPT-5",
            "大模型应用落地加速",
            "AI监管政策全球讨论",
            "算力需求持续增长",
            "AI芯片竞争加剧"
        ],
        "半导体": [
            "存储芯片价格反弹",
            "先进制程产能紧张",
            "半导体设备订单增加",
            "国产替代进程加速",
            "台积电公布超预期营收"
        ],
        "新能源": [
            "光伏装机超预期",
            "锂电池价格趋稳",
            "新能源汽车销量环比增长",
            "风电招标量创新高",
            "储能政策利好频出"
        ],
        "消费电子": [
            "iPhone16发布在即",
            "华为折叠屏手机热销",
            "VR/AR新品密集发布",
            "PC市场复苏信号",
            "芯片库存调整接近尾声"
        ],
        "医药": [
            "创新药医保谈判落地",
            "CXO行业订单回暖",
            "医疗器械集采价格温和",
            "减肥药研发进展",
            "中药配方颗粒国标发布"
        ],
        "金融": [
            "券商并购传闻再起",
            "银行净息差企稳",
            "保险新业务价值增长",
            "金融科技监管定调",
            "跨境理财通优化"
        ]
    }
    default_news = ["板块暂无重要新闻", "市场关注度一般", "行业动态平淡"]
    pool = news_pool.get(plate, default_news)
    # 随机选取最多5条（不设固定种子，使每次刷新可能变化，模拟实时更新）
    k = min(5, len(pool))
    selected = random.sample(pool, k)
    return "\n".join(selected)

# ---------- 数据库操作 ----------
def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    # 动态构建列：date, 板块1, 板块2, ..., 备注
    cols = ', '.join([f'"{plate}" TEXT' for plate in PLATES] + [f'"{NOTES_COL}" TEXT'])
    c.execute(f'CREATE TABLE IF NOT EXISTS daily_news (date TEXT PRIMARY KEY, {cols})')
    conn.commit()
    conn.close()

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def get_recent_dates(days=RECENT_DAYS):
    """返回最近N天的日期字符串列表（含今天）"""
    today = datetime.now().date()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

def load_data():
    """从数据库加载最近RECENT_DAYS天的数据，返回DataFrame（索引为日期）"""
    conn = sqlite3.connect('daily_news.db')
    dates = get_recent_dates()
    placeholders = ','.join(['?'] * len(dates))
    # 安全拼接列名（PLATES为固定列表）
    cols = 'date, ' + ', '.join([f'"{plate}"' for plate in PLATES] + [f'"{NOTES_COL}"'])
    query = f'SELECT {cols} FROM daily_news WHERE date IN ({placeholders}) ORDER BY date DESC'
    df = pd.read_sql_query(query, conn, params=dates, index_col='date')
    conn.close()
    # 补全缺失日期（显示为全空行）
    df = df.reindex(dates)
    return df

def update_today_if_missing():
    """如果今天没有数据，则自动抓取新闻并插入"""
    today = get_today_str()
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    c.execute('SELECT date FROM daily_news WHERE date = ?', (today,))
    if c.fetchone() is None:
        # 生成各板块新闻
        news_values = [fetch_mock_news(plate, today) for plate in PLATES]
        notes = ""  # 初始备注为空
        cols = ','.join(['date'] + [f'"{plate}"' for plate in PLATES] + [f'"{NOTES_COL}"'])
        placeholders = ','.join(['?'] * (len(PLATES) + 2))
        c.execute(f'INSERT INTO daily_news ({cols}) VALUES ({placeholders})',
                  (today, *news_values, notes))
        conn.commit()
    conn.close()

def update_notes(edited_df):
    """将用户编辑的备注列保存到数据库"""
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    for date, row in edited_df.iterrows():
        notes = row[NOTES_COL]
        if pd.isna(notes):
            notes = None
        c.execute(f'UPDATE daily_news SET "{NOTES_COL}" = ? WHERE date = ?', (notes, date))
    conn.commit()
    conn.close()

def refresh_today_news():
    """重新抓取今天的新闻（保留原有备注）"""
    today = get_today_str()
    # 生成新新闻
    news_values = [fetch_mock_news(plate, today) for plate in PLATES]
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    # 获取当前备注（如果有）
    c.execute(f'SELECT "{NOTES_COL}" FROM daily_news WHERE date = ?', (today,))
    row = c.fetchone()
    notes = row[0] if row else ""
    # 使用 REPLACE 覆盖当天数据
    cols = ','.join(['date'] + [f'"{plate}"' for plate in PLATES] + [f'"{NOTES_COL}"'])
    placeholders = ','.join(['?'] * (len(PLATES) + 2))
    c.execute(f'REPLACE INTO daily_news ({cols}) VALUES ({placeholders})',
              (today, *news_values, notes))
    conn.commit()
    conn.close()

# ---------- Streamlit 界面 ----------
def main():
    st.set_page_config(page_title="板块财经新闻工作簿", layout="wide")
    st.title("📈 板块财经新闻工作簿")
    st.caption("自动抓取每日板块新闻（最多5条），支持添加个人备注")

    # 初始化数据库
    init_db()
    # 确保今天数据存在（自动填充）
    update_today_if_missing()

    # 加载初始数据到 session_state
    if "df" not in st.session_state:
        st.session_state.df = load_data()

    # 定义列配置（所有板块列只读，备注列可编辑）
    column_config = {
        "date": st.column_config.TextColumn("日期", disabled=True, width="small")
    }
    for plate in PLATES:
        column_config[plate] = st.column_config.TextColumn(
            plate, disabled=True, width="large", help="自动抓取的新闻（最多5条）"
        )
    column_config[NOTES_COL] = st.column_config.TextColumn(
        "备注", disabled=False, width="medium", help="输入您的观点（可换行）"
    )

    # 显示数据编辑器
    edited_df = st.data_editor(
        st.session_state.df,
        column_config=column_config,
        use_container_width=True,
        num_rows="fixed",        # 禁止增删行
        key="data_editor"
    )

    # 操作按钮区域
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 保存备注"):
            update_notes(edited_df)
            st.session_state.df = load_data()   # 重载数据（确保显示最新）
            st.rerun()
    with col2:
        if st.button("🔄 刷新今天新闻"):
            refresh_today_news()
            st.session_state.df = load_data()
            st.rerun()

    # 显示最近更新提示
    st.info(f"✅ 最近 {RECENT_DAYS} 天数据已加载。今日数据若不存在，系统已自动填充模拟新闻。")

if __name__ == "__main__":
    main()
