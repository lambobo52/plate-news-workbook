import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
from streamlit_autorefresh import st_autorefresh

# ---------- 配置 ----------
PLATES = [
    "GPU", "光模块", "有色", "贵金属", "人型机器人",
    "宏观", "AI", "半导体", "新能源", "消费电子",
    "医药", "金融"
]
NOTES_COL = "备注"
RECENT_DAYS = 10            # 显示最近10天

# ---------- 模拟新闻生成（带链接） ----------
def fetch_mock_news(plate, date):
    """返回最多5条新闻，每条新闻后附带一个模拟链接"""
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
    k = min(5, len(pool))
    selected = random.sample(pool, k)
    linked_news = []
    for news in selected:
        fake_id = random.randint(100000, 999999)
        linked_news.append(f"{news} (http://example.com/news/{fake_id})")
    return "\n".join(linked_news)

# ---------- 数据库操作 ----------
def init_db():
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    cols = ', '.join([f'"{plate}" TEXT' for plate in PLATES] + [f'"{NOTES_COL}" TEXT'])
    c.execute(f'CREATE TABLE IF NOT EXISTS daily_news (date TEXT PRIMARY KEY, {cols})')
    conn.commit()
    conn.close()

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def get_recent_dates(days=RECENT_DAYS):
    today = datetime.now().date()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

def ensure_dates_exist(dates):
    """确保指定日期列表中的每一天在数据库中都有记录（若无则插入）"""
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    for date in dates:
        c.execute('SELECT date FROM daily_news WHERE date = ?', (date,))
        if c.fetchone() is None:
            news_values = [fetch_mock_news(plate, date) for plate in PLATES]
            notes = ""
            cols = ','.join(['date'] + [f'"{plate}"' for plate in PLATES] + [f'"{NOTES_COL}"'])
            placeholders = ','.join(['?'] * (len(PLATES) + 2))
            c.execute(f'INSERT INTO daily_news ({cols}) VALUES ({placeholders})',
                      (date, *news_values, notes))
    conn.commit()
    conn.close()

def load_data():
    """加载最近RECENT_DAYS天的数据，并确保都有记录"""
    dates = get_recent_dates()
    ensure_dates_exist(dates)
    conn = sqlite3.connect('daily_news.db')
    cols = 'date, ' + ', '.join([f'"{plate}"' for plate in PLATES] + [f'"{NOTES_COL}"'])
    query = f'SELECT {cols} FROM daily_news WHERE date IN ({",".join(["?"]*len(dates))}) ORDER BY date DESC'
    df = pd.read_sql_query(query, conn, params=dates, index_col='date')
    conn.close()
    df = df.reindex(dates)
    return df

def update_notes(edited_df):
    """保存备注列"""
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
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    c.execute(f'SELECT "{NOTES_COL}" FROM daily_news WHERE date = ?', (today,))
    row = c.fetchone()
    notes = row[0] if row else ""
    news_values = [fetch_mock_news(plate, today) for plate in PLATES]
    cols = ','.join(['date'] + [f'"{plate}"' for plate in PLATES] + [f'"{NOTES_COL}"'])
    placeholders = ','.join(['?'] * (len(PLATES) + 2))
    c.execute(f'REPLACE INTO daily_news ({cols}) VALUES ({placeholders})',
              (today, *news_values, notes))
    conn.commit()
    conn.close()

def refresh_all_recent_news():
    """重新抓取最近RECENT_DAYS所有日期的新闻（保留备注）"""
    dates = get_recent_dates()
    conn = sqlite3.connect('daily_news.db')
    c = conn.cursor()
    for date in dates:
        c.execute(f'SELECT "{NOTES_COL}" FROM daily_news WHERE date = ?', (date,))
        row = c.fetchone()
        notes = row[0] if row else ""
        news_values = [fetch_mock_news(plate, date) for plate in PLATES]
        cols = ','.join(['date'] + [f'"{plate}"' for plate in PLATES] + [f'"{NOTES_COL}"'])
        placeholders = ','.join(['?'] * (len(PLATES) + 2))
        c.execute(f'REPLACE INTO daily_news ({cols}) VALUES ({placeholders})',
                  (date, *news_values, notes))
    conn.commit()
    conn.close()

