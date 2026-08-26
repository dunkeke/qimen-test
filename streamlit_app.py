"""八字、人生 K 线与奇门排盘的一体化 Streamlit 界面。"""

from datetime import date, datetime, time
import json
from pathlib import Path
import subprocess

import pandas as pd
import plotly.express as px
import streamlit as st

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


def render_palace(pan: dict) -> None:
    st.subheader("奇门九宫")
    for row_start in range(0, 9, 3):
        columns = st.columns(3)
        for column, gong in zip(columns, PALACE_ORDER[row_start:row_start + 3]):
            with column:
                mark = " · 值符" if pan.get("zhiFuGong") == gong else ""
                st.markdown(f"#### {PALACE_NAMES[gong]}{mark}")
                st.caption(
                    f"{pan.get('baShen', {}).get(gong, '—')} · "
                    f"{pan.get('jiuXing', {}).get(gong, '—')} · "
                    f"{pan.get('baMen', {}).get(gong, '—')}"
                )
                st.write(f"天盘 **{pan.get('tianPan', {}).get(gong, '—')}**　地盘 **{pan.get('diPan', {}).get(gong, '—')}**")


st.set_page_config(page_title="八字 · 人生 K 线 · 奇门", page_icon="☯", layout="wide")
st.title("☯ 八字 · 人生 K 线 · 奇门融合排盘")
st.caption("同一出生资料生成四柱、年度趋势与奇门九宫；年度点取每年生日正午的时家奇门盘。")

with st.sidebar:
    st.header("出生资料")
    birth_day = st.date_input("公历生日", value=date(1990, 1, 1), min_value=date(1901, 1, 1), max_value=date(2099, 12, 31))
    birth_time = st.time_input("出生时间", value=time(12, 0))
    location = st.text_input("地点", value="默认位置", help="目前作为排盘记录；尚未进行真太阳时换算。")
    purpose = st.selectbox("主题", ("综合", "事业", "财运", "感情", "健康"))
    start_year, end_year = st.slider("K 线年份", 1901, 2100, (birth_day.year, min(2100, birth_day.year + 60)))
    submitted = st.button("开始融合排盘", type="primary", use_container_width=True)

if submitted:
    birth = datetime.combine(birth_day, birth_time)
    payload = json.dumps({
        "birthDate": birth.isoformat(), "startYear": start_year, "endYear": end_year,
        "location": location, "purpose": purpose,
    }, ensure_ascii=False)
    try:
        with st.spinner("正在排盘…"):
            result = calculate(payload)
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        st.error(f"无法完成排盘：{error}")
        st.stop()

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

    render_palace(pan)
    st.info(result["disclaimer"])
else:
    st.info("请在左侧填写出生资料并点击“开始融合排盘”。")
