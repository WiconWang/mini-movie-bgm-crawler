---
name: mini-movie-bgm-crawler
description: >-
  为游戏版本自动采集适合做视频BGM的轻柔音乐。
  根据版本号映射到OST专辑，从网易云搜索下载，分析BPM/响度，筛选轻柔候选。
  游戏 code 与统一台账一致：genshin/zzz/starrail/wave/endfield。
  触发词：原神BGM、版本BGM、OST采集、BGM筛选、mini-movie-bgm-crawler、绝区零BGM、鸣潮BGM。
---

# 游戏版本BGM采集器

为游戏版本自动采集适合做视频BGM的轻柔音乐。支持多游戏。

## 支持的游戏（code 与统一台账一致，定死后不改）

| 游戏 | code | 目录名示例 | 状态 |
|------|------|------------|------|
| 原神 | `genshin` | `genshin-2.1` | ✅ 已适配 |
| 星穹铁道 | `starrail` | `starrail-3.6` | ✅ 已适配 |
| 绝区零 | `zzz` | `zzz-1.2` | 🔲 待适配 |
| 鸣潮 | `wave` | `wave-1.0` | 🔲 待适配 |
| 终末地 | `endfield` | — | 🔲 待适配 |

## 依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| `msc` (musicn) | 网易云搜索+下载 API | `npm install -g musicn` |
| `librosa` | BPM + RMS 分析 | `uv pip install librosa soundfile` (venv) |
| `curl` | 下载 | 系统自带 |

环境准备：
```bash
msc -q -P 18080 &                    # 启动 musicn Web 服务
uv venv ~/.venvs/audio               # 音频分析 venv（持久路径，勿用 /tmp）
# 安装 librosa+soundfile —— 解释器路径随平台而异：
uv pip install --python ~/.venvs/audio/bin/python librosa soundfile        # Linux / macOS
uv pip install --python ~/.venvs/audio/Scripts/python.exe librosa soundfile   # Windows
```
> 分析用的解释器由 `crawl_version.py` 在**运行时**解析（`_resolve_audio_python()`）：
> `MMM_AUDIO_VENV_PYTHON` 显式指定 → 约定 venv `~/.venvs/audio`（按平台探测
> `bin/python3` 或 `Scripts/python.exe`）→ 当前解释器兜底。
> **不要用 `/tmp` 存 venv**：重启即丢，会导致 BPM/RMS 分析静默返回 0 首。

## 两阶段工作流

> 脚本位于本 skill 目录 `scripts/` 下，以下命令均从 skill 目录（本 SKILL.md 所在目录）执行；产物落 `-o/--out-dir` 指定目录（默认仓库根 `Downloads/`）。
> **作为 game-storyline-pipeline 一环时**：管线铁律要求产物不进各 skill 仓库，必须显式 `-o` 暂存（如 `-o /tmp/bgm-staging`），再 `mmm add-asset` 登记入库。

### 阶段一：搜索 + 分析

```bash
python3 scripts/crawl_version.py <code> <版本> --dry-run
# 例：python3 scripts/crawl_version.py genshin 2.1 --dry-run
```

流程：版本号 → 映射OST专辑 → musicn搜索 → 过滤战斗曲 → 临时下载 → BPM/RMS分析 → 输出候选清单

输出候选清单示例：
```
原神 2.1 版本 BGM 候选清单
地区: 稻妻 | OST: 寂远无妄之国

 #   BPM    时长   RMS     标签         名称
 1   76.0   1:36  0.062   ✅轻柔 ⭐    美梦抚归人(望舒夜间)
 2   99.4   1:24  0.057   ✅轻柔       青云流风饰霓裳
 3  107.7   1:56  0.075   ⚠️可能       暧暧含光 Hazy Light

轻柔候选(✅): 2 首 | 可能适合(⚠️): 1 首 | 共 3 首
```

### 阶段二：用户确认后下载

```bash
python3 scripts/crawl_version.py <code> <版本> --download <编号>
# 例：python3 scripts/crawl_version.py genshin 2.1 --download 1,2
# 例：python3 scripts/crawl_version.py genshin 2.1 --download all
```

下载到 `<out-dir>/<code>-<版本>/tracks/`（`-o` 指定，默认仓库 `Downloads/`），同时生成 `metadata.json` 和 `preview.html`。

> 登记进统一台账（版本级 bgm 资产，落 `{game}/{version}/_version/bgm/`，BPM/RMS 进 ledger `meta_json`）：
> ```bash
> mmm add-asset --game genshin --version 2.1 --slug <quest_slug> \
>     --kind bgm --src <out-dir>/genshin-2.1/tracks/01-美梦抚归人.mp3 \
>     --source-url "<OST专辑>"
> ```
> （`-o/--out-dir` 指定暂存根；登记时 `add-asset` 复制入库。`--slug` 仅用于定位版本，bgm 不挂 quest。）

