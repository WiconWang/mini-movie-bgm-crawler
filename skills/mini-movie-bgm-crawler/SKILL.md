---
name: mini-movie-bgm-crawler
description: >-
  为游戏版本自动采集适合做视频BGM的轻柔音乐。
  根据版本号映射到OST专辑，用 yt-dlp 从QQ音乐/网易云下载官方原版，分析BPM/响度，筛选轻柔候选。
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
| **`yt-dlp`** | **主渠道：QQ音乐/网易云单曲下载（原生支持，无需逆向）** | `pip install -U yt-dlp` |
| `msc` (musicn) | 旧方案（网易云搜索）。**网易云播放接口已封**，仅 yt-dlp 歌手页也失效时才考虑 | `npm install -g musicn` |
| `librosa` | BPM + RMS 分析 | `uv pip install librosa soundfile` (venv) |
| `curl` | 下载 | 系统自带 |

**yt-dlp 支持的音乐站点**（`yt-dlp --list-extractors` 实测）：
```
qqmusic / qqmusic:album / qqmusic:playlist / qqmusic:singer / qqmusic:toplist
netease:song / netease:album / netease:playlist / netease:singer
apple:music:connect
```
⚠️ **无 `qqmusic:search`** —— 老的 `qqsearch:` / `qqsearch10:` 伪协议已被 yt-dlp 移除，
会报 `Unsupported url scheme`。拿 songmid 走下面的「歌手页」路径。

**yt-dlp 是首选渠道，不是 musicn。** yt-dlp 内部已处理 QQ 的 vkey 加密和网易云鉴权，
不需要 cookie、不需要逆向、不需要常驻 Web 服务。实测 QQ 音乐单曲页直接拿到 FLAC 无损。

环境准备：
```bash
# ---- 取 songmid：歌手页直取（唯一稳定路径，QQ 搜索 API 已死）----
# 路径只认老式 /n/ryqq/singer/<mid>；_<v2>_ 路径会 Unsupported URL
# 歌手 mid 属各游戏专属资料，查 references/singer-mid-map.md，不要写死在 skill 里
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(album)s" \
  "https://y.qq.com/n/ryqq/singer/<SINGER_MID>"
# 每行即一个 songmid；一次可列全该歌手名下所有官方曲目

# ---- 下载：QQ 音乐 songDetail 页（最稳）----
yt-dlp -f "bestaudio/best" -o "out/%(id)s.%(ext)s" \
  "https://y.qq.com/n/ryqq/songDetail/<songmid>"
# 遇到 VIP/试听限制 → 带浏览器 cookie
yt-dlp --cookies-from-browser firefox:<profile> -f "bestaudio/best" \
  -o "out/%(id)s.%(ext)s" "https://y.qq.com/n/ryqq/songDetail/<songmid>"

msc -q -P 18080 &                    # 仅 yt-dlp 不可用时才启动 musicn
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
<game> <version> 版本 BGM 候选清单
地区: <region> | OST: <album>

 #   BPM    时长   RMS     标签         名称
 1   76.0   1:36  0.062   ✅轻柔 ⭐    <track-cn>
 2   99.4   1:24  0.057   ✅轻柔       <track-cn>
 3  107.7   1:56  0.075   ⚠️可能       <track-cn> <track-en>

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
>     --kind bgm --src <out-dir>/genshin-2.1/tracks/01-<track-cn>.mp3 \
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
      01-<track-cn>.mp3
      02-<track-cn>.mp3
  .tmp-genshin-2.1/               # 临时文件（阶段一用）
    01.mp3
    name_map.json
    url_map.json
```

## 按需下载 + OSS 持久化（默认策略）

**不要全量囤曲库。** 一个游戏全版本 OST 常有上千首、几十 GB，而实际做视频只会用到一两百首。全量下载既占硬盘，又让 95% 的文件永远不被打开。

默认改为：**用户说版本号 → 只下该版本曲库（十几首）→ 用完即传到 OSS 归档 → 本地可删。**
OSS 不占本机硬盘，随时可重新签 URL 拉回。

### 标准流程

