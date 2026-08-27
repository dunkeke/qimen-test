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
PALACE_META = {
    "1": {"direction": "正北", "element": "水"}, "2": {"direction": "西南", "element": "土"},
    "3": {"direction": "正东", "element": "木"}, "4": {"direction": "东南", "element": "木"},
    "5": {"direction": "中宫", "element": "土"}, "6": {"direction": "西北", "element": "金"},
    "7": {"direction": "正西", "element": "金"}, "8": {"direction": "东北", "element": "土"},
    "9": {"direction": "正南", "element": "火"},
}
HARM_CODES = {"空亡": "kong-wang", "门迫": "men-po", "击刑": "ji-xing", "入墓": "ru-mu"}


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
    """Render a responsive Luoshu grid with direct Four Harms annotations."""
    st.subheader("奇门九宫盘")
    cards = []
    harm_rows = []
    si_hai = pan.get("siHai", {})
    harms_by_palace = si_hai.get("byGong", {})
    summary = si_hai.get("summary", {})
    counts = summary.get("counts", {})

    def palace_value(section: str, gong: str) -> str:
        return escape(str(pan.get(section, {}).get(gong) or "—"))

    for gong in PALACE_ORDER:
        markers = []
        if pan.get("zhiFuGong") == gong:
            markers.append(("值符", "zhi-fu"))
        if pan.get("zhiShiGong") == gong:
            markers.append(("值使", "zhi-shi"))
        if str(pan.get("maStar", {}).get("gong")) == gong:
            markers.append(("驿马", "horse"))

        harms = harms_by_palace.get(gong, [])
        marker_badges = "".join(
            f'<span class="qm-marker qm-marker--{code}">{escape(label)}</span>'
            for label, code in markers
        )
        harm_badges = "".join(
            f'<span class="qm-harm qm-harm--{escape(harm.get("code", HARM_CODES.get(harm.get("type"), "generic")))}" '
            f'title="{escape(str(harm.get("reason", "")), quote=True)}">{escape(str(harm.get("type", "")))}</span>'
            for harm in harms
        )
        for harm in harms:
            harm_rows.append({
                "宫位": f"{PALACE_NAMES[gong]} · {PALACE_META[gong]['direction']}",
                "四害": harm.get("type", ""),
                "判定依据": harm.get("reason", ""),
            })

        risk_class = " qm-card--risk" if harms else ""
        stacked_class = " qm-card--stacked" if len(harms) > 1 else ""
        meta = PALACE_META[gong]
        harms_html = harm_badges or '<span class="qm-clear">四害未见</span>'
        # Keep tags flush-left: indented HTML is interpreted as a Markdown code block.
        cards.append(
            f'<section class="qm-card{risk_class}{stacked_class}"><header>'
            f'<span class="qm-palace"><b>{PALACE_NAMES[gong]}</b><small>{meta["direction"]} · {meta["element"]}</small></span>'
            f'<span class="qm-markers">{marker_badges}</span></header>'
            f'<div class="qm-roles"><span><small>神</small><b>{palace_value("baShen", gong)}</b></span>'
            f'<span><small>星</small><b>{palace_value("jiuXing", gong)}</b></span>'
            f'<span><small>门</small><b>{palace_value("baMen", gong)}</b></span></div>'
            f'<div class="qm-stems"><span><small>天盘</small><b>{palace_value("tianPan", gong)}</b></span>'
            f'<span><small>地盘</small><b>{palace_value("diPan", gong)}</b></span>'
            f'<span><small>暗干</small><b>{palace_value("anGan", gong)}</b></span></div>'
            f'<div class="qm-harms">{harms_html}</div></section>'
        )

    total = int(summary.get("total", sum(int(counts.get(name, 0)) for name in HARM_CODES)))
    affected = len(summary.get("affectedGongs", []))
    overview_items = "".join(
        f'<span class="qm-overview-item qm-overview-item--{code}"><b>{escape(name)}</b><em>{int(counts.get(name, 0))}</em></span>'
        for name, code in HARM_CODES.items()
    )
    overview = (
        f'<div class="qm-overview"><span class="qm-overview-lead"><small>本盘四害</small><b>{total}</b>'
        f'<em>{affected} 宫受影响</em></span>{overview_items}</div>'
    )
    styles = """<style>
.qm-overview{display:grid;grid-template-columns:1.35fr repeat(4,1fr);gap:.55rem;margin:.1rem 0 .8rem}
.qm-overview>span{display:flex;align-items:center;justify-content:space-between;gap:.45rem;border:1px solid rgba(128,128,128,.24);border-radius:12px;padding:.55rem .7rem;background:rgba(128,128,128,.055)}
.qm-overview-lead{background:linear-gradient(135deg,rgba(179,54,38,.15),rgba(222,158,44,.10))!important}.qm-overview small{font-weight:650}.qm-overview b{font-size:1.18rem}.qm-overview em{font-style:normal;font-size:.72rem;opacity:.68}.qm-overview-item--kong-wang{border-bottom:3px solid #71639a!important}.qm-overview-item--men-po{border-bottom:3px solid #d27b24!important}.qm-overview-item--ji-xing{border-bottom:3px solid #c44332!important}.qm-overview-item--ru-mu{border-bottom:3px solid #8a5b43!important}
.qm-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.62rem;margin-bottom:1rem}
.qm-card{position:relative;overflow:hidden;border:1px solid rgba(128,128,128,.26);border-radius:14px;padding:.72rem;background:linear-gradient(150deg,rgba(255,183,77,.08),rgba(102,80,170,.045));min-height:148px;box-shadow:0 7px 22px rgba(30,24,20,.045)}
.qm-card--risk{border-color:rgba(190,92,45,.38);background:linear-gradient(150deg,rgba(205,80,46,.095),rgba(255,184,77,.045))}.qm-card--risk:before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:#d27b24}.qm-card--stacked:before{background:#bd3f31;width:4px}
.qm-card header{display:flex;justify-content:space-between;gap:.35rem;border-bottom:1px solid rgba(128,128,128,.2);padding-bottom:.42rem}.qm-palace{display:flex;align-items:baseline;gap:.45rem}.qm-palace b{font-size:1.02rem}.qm-palace small{font-size:.67rem;opacity:.58;white-space:nowrap}.qm-markers{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:.18rem}.qm-marker{font-size:.61rem;color:white;padding:.12rem .32rem;border-radius:999px;line-height:1.45}.qm-marker--zhi-fu{background:#7652aa}.qm-marker--zhi-shi{background:#2c7180}.qm-marker--horse{background:#31765a}
.qm-roles,.qm-stems{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.3rem}.qm-roles{margin-top:.7rem}.qm-roles span,.qm-stems span{display:flex;flex-direction:column;align-items:center;min-width:0}.qm-roles small,.qm-stems small{font-size:.59rem;letter-spacing:.08em;opacity:.5}.qm-roles b{font-size:1.01rem;white-space:nowrap}.qm-stems{margin-top:.54rem;padding-top:.48rem;border-top:1px dashed rgba(128,128,128,.2)}.qm-stems b{font-size:.86rem;margin-top:.06rem}
.qm-harms{display:flex;flex-wrap:wrap;gap:.2rem;min-height:1.35rem;margin-top:.58rem;align-items:flex-end}.qm-harm{font-size:.66rem;font-weight:700;padding:.15rem .38rem;border-radius:5px;border:1px solid transparent;line-height:1.35}.qm-harm--kong-wang{color:#65568d;background:rgba(113,99,154,.12);border-color:rgba(113,99,154,.25)}.qm-harm--men-po{color:#a75913;background:rgba(210,123,36,.12);border-color:rgba(210,123,36,.28)}.qm-harm--ji-xing{color:#a43125;background:rgba(196,67,50,.12);border-color:rgba(196,67,50,.27)}.qm-harm--ru-mu{color:#70442f;background:rgba(138,91,67,.12);border-color:rgba(138,91,67,.27)}.qm-clear{font-size:.61rem;opacity:.35}
@media(max-width:700px){.qm-overview{grid-template-columns:repeat(4,1fr);gap:.3rem}.qm-overview-lead{grid-column:1/-1}.qm-overview>span{padding:.38rem .45rem}.qm-overview-item{flex-direction:column;gap:.08rem!important}.qm-grid{gap:.28rem}.qm-card{padding:.42rem;min-height:138px;border-radius:9px}.qm-palace{display:block}.qm-palace b{font-size:.79rem}.qm-palace small{display:block;font-size:.48rem;margin-top:.08rem}.qm-marker{font-size:.48rem;padding:.08rem .2rem}.qm-roles{margin-top:.45rem;gap:.05rem}.qm-roles small,.qm-stems small{font-size:.46rem}.qm-roles b{font-size:.68rem}.qm-stems{gap:.04rem;margin-top:.38rem;padding-top:.32rem}.qm-stems b{font-size:.64rem}.qm-harms{gap:.12rem;margin-top:.4rem;min-height:1.05rem}.qm-harm{font-size:.52rem;padding:.08rem .19rem}.qm-clear{font-size:.48rem}}
</style>"""
    # st.html is intended for HTML/CSS and avoids Markdown turning nested tags into text.
    st.html(styles + overview + '<div class="qm-grid">' + "".join(cards) + "</div>")

    with st.expander("查看四害判定依据与规则口径"):
        if harm_rows:
            st.dataframe(harm_rows, use_container_width=True, hide_index=True)
        else:
            st.success("本盘未标出空亡、门迫、击刑或入墓。")
        st.caption(si_hai.get("ruleSet", {}).get("note", "四害口径因门派而异，本结果仅作传统文化研究与排盘辅助。"))


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