阶段一会在 `<out-dir>/<前缀>-<版本>/` 生成 `preview.html` 预览页，底部固定播放器，浏览器打开可直接试听所有候选曲目。

## 输出目录结构

```
<out-dir>/                         # -o 指定；默认仓库根 Downloads/
  genshin-2.1/                    # 原神 2.1
    metadata.json                 # 版本元信息 + 曲目列表
    preview.html                  # 可试听的候选预览页
    tracks/
      01-美梦抚归人.mp3
      02-青云流风饰霓裳.mp3
  .tmp-genshin-2.1/               # 临时文件（阶段一用）
    01.mp3
    name_map.json
    url_map.json
```

## 版本→OST专辑映射

映射表内联如下（原件备份于本 skill 目录 `references/version-album-map.md`，以内联表为准）。

### 原神

| 版本范围 | 地区 | OST专辑 |
|----------|------|---------|
| 1.0-1.6 | 蒙德/璃月 | 风与牧歌之城、皎月云间之梦 |
| 2.0-2.8 | 稻妻 | 寂远无妄之国 |
| 3.0-3.8 | 须弥 | 智妙明论之林、啁哳流变之砂 |
| 4.0-4.8 | 枫丹 | 白露澈明之泉 |
| 5.0-5.x | 纳塔 | 炽炎交逐之原 |

### 崩坏星穹铁道

铁道 OST 分两类：**Experience the Paths** = PV主题曲(偏燃)，**Allegory of the Cave / Astral Theater** = 故事/区域OST(轻柔BGM)。搜索时优先用后者。

| 版本范围 | 区域 | OST专辑 |
|----------|------|---------|
| 1.0-1.2 | 空间站/雅利洛/仙舟 | Out of Control, Of Snow and Ember, Svah Sanishyu |
| 1.3-2.2 | 仙舟/匹诺康尼 | Experience the Paths Vol.1-3, Astral Theater Vol.1-2 |
| 2.3-2.7 | 翁法罗斯 | Allegory of the Cave (Part 1-3), Experience the Paths Vol.4-5 |
| 3.0-3.6 | 翁法罗斯/新区域 | Astral Theater Vol.3, Let There Be Laughter (Part 1-2), Experience the Paths Vol.6 |

## 筛选标准

| 指标 | 轻柔(✅) | 可能(⚠️) |
|------|----------|----------|
| BPM | < 100 | < 110 |
| RMS avg | < 0.08 | < 0.10 |
| 时长 | > 60s | > 60s |

排除关键词：Battle, Boss, Combat, War, 战斗, 周本
优先关键词：Theme, Day, Night, Village, Peaceful, 月, 夜, 风

## Agent 执行规范

1. 用户说「找 XX 版本的 BGM」→ 执行阶段一，输出候选清单
2. 等用户确认编号 → 执行阶段二下载
3. 下载完成后报告文件位置
4. musicn 未运行时自动启动（`msc -q -P 18080 &`）
5. librosa venv 不存在时自动创建

## 注意事项

- 音质：网易云免费源默认 128kbps，够用于视频BGM
- 频率限制：批量下载间隔 0.5s
- BPM检测对纯音乐准确，交响乐可能有偏差，建议人工试听
- musicn Web 服务需保持运行，端口 18080
- 搜索结果 ≠ OST完整曲目列表（网易云搜索限制）
- musicn 不支持登录/高音质 Cookie，高音质需走 go-music-dl Web UI 或手动提取 Cookie

## 陷阱

### musicn Web 服务崩溃
下载 URL 失效时进程可能退出。解决：监控进程，必要时重启 `msc -q -P 18080 &`。

### 音频分析失败（BPM/RMS 全空 / 结果 0 首）
先看 stderr：脚本会显式报出解释器路径与退出码。
- **`✗ 音频分析解释器不存在: <路径>`** → venv 丢了，按上文「环境准备」重建（注意平台差异）
- 换用其它含 librosa 的解释器：`export MMM_AUDIO_VENV_PYTHON=/path/to/python`
- ⚠️ 历史坑：`PYTHON_VENV` 曾硬编码 `/tmp/audio-venv`，**重启后 venv 消失**，
  而 `json.loads("")` 只抛出 "Expecting value"，真实原因被吞 →
  **BGM 能搜能下但分析结果恒为 0 首、看不出原因**。现已改为运行时跨平台解析 + 前置存在性检查。

### 临时文件名丢失歌名
musicn 下载临时文件用序号命名（01.mp3），需通过 `name_map.json` 映射回原始歌名。脚本已处理此问题（`download_temp` 函数）。

### go-music-dl 仅 386 版本
GitHub Release 只有 Linux 386 包，x86_64 可兼容运行但非原生。Web UI 返回 HTML 不是 JSON API，不适合脚本化。仅建议用于手动登录获取高音质。
