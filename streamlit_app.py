"""八字、人生 K 线与奇门排盘的一体化 Streamlit 界面。"""

from datetime import date, datetime, time
from html import escape
import json
import os
from pathlib import Path
import subprocess

import pandas as pd
import plotly.express as px
import streamlit as st

from deepseek_client import interpret

ROOT = Path(__file__).resolve().parent
PALACE_ORDER = ("4", "9", "2", "3", "5", "7", "8", "1", "6")
PALACE_NAMES = {"1": "坎一", "2": "坤二", "3": "震三", "4": "巽四", "5": "中五", "6": "乾六", "7": "兑七", "8": "艮八", "9": "离九"}


@st.cache_resource(show_spinner=False)
def prepare_node_runtime() -> None:
    """Install locked Node dependencies when Streamlit Cloud checks out a clean repo."""
    probe = subprocess.run(
        ["node", "-e", "require('lunar-javascript')"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode == 0:
        return

    install = subprocess.run(
        ["npm", "ci", "--omit=dev", "--no-audit", "--no-fund"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if install.returncode:
        detail = install.stderr.strip().splitlines()[-1] if install.stderr.strip() else "未知错误"
        raise RuntimeError(f"Node 依赖安装失败：{detail}")


@st.cache_data(show_spinner=False)
def calculate(payload: str) -> dict:
    """Call the existing, tested Node calculation core and return JSON."""
    prepare_node_runtime()
    command = ["node", str(ROOT / "bin" / "chart.js"), payload]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "排盘程序执行失败")
    return json.loads(result.stdout)


def configured_api_key() -> str:
    """Read the key from Streamlit Secrets when present, otherwise the environment."""
    try:
        return st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
    except FileNotFoundError:
        return os.getenv("DEEPSEEK_API_KEY", "")


def render_palace(pan: dict) -> None:
    """Render a responsive Luoshu grid with visual hierarchy and chart markers."""
    st.subheader("奇门九宫盘")
    cards = []

    def palace_value(section: str, gong: str) -> str:
        return escape(str(pan.get(section, {}).get(gong) or "—"))

    for gong in PALACE_ORDER:
        flags = []
        if pan.get("zhiFuGong") == gong:
            flags.append("值符")
        if pan.get("zhiShiGong") == gong:
            flags.append("值使")
        if gong in pan.get("kongWangGong", []):
            flags.append("空亡")
        if str(pan.get("maStar", {}).get("gong")) == gong:
            flags.append("驿马")
        badges = "".join(f'<span class="qm-badge">{escape(flag)}</span>' for flag in flags)
        # Keep tags flush-left: indented HTML is interpreted as a Markdown code block.
        cards.append(
            f'<section class="qm-card"><header><b>{PALACE_NAMES[gong]}</b><span>{badges}</span></header>'
            f'<div class="qm-trio"><strong>{palace_value("baShen", gong)}</strong><strong>{palace_value("jiuXing", gong)}</strong><strong>{palace_value("baMen", gong)}</strong></div>'
            f'<div class="qm-stems"><span>天盘 <b>{palace_value("tianPan", gong)}</b></span><span>地盘 <b>{palace_value("diPan", gong)}</b></span><span>暗干 <b>{palace_value("anGan", gong)}</b></span></div></section>'
        )
    styles = """<style>
.qm-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem;margin-bottom:1rem}
.qm-card{border:1px solid rgba(128,128,128,.3);border-radius:12px;padding:.75rem;background:linear-gradient(145deg,rgba(255,180,60,.10),rgba(120,70,220,.06));min-height:130px}
.qm-card header{display:flex;justify-content:space-between;border-bottom:1px solid rgba(128,128,128,.22);padding-bottom:.4rem}.qm-badge{font-size:.68rem;background:#b54708;color:white;padding:.15rem .35rem;border-radius:99px;margin-left:.2rem}
.qm-trio,.qm-stems{display:flex;justify-content:space-between;gap:.3rem;margin-top:.8rem}.qm-trio strong{font-size:1.05rem}.qm-stems{font-size:.78rem;opacity:.82}
@media(max-width:640px){.qm-grid{gap:.3rem}.qm-card{padding:.45rem;min-height:115px}.qm-card header span{display:none}.qm-trio{flex-direction:column;margin-top:.4rem}.qm-trio strong{font-size:.8rem}.qm-stems{flex-direction:column;margin-top:.3rem}}
</style>"""
    # st.html is intended for HTML/CSS and avoids Markdown turning nested tags into text.
    st.html(styles + '<div class="qm-grid">' + "".join(cards) + "</div>")


st.set_page_config(page_title="八字 · 人生 K 线 · 奇门", page_icon="☯", layout="wide")
st.title("☯ 八字 · 人生 K 线 · 奇门融合排盘")
st.caption("同一出生资料生成四柱、年度趋势与奇门九宫；年度点取每年生日正午的时家奇门盘。")

with st.sidebar:
    st.header("出生资料")
    birth_day = st.date_input("公历生日", value=date(1990, 1, 1), min_value=date(1901, 1, 1), max_value=date(2099, 12, 31))
    birth_time = st.time_input("出生时间", value=time(12, 0))
    location = st.text_input("地点", value="默认位置", help="目前作为排盘记录；尚未进行真太阳时换算。")
    purpose = st.selectbox("主题", ("综合", "事业", "财运", "感情", "健康"))
    st.divider()
    st.header("占卦资料")
    query_day = st.date_input("占卦日期", value=date.today(), min_value=date(1901, 1, 1), max_value=date(2099, 12, 31))
    query_time = st.time_input("占卦时间", value=datetime.now().time().replace(second=0, microsecond=0))
    question = st.text_area("所问事项", placeholder="例如：未来三个月项目推进需要注意什么？")
    start_year, end_year = st.slider("K 线年份", 1901, 2100, (birth_day.year, min(2100, birth_day.year + 60)))
    submitted = st.button("开始融合排盘", type="primary", use_container_width=True)

if submitted:
    birth = datetime.combine(birth_day, birth_time)
    payload = json.dumps({
        "birthDate": birth.isoformat(), "startYear": start_year, "endYear": end_year,
        "location": location, "purpose": purpose, "queryDate": datetime.combine(query_day, query_time).isoformat(),
        "question": question,
    }, ensure_ascii=False)
    try:
        with st.spinner("正在排盘…"):
            result = calculate(payload)
            st.session_state["chart_result"] = result
            st.session_state.pop("ai_reading", None)
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        st.error(f"无法完成排盘：{error}")
        st.stop()

if "chart_result" in st.session_state:
    result = st.session_state["chart_result"]
    bazi = result["bazi"]
    pan = result["natal"]
    pillars = bazi["pillars"]
    st.subheader("八字命盘")
    cols = st.columns(5)
    for col, label, value in zip(cols[:4], ("年柱", "月柱", "日柱", "时柱"), (pillars["year"], pillars["month"], pillars["day"], pillars["time"])):
        col.metric(label, value)
    cols[4].metric("日主", f"{bazi['dayMaster']} · {bazi['dayElement']}")

    st.subheader("人生 K 线")
    frame = pd.DataFrame(result["points"])
    figure = px.line(frame, x="year", y="score", markers=True, range_y=(0, 100),
                     labels={"year": "年份", "score": "融合指数"}, custom_data=["age", "yearPillar", "relation", "juShu", "door", "star", "god"])
    figure.update_traces(hovertemplate="年份 %{x}（%{customdata[0]} 岁）<br>指数 %{y}<br>%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}<br>%{customdata[4]} · %{customdata[5]} · %{customdata[6]}<extra></extra>")
    figure.add_hline(y=50, line_dash="dot", opacity=0.4)
    st.plotly_chart(figure, use_container_width=True)
    with st.expander("查看年度明细"):
        st.dataframe(frame.rename(columns={"year": "年份", "age": "年龄", "score": "指数", "relation": "五行关系", "yearPillar": "流年", "juShu": "奇门局", "focusGong": "值符宫", "door": "门", "star": "星", "god": "神"}), use_container_width=True, hide_index=True)

    query_pan = result["queryPan"]
    st.divider()
    info_cols = st.columns(4)
    info_cols[0].metric("占卦时间", query_pan.get("basicInfo", {}).get("date", "—"))
    info_cols[1].metric("局数", query_pan.get("juShu", {}).get("fullName", "—"))
    info_cols[2].metric("值符", f"{query_pan.get('zhiFuXing', '—')} · {query_pan.get('zhiFuGong', '—')}宫")
    info_cols[3].metric("值使", f"{query_pan.get('zhiShiMen', '—')} · {query_pan.get('zhiShiGong', '—')}宫")
    if result.get("question"):
        st.markdown(f"**所问事项：** {escape(result['question'])}")
    render_palace(query_pan)

    st.subheader("DeepSeek AI 解读")
    secret_key = configured_api_key()
    api_key = st.text_input("DeepSeek API Key", value=secret_key, type="password", help="建议在 Streamlit Secrets 中配置；不会发送给奇门计算程序。")
    if st.button("生成 AI 解读", type="primary"):
        try:
            with st.spinner("DeepSeek 正在依据盘面分析…"):
                st.session_state["ai_reading"] = interpret(api_key, query_pan, result.get("question", ""))
        except (ValueError, RuntimeError) as error:
            st.error(str(error))
    if st.session_state.get("ai_reading"):
        st.markdown(st.session_state["ai_reading"])
    st.info(result["disclaimer"])
elif not submitted:
    st.info("请在左侧填写出生资料并点击“开始融合排盘”。")