```bash
# 1. 取该版本曲库的 songmid（从 OSS 曲库表筛，或走歌手页）
python3 - <<'PY'
import json
d = json.load(open("/tmp/<game>_ost.json", encoding="utf-8"))
for a in d["albums"]:
    if a.get("_regions") and "<目标地区>" in " ".join(a["_regions"]):
        for t in a["tracks"]:
            if t.get("qqmusic_songmid"):
                print(t["qqmusic_songmid"], t["name_cn"], t["name_en"], sep="\t")
PY

# 2. 下载（先落 /tmp，tmpfs 不占硬盘，重启即失）
OUT=/tmp/<game>-<版本>-bgm; mkdir -p "$OUT"
while IFS=$'\t' read -r mid cn en; do
  yt-dlp --no-warnings -f "bestaudio/best" -o "$OUT/%(id)s.%(ext)s" \
    "https://y.qq.com/n/ryqq/songDetail/$mid" >/dev/null 2>&1
done <<< "$SONGMIDS"

# 3. 校验官方标签（★ 铁律，绝不可跳过）
ffprobe -v error -show_entries format_tags=title,album,artist -of json "$OUT"/*.flac

# 4. 传到 OSS 持久化（★ 用原生 https 域签名，避免审批噪音）
ossutil cp -f "$OUT"/*.flac oss://<BUCKET>/<game>/<版本>/bgm-<disc>/ -e oss-cn-beijing.aliyuncs.com
```

### 命名与目录约定

```
oss://<BUCKET>/<game>/<版本>/bgm-<disc>/
  <曲名中文>_<曲名英文>.flac     # 保留歌名，避免"临时文件名丢失歌名"
oss://<BUCKET>/<game>/<版本>/bgm-board.html   # 试听看板（含签名 URL）
```

### 容量估算（下载前先算给用户看）

QQ 音乐 FLAC 单曲均约 16 MB（区间 6~30 MB）。
```python
n, avg_mb = 17, 16.6      # 按实际样本替换
print(f"FLAC 全质量 ≈ {n*avg_mb/1024:.1f} GB")
```
先问用户「按需下 / 只囤核心专辑 / 全量」，给数字再动手。别擅自全量下载。

### 探测文件大小时不要用 `--skip-download`

`yt-dlp --print "%(filesize_approx)s" --skip-download` 在 QQ 音乐返回 `NA`，
拿不到体积。**只能真下后 `stat`/`ffprobe` 量。** 抽样估算时抽完记得删。

### 播放/试听 URL 会过期，音源 ID 不会

- 签名 URL 一年期，但**重新签一次即可**，不是音源丢失
- `qqmusic_songmid` 是稳定 ID，可重复下载
- 所以「怕被禁止爬取」而全量囤盘必要性不高——真正该备份的是
  **songmid 清单（即 OST 曲库表 JSON）**，体积仅数百 KB
- 建议：曲库表 JSON 务必持久化到 OSS；音频按需下、用完归档

## 版本→OST专辑映射

映射表**不放本 skill**，按游戏拆到 `references/` 与 OSS 资料库：

| 文件 | 内容 |
|------|------|
| `references/version-album-map.md` | 各游戏版本→专辑候选范围（粗筛用，非最终曲库） |
| `references/singer-mid-map.md` | 各游戏作曲团队的 QQ 歌手 mid（取 songmid 用） |
| `oss://mini-movie/资料/游戏/<游戏>/` | 权威曲库对照表：专辑/曲名/时长/地区/songmid |

**粗筛映射表只是起点**，最终曲库必须以对照表的「地区/场景」列筛出来
（理由见陷阱区「OST 专辑常跨版本」）。跨 3 个维度（版本 × 地区 × 场景）时
一律回资料库查，不要凭印象套表。

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

- **音质：QQ 音乐（yt-dlp）明显优于网易云**。实测同一专辑：QQ 拿到 FLAC 无损
  （19.6MB / 116.8s / 1345kbps）与 320k mp3；网易云免费源只有 128kbps。
  **音频一律走 yt-dlp + QQ 单曲页**；网易云现只剩元数据可用。
- 用户手动抓的 QQ 播放 URL（DevTools cURL）只有 ~97kbps，是试听级，不适合做正式 BGM。
- 频率限制：yt-dlp 单曲下载间隔 ≥2s；网易云搜索接口 ≥8s（否则 IP 限流）。
- BPM检测对纯音乐准确，交响乐可能有偏差，建议人工试听
- musicn Web 服务需保持运行，端口 18080（仅 yt-dlp 不可用时才需要）
- **下载耗时**：QQ FLAC 单曲约 200KiB/s，15~20MB/首 → 1~2 分钟一首；批量加 `sleep 2`
- 搜索结果 ≠ OST完整曲目列表（网易云搜索限制 + QQ 专辑页易空）；**单曲页最稳**
- 高音质/VIP 曲目：yt-dlp 加 `--cookies-from-browser firefox:<profile>`，实测可下

## 陷阱

### ★ 音源必须先下载到本地/OSS，看板只是临时试听手段

音乐平台的播放 URL 都带**短时效签名**，过期后一律 403：

