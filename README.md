# 奇门遁甲排盘系统

基于 Node.js 的奇门遁甲排盘系统，遵循茅山派奇门遁甲排盘方法，支持转盘排法。

## 功能特点

- **实时排盘** - 根据当前时间自动计算奇门盘
- **自选时间** - 支持任意日期时间排盘
- **完整要素** - 包含地盘、天盘、八门、九星、八神、暗干等
- **直观界面** - 九宫格可视化展示，信息清晰明了
- **转盘排法** - 采用传统转盘方式排布天盘与八门

## 预览

访问在线演示：[qm.qfdk.me](https://qm.qfdk.me)

## 快速开始

### 安装

```bash
git clone https://github.com/qfdk/qimen.git
cd qimen
pnpm install
```

### 运行

```bash
pnpm start
```

浏览器访问 `http://localhost:3000`

## 八字、人生 K 线与奇门融合（Streamlit）

项目同时提供 Streamlit 一体化界面：复用原有 `lunar-javascript` 四柱与奇门核心，按每年生日正午生成年度奇门盘，再把日主五行关系和值符宫的门、星、神转为透明、可追溯的 0–100 可视化指数。它不是从第三方仓库复制代码，也不把指数描述为确定预测。

```bash
npm install
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

浏览器访问 `http://localhost:8501`。侧栏可输入公历出生日期、时间、地点、分析主题和年份范围；页面会同时显示四柱、人生 K 线、逐年依据及出生时刻奇门九宫。

> 地点目前仅随结果保存，未做经纬度或真太阳时校正。人生 K 线属于传统文化模型的可视化结果，仅供学习与娱乐，不应用于医疗、投资或其他重要决策。

### Streamlit Community Cloud 一键部署

合并 PR 后可以直接部署，无需手工提交 `node_modules`：`requirements.txt` 安装 Python 包，`packages.txt` 安装 Node.js/npm，应用首次启动时根据 `package-lock.json` 自动执行 `npm ci --omit=dev`。

1. 在 [Streamlit Community Cloud](https://share.streamlit.io/) 选择本仓库和已合并的分支。
2. **Main file path** 填写 `streamlit_app.py`，点击 **Deploy**。
3. 首次启动需要下载 npm 依赖，通常会比后续重启稍慢；无需配置 Secrets。

部署前提是仓库为 Community Cloud 可访问的公开仓库，或部署账号已获得私有仓库授权；构建及首次启动环境还需要能够访问 PyPI、Debian 与 npm 软件源。

### 测试

```bash
pnpm test
```

## Docker 部署

```bash
# 构建 Streamlit 融合版镜像
docker build -t qimen .

# 运行容器
docker run -p 8501:8501 qimen
```

## 技术栈

| 类型 | 技术 |
|------|------|
| 后端 | Node.js + Express |
| 模板 | EJS |
| 前端 | HTML + CSS + JavaScript + Bootstrap |
| 历法 | lunar-javascript |

## 项目结构

```
qimen/
├── app.js                      # 应用入口（Express 服务）
├── lib/                        # 核心算法
│   ├── qimen.js                # 奇门排盘主逻辑
│   ├── bamen.js                # 八门计算
│   ├── bashen.js               # 八神计算
│   ├── jiuxing.js              # 九星计算
│   ├── dipan.js                # 地盘计算
│   ├── jieduan.js              # 节气定局计算
│   └── constants.js            # 常量定义
├── views/                      # 页面模板
│   ├── index.html              # 主页面
│   ├── standardGongTemplate.ejs # 九宫格模板
│   └── gongTemplate.html       # 宫格模板
├── public/                     # 静态资源
│   ├── css/                    # 样式
│   └── js/                     # 脚本
├── test/                       # 单元测试
│   ├── paipan.test.js          # 排盘基准测试
│   └── jieduan.test.js         # 节气定局测试
└── Dockerfile                  # 容器构建
```

## 奇门基础

### 阴阳遁局数

**阳遁歌诀：**
```
冬至、惊蛰一七四，小寒二八五，
大寒、春分三九六，雨水九六三，
清明、立夏四一七，立春八五二，
谷雨、小满五二八，芒种六三九。
```

**阴遁歌诀：**
```
夏至、白露九三六，小暑八二五，
大暑、秋分七一四，立秋二五八，
寒露、立冬六九三，处暑一四七，
霜降、小雪五八二，大雪四七一。
```

### 排盘步骤

1. 确定节气与三元（上元/中元/下元）
2. 确定阴阳遁与局数
3. 排布地盘天干地支
4. 确定值符、值使
5. 排布天盘九星
6. 排布八门
7. 排布八神

## 赞助

本项目由 [Voilà Pro](https://voilapro.app/) 赞助支持。

## 许可证

MIT License
