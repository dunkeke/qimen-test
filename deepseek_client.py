"""Minimal DeepSeek chat-completions client using only the Python standard library."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://api.deepseek.com/chat/completions"


def build_prompt(pan: dict, question: str) -> str:
    """Create a compact, auditable prompt from the calculated Qi Men chart."""
    chart = {
        "占卦时间": pan.get("basicInfo", {}).get("date"),
        "四柱": pan.get("siZhu"),
        "局数": pan.get("juShu", {}).get("fullName"),
        "旬首": pan.get("xunShou"),
        "值符": {"星": pan.get("zhiFuXing"), "宫": pan.get("zhiFuGong")},
        "值使": {"门": pan.get("zhiShiMen"), "宫": pan.get("zhiShiGong")},
        "九星": pan.get("jiuXing"),
        "八门": pan.get("baMen"),
        "八神": pan.get("baShen"),
        "天盘": pan.get("tianPan"),
        "地盘": pan.get("diPan"),
        "空亡": pan.get("kongWangZhi"),
        "驿马": pan.get("maStar"),
        "四害": pan.get("siHai"),
        "程序格局": pan.get("geju"),
    }
    return (
        f"用户问题：{question or '综合趋势'}\n\n奇门盘 JSON：\n"
        f"{json.dumps(chart, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "请严格依据盘面，不要虚构缺失信息。依次给出：1.盘面要点；2.针对问题的分析；"
        "3.有利与不利因素；4.可执行建议；5.不确定性提示。避免绝对化预测，健康、法律、投资问题须提示咨询专业人士。"
    )


def interpret(api_key: str, pan: dict, question: str, timeout: int = 60) -> str:
    """Request an interpretation from DeepSeek's OpenAI-compatible endpoint."""
    if not api_key.strip():
        raise ValueError("请先配置 DeepSeek API Key")
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是谨慎的奇门遁甲传统文化研究助手。区分盘面事实、推断和建议，并使用中文回答。"},
            {"role": "user", "content": build_prompt(pan, question)},
        ],
        "temperature": 0.4,
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    request = Request(API_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"DeepSeek API 返回 {error.code}：{detail}") from error
    except URLError as error:
        raise RuntimeError(f"无法连接 DeepSeek API：{error.reason}") from error
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("DeepSeek API 返回了无法识别的响应") from error