| 平台 | 签名形式 | 实测寿命 |
|------|---------|---------|
| 网易云 | `m*.music.126.net/<YYYYMMDDHHMMSS>/<hash>/...`（时间戳在路径里） | **约 1~3 天** |
| QQ 音乐 | `vkey=...` 参数 | 几十分钟~几小时 |
| 酷狗 | `err_code: 20010` | 需 VIP |
| 咪咕 | SSL 握手 EOF | 不可用 |

⚠️ **网易云过期后的迷惑现象**：仍返回 `HTTP 403` + `Content-Type: audio/mpeg` + **146 字节**，
**状态码和 MIME 都正常，只有内容是错误页**。所以"curl 看着成功"≠ 音频可用，必须校验字节数/文件头。

**正确流程**：
```
采集 → 下载到本地 → 上传 OSS → 看板指向 OSS 签名 URL（1 年）
```
看板 URL 只是给用户试听的，**音频本体永远在 OSS**，不再依赖任何平台临时 URL。
OSS 签名用 `--timeout 31536000 --disable-encode-slash`（1 年），看板做完视频即可废弃。

### ★★ 网易云播放接口全线封死（2026-10 实测），别再试

以下全部已失效，**不要再浪费时间**：

| 接口 | 实测结果 |
|------|----------|
| `player/url/v1/?id=&ids=[…]` | 302 跳网页播放器，返回 `<!doctype html>` |
| `song/media/v1/?id=` | 返回带验证码 meta 的搜索页 HTML |
| `weapi/song/enhance/player/url` (POST) | 空响应 `b''` |
| `yt-dlp netease:song` | `geo restricted` + `No media links found` |
| `yt-dlp netease:album` | `Unable to extract metainfo` |

**网易云只剩元数据可用**（`https://music.163.com/api/album/<albumId>` 仍能读全量曲目名/时长/出品方，
适合做对照表），**音频一律走 QQ**。

### ★★ QQ 搜索 API 已锁死，取 songmid 只能走歌手页

以下全部返回空 / `req.code=40000`：
- `music.search.SearchCgiService` / `DoSearchForQQMusicDesktop`（search_type 0=专辑 1=歌曲）
- `music.musichallAlbum.AlbumInfoServer` / `GetAlbumList`
- `music.musichallSinger.SingerInfoInter` / `GetSingerSongList`
- `music.homepage.HomepageSrv` / `GetHomepage`
- `GetAlbumDetail` 能用，但**只返回 basicInfo/company/singer，不含 songList**

**唯一稳定的批量路径 —— 歌手页直取**：
```bash
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(album)s" \
  "https://y.qq.com/n/ryqq/singer/<SINGER_MID>"
```
`--flat-playlist` 不下音频只列条目，一次可出数千首。**songmid 拿到后永久有效**，
建议一次采集并落进该游戏的曲库对照表，以后直接用、无需再搜。
注意 `qqmusic:singer` 提取器只支持**老式路径** `/n/ryqq/singer/<mid>`；
`/n/ryqq_v2/singer/<mid>` 报 `Unsupported URL`。

**通用反查歌手 mid 的办法**：从任一官方专辑调
`music.musichallAlbum.AlbumInfoServer` / `GetAlbumDetail`，从
`data.singer.singerList[].mid` 取；`data.company.name` 同时可用于
核对出品方是否为官方（防搬运号）。各游戏已知的 mid 记在
`references/singer-mid-map.md`。

### ★ songmid ↔ 曲名匹配的 5 个坑（QQ 侧曲名 ≠ 网易云曲名）

QQ 标题与网易云曲名**顺序相反且各有脏数据**，整串精确比对必然漏一批，必须逐级放宽：

1. **顺序**：QQ 为「外文名 中文名」，网易云为「中文名 外文名」，两种拼接都要试
2. **括号**：QQ 常带场景补充说明，归一化时先剥掉 `(...)` / `（...）`
3. **连字符会丢**：`Moon-Eclipsing` 在 QQ 上可能是 `Moon-Elipsing`
4. **CJK 扩展区罕用字**：同一个汉字存在两种码位（常用区 U+4E00 与扩展区 U+2E80），
   归一化须剔除 `[\u2e80-\u2fdf\uf900-\ufaff]`，否则子串匹配失效
5. **同名多版本**：歌手页存在同名冲突条目（重制版/重复收录），必须**保留首次出现**
   并跳过重复；宽松键只在**全库唯一**时才可采信，否则会误配

兜底顺序：整串比对 → 放宽全角半角并剔除扩展区字 → 中文主体在全库唯一包含 →
英文主体在全库唯一包含。**匹配完务必抽验 3~5 条**
（`yt-dlp --print "%(album)s|%(creator)s" <songmid>`）核对专辑名与作曲者，防止误配。