# ---------- Streamlit 界面 ----------
def main():
    st.set_page_config(page_title="板块财经新闻工作簿", layout="wide")
    st.title("📈 板块财经新闻工作簿")
    st.caption("自动填充每日板块新闻（最多5条），新闻末尾附带模拟链接（可复制）。支持添加个人备注。")

    # --- 自定义CSS：让表格单元格高度自适应 ---
    st.markdown("""
    <style>
        /* 让data_editor单元格内容自动换行，高度自适应 */
        .stDataFrame td {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            line-height: 1.5 !important;
            height: auto !important;
            min-height: 2.5em !important;
        }
        /* 可选的，让表格列宽分配更合理 */
        .stDataFrame th, .stDataFrame td {
            text-align: left !important;
            vertical-align: top !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- 初始化数据库并确保最近日期有数据 ---
    init_db()
    ensure_dates_exist(get_recent_dates())

    # --- 实时刷新设置（侧边栏）---
    with st.sidebar:
        st.header("⏱️ 实时刷新")
        refresh_interval = st.number_input(
            "自动刷新间隔（秒，0=关闭）",
            min_value=0,
            max_value=3600,
            value=0,
            step=10,
            help="开启后，页面将按设定间隔自动抓取今天的新闻并更新表格。请注意：刷新时未保存的编辑可能丢失。"
        )
        if refresh_interval > 0:
            st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
            # 检查是否需要刷新今天新闻
            now = datetime.now()
            last_refresh = st.session_state.get("last_auto_refresh", None)
            if last_refresh is None or (now - last_refresh).total_seconds() >= refresh_interval:
                with st.spinner("正在刷新今日新闻..."):
                    refresh_today_news()
                    st.session_state.last_auto_refresh = now
                    # 重载数据到session_state
                    st.session_state.df = load_data()
        st.divider()
        st.info("💡 提示：新闻后的链接为模拟出处，可复制到浏览器访问。")

    # --- 加载数据到session_state（如果还没有）---
    if "df" not in st.session_state:
        st.session_state.df = load_data()

    # --- 列配置 ---
    column_config = {
        "date": st.column_config.TextColumn("日期", disabled=True, width="small")
    }
    for plate in PLATES:
        column_config[plate] = st.column_config.TextColumn(
            plate,
            disabled=True,
            width="large",          # 给新闻列较大宽度
            help="自动抓取的新闻（最多5条，含链接）"
        )
    column_config[NOTES_COL] = st.column_config.TextColumn(
        "备注",
        disabled=False,
        width="medium",
        help="输入您的观点（可换行）"
    )

    # --- 数据编辑器（表格）---
    edited_df = st.data_editor(
        st.session_state.df,
        column_config=column_config,
        width="stretch",            # 占满容器宽度
        num_rows="fixed",
        key="data_editor",
        height=600                  # 表格整体高度固定，内部滚动
    )

    # --- 操作按钮 ---
    col1, col2, col3 = st.columns([1, 1, 5])
    with col1:
        if st.button("💾 保存备注"):
            update_notes(edited_df)
            st.session_state.df = load_data()
            st.rerun()
    with col2:
        if st.button("🔄 刷新历史新闻"):
            refresh_all_recent_news()
            st.session_state.df = load_data()
            st.rerun()
    with col3:
        st.caption("刷新历史新闻将重新抓取最近10天所有新闻（保留备注），模拟链接会变化。")

    # --- 提示信息 ---
    st.info(f"✅ 最近 {RECENT_DAYS} 天数据已自动填充。新闻后的 (链接) 为模拟出处，可复制。")

if __name__ == "__main__":
    main()