### ★ QQ 音乐 vkey 接口已不开放给网页，不要再逆向

实测**全部**返回 `{"code":500001}`（连 `vkey` 块都没有）：
- 模块 `music.vkey.GetEVkey` / `StreamProxy.GetVkeyService` / `GetSongUrl`
- 域 `u.y.qq.com` 与 `t.y.qq.com`
- 完整 comm 字段（`cv:4747474`、`g_tk` = md5 位运算、`xcdn:1`、数组 `songmid`、数字型 guid）
- **在浏览器页面内、用 QQ 自己的域、credentials:'include' 也一样 500001**

结论：该接口只服务 App，网页版走另一条通道。**用 yt-dlp，不要逆向。**
（用户手动 DevTools 抓一条 cURL 可以拿到能播的 URL，但那是试听级码率 ~97kbps，
且只能单曲手动操作，不适合批量采集。）

### ★★ 「版本 → 专辑」映射不能只按地区猜，OST 专辑常跨版本

同一张 OST 专辑经常横跨多个版本甚至多个地区，硬套「某版本 = 某专辑」会取到大量无关曲。
（实例：某游戏 1.0 回顾 OST 里混着后续版本地图音乐与其它地区主线曲。）

**正确做法：拿权威曲目表的「地区/场景」维度筛，而不是按专辑名映射。**
wiki 的专辑页通常是逐曲表，筛选含目标地区关键词的行即得该版本准确曲库。
解析 wikitext 时注意清理 HTML 注释和 `[[链接|显示]]` 语法。
各游戏具体用哪张表、筛哪个关键词，记在该游戏的资料文档里，不要写进本 skill。

### ★ 别用 ytsearch 找音乐，会落到 YouTube

`ytsearch5:` 会返回 **YouTube 视频**，不是 QQ 音乐，多半是翻唱/改编/二创。
拿 songmid 走「歌手页」，下载走「单曲页」，见上文。

### ★ ossutil 上传成功的判据是 "OK num"，不是 "100%"

```bash
ossutil cp "$f" "oss://bucket/path/" -f 2>&1 | grep -q "OK num"   # ✓ 正确
ossutil cp ... | grep -q "100%"                                     # ✗ 永远匹配不上
```
用错判据会让整批上传**全部误报失败**（实际都已成功）。

### ★ OSS 签名不要传 -e 参数

```bash
ossutil sign oss://mini-movie/path.html --timeout 31536000 --disable-encode-slash
#                  ^ 不要 -e https://xxx.oss-cn-beijing.aliyuncs.com
```
传了 `-e` 会把域名拼成 `mini-movie.mini-movie.oss-cn-beijing.aliyuncs.com`（重复）导致签名不匹配。
默认签出的就是原生域。签名 URL 是 **http** 协议，浏览器/curl 直接用 https 替换即可，
**签名仍然有效**（OSS 签名不绑定协议），且 https 不会触发 tirith 的 `plain_http_to_sink`。

### ★ 交付链接一律用用户自定义域名，别给 OSS 原生域

用户会直接要求「用我们自己的自定义域名，不要用 OSS 的域名」。原因有二：
① 原生域下 `.html` 被平台**强制下载**（响应带 `x-oss-force-download` +
`Content-Disposition: attachment`），看板在浏览器里点开是下载而不是渲染；
② 自定义域实测 `ssl_verify_result=0`、直接渲染。

**换 Host 前缀不用重签** —— OSS 签名只绑「资源路径 + Expires + HTTP 方法」，与 Host 无关。
流程固定为：**签原生域 → 只替换 Host 前缀 → 落盘 → 逐个实测**。

⚠️ **换域后看板内嵌的每一个音源都要重新实测**，别只测 html 本身：
断言 `grep -c '<自定义域>' 看板.html` == 音源数、且原生域出现 0 处，两者都过再上传。
（html 返回 200 只证明壳子能打开，证明不了 `<audio>` 能出声。）

### ★ 看板 JS 事件绑定：data-i 在 td 上，不在 tr 上

表头 `<tr>` 没有 `.icon` 单元格，`document.querySelectorAll('tr').forEach` 会取到 null
→ `Cannot set properties of null (setting 'onclick')`。
改成 `tr[data-i]` 后匹配 0 个元素（因为 `data-i` 在 `<td class="icon">` 上）→ 点击完全无反应。
**正确写法**：
```js
document.querySelectorAll('td.icon[data-i]').forEach(td => {
  const ic = td.querySelector('.icon');
  if (!ic) return;            // 表头防御
  ic.onclick = () => play(+td.dataset.i);
});
```
排查顺序：先确认选择器匹配数 ≠ 0，再看有没有网络请求，最后才查音频 URL 是否过期。

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
