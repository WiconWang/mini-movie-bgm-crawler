#!/usr/bin/env python3
"""
游戏版本BGM采集脚本（两阶段：搜索分析 → 确认后下载）
用法:
  # 阶段一：搜索 + 分析（不下载）
  python3 crawl_version.py genshin 2.1 --dry-run

  # 阶段二：下载指定编号
  python3 crawl_version.py genshin 2.1 --download 1,3,5,7

  # 下载全部候选
  python3 crawl_version.py genshin 2.1 --download all
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# 配置
MUSICN_API = "http://localhost:18080"
PYTHON_VENV = "/tmp/audio-venv/bin/python3"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DOWNLOADS_DIR = os.path.join(PROJECT_DIR, "Downloads")
BPM_SCRIPT = os.path.join(SCRIPT_DIR, "bpm_analyze.py")

# 游戏前缀映射
GAME_PREFIXES = {
    "genshin": "原神",
    "starrail": "星穹铁道",
    "zzz": "绝区零",
    "wave": "鸣潮",
}

# 排除关键词（战斗相关）
EXCLUDE_KEYWORDS = [
    "battle", "boss", "combat", "war", "fight", "storm",
    "战斗", "周本", "深渊", "秘境",
]

# 优先关键词（适合BGM）
PREFER_KEYWORDS = [
    "theme", "day", "night", "village", "harbor", "peaceful",
    "serene", "melody", "lullaby", "reminiscence",
    "旋律", "月", "夜", "风", "梦", "宁静", "安详",
]

# 版本→OST专辑映射（原神）
VERSION_MAP_GENSHIN = {
    "1.0": {"region": "蒙德/璃月", "albums": ["风与牧歌之城", "皎月云间之梦"]},
    "1.1": {"region": "璃月", "albums": ["皎月云间之梦"]},
    "1.2": {"region": "蒙德(龙脊)", "albums": ["风与牧歌之城", "漩涡、落星与冰山"]},
    "1.3": {"region": "璃月", "albums": ["皎月云间之梦"]},
    "1.4": {"region": "蒙德", "albums": ["风与牧歌之城"]},
    "1.5": {"region": "璃月", "albums": ["皎月云间之梦"]},
    "1.6": {"region": "蒙德(海岛)", "albums": ["风与牧歌之城"]},
    "2.0": {"region": "稻妻", "albums": ["寂远无妄之国"]},
    "2.1": {"region": "稻妻", "albums": ["寂远无妄之国"]},
    "2.2": {"region": "稻妻", "albums": ["寂远无妄之国"]},
    "2.3": {"region": "稻妻", "albums": ["寂远无妄之国"]},
    "2.4": {"region": "璃月", "albums": ["皎月云间之梦"]},
    "2.5": {"region": "稻妻", "albums": ["寂远无妄之国"]},
    "2.6": {"region": "稻妻", "albums": ["寂远无妄之国", "佚落迁忘之岛"]},
    "2.7": {"region": "稻妻", "albums": ["寂远无妄之国", "佚落迁忘之岛"]},
    "2.8": {"region": "蒙德(海岛)", "albums": ["风与牧歌之城"]},
    "3.0": {"region": "须弥", "albums": ["智妙明论之林"]},
    "3.1": {"region": "须弥", "albums": ["智妙明论之林"]},
    "3.2": {"region": "须弥", "albums": ["智妙明论之林"]},
    "3.3": {"region": "须弥", "albums": ["智妙明论之林"]},
    "3.4": {"region": "须弥", "albums": ["智妙明论之林"]},
    "3.5": {"region": "须弥", "albums": ["啁哳流变之砂"]},
    "3.6": {"region": "须弥", "albums": ["啁哳流变之砂"]},
    "3.7": {"region": "须弥", "albums": ["智妙明论之林"]},
    "3.8": {"region": "须弥(海岛)", "albums": ["智妙明论之林"]},
    "4.0": {"region": "枫丹", "albums": ["白露澈明之泉"]},
    "4.1": {"region": "枫丹", "albums": ["白露澈明之泉"]},
    "4.2": {"region": "枫丹", "albums": ["白露澈明之泉"]},
    "4.3": {"region": "枫丹", "albums": ["白露澈明之泉"]},
    "4.4": {"region": "璃月", "albums": ["皎月云间之梦"]},
    "4.5": {"region": "枫丹", "albums": ["白露澈明之泉"]},
    "4.6": {"region": "枫丹", "albums": ["白露澈明之泉"]},
    "4.7": {"region": "枫丹", "albums": ["白露澈明之泉"]},
    "4.8": {"region": "蒙德(海岛)", "albums": ["风与牧歌之城"]},
    "5.0": {"region": "纳塔", "albums": ["炽炎交逐之原"]},
    "5.1": {"region": "纳塔", "albums": ["炽炎交逐之原"]},
    "5.2": {"region": "纳塔", "albums": ["炽炎交逐之原", "遥古喁望之阳"]},
    "5.3": {"region": "纳塔", "albums": ["遥古喁望之阳"]},
    "5.4": {"region": "纳塔", "albums": ["遥古喁望之阳"]},
    "5.5": {"region": "纳塔", "albums": ["竟夜有辉之燎"]},
}

# 版本→OST专辑映射（崩坏星穹铁道）
# 铁道 OST 结构：Experience the Paths = PV主题曲(偏燃)，Astral Theater = 角色曲
# Allegory of the Cave = 故事/区域OST(轻柔BGM) → 优先搜索
VERSION_MAP_STARRAIL = {
    "1.0": {"region": "空间站/雅利洛", "albums": ["Out of Control", "Of Snow and Ember"]},
    "1.1": {"region": "空间站/雅利洛", "albums": ["Of Snow and Ember", "Svah Sanishyu"]},
    "1.2": {"region": "仙舟", "albums": ["Svah Sanishyu"]},
    "1.3": {"region": "仙舟", "albums": ["Experience the Paths Vol. 1"]},
    "1.4": {"region": "匹诺康尼", "albums": ["Astral Theater"]},
    "1.5": {"region": "匹诺康尼", "albums": ["Experience the Paths Vol. 2"]},
    "1.6": {"region": "匹诺康尼", "albums": ["The Flapper Sinthome (Part 1)"]},
    "2.0": {"region": "匹诺康尼", "albums": ["The Flapper Sinthome (Part 2)"]},
    "2.1": {"region": "匹诺康尼", "albums": ["Experience the Paths Vol. 3"]},
    "2.2": {"region": "匹诺康尼", "albums": ["Astral Theater Vol. 2"]},
    "2.3": {"region": "翁法罗斯", "albums": ["Allegory of the Cave (Part 1)"]},
    "2.4": {"region": "翁法罗斯", "albums": ["Experience the Paths Vol. 4"]},
    "2.5": {"region": "翁法罗斯", "albums": ["Allegory of the Cave (Part 2)"]},
    "2.6": {"region": "翁法罗斯", "albums": ["Allegory of the Cave (Part 3)"]},
    "2.7": {"region": "翁法罗斯", "albums": ["Experience the Paths Vol. 5"]},
    "3.0": {"region": "翁法罗斯", "albums": ["Astral Theater Vol. 3"]},
    "3.1": {"region": "新区域", "albums": ["Let There Be Laughter (Part 1)"]},
    "3.2": {"region": "新区域", "albums": ["Let There Be Laughter (Part 1)"]},
    "3.3": {"region": "新区域", "albums": ["Let There Be Laughter (Part 2)"]},
    "3.4": {"region": "新区域", "albums": ["Let There Be Laughter (Part 2)"]},
    "3.5": {"region": "新区域", "albums": ["Let There Be Laughter (Part 2)"]},
    "3.6": {"region": "新区域", "albums": ["Experience the Paths Vol. 6"]},
}

# 版本映射注册表
VERSION_MAPS = {
    "genshin": VERSION_MAP_GENSHIN,
    "starrail": VERSION_MAP_STARRAIL,
    # "zzz": {},  # 待补充（绝区零）
    # "wave": {},  # 待补充（鸣潮）
}


def check_musicn():
    """检查 musicn Web 服务是否运行"""
    try:
        req = urllib.request.Request(f"{MUSICN_API}/search?service=wangyi&text=test&pageNum=1&pageSize=1")
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except Exception:
        return False


def search_album(keyword, service="wangyi", page_size=50):
    """搜索网易云OST专辑"""
    params = urllib.parse.urlencode({
        "service": service,
        "text": keyword,
        "pageNum": 1,
        "pageSize": page_size,
    })
    url = f"{MUSICN_API}/search?{params}"
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        return data.get("searchSongs", []), data.get("totalSongCount", 0)
    except Exception as e:
        print(f"  ✗ 搜索失败: {e}", file=sys.stderr)
        return [], 0


def filter_songs(songs):
    """过滤掉战斗相关曲目"""
    filtered = []
    excluded = []
    for song in songs:
        name = song.get("name", "").lower()
        if song.get("disabled") or not song.get("url"):
            excluded.append(song)
            continue
        if any(kw in name for kw in EXCLUDE_KEYWORDS):
            excluded.append(song)
            continue
        filtered.append(song)
    return filtered, excluded


def download_temp(songs, temp_dir):
    """下载到临时目录（仅用于BPM分析），保留原始歌名和URL映射"""
    os.makedirs(temp_dir, exist_ok=True)
    # 保存歌名映射: temp文件名 → 原始歌名
    name_map = {}
    # 保存URL映射: temp文件名 → 下载URL
    url_map = {}
    downloaded = []
    for i, song in enumerate(songs):
        name = song.get("songName", f"track_{i+1}.mp3")
        url = song.get("url", "")
        if not url:
            continue
        temp_name = f"{i+1:02d}.mp3"
        filepath = os.path.join(temp_dir, temp_name)
        name_map[temp_name] = name
        url_map[temp_name] = url
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=30)
            with open(filepath, "wb") as f:
                f.write(resp.read())
            size = os.path.getsize(filepath)
            if size > 1000:
                downloaded.append({
                    "index": i + 1,
                    "path": filepath,
                    "temp_name": temp_name,
                    "name": name,
                    "size": size,
                })
            else:
                os.remove(filepath)
                del name_map[temp_name]
        except Exception:
            del name_map[temp_name]
        time.sleep(0.3)
    # 保存映射到磁盘
    map_file = os.path.join(temp_dir, "name_map.json")
    with open(map_file, "w") as f:
        json.dump(name_map, f, ensure_ascii=False)
    url_file = os.path.join(temp_dir, "url_map.json")
    with open(url_file, "w") as f:
        json.dump(url_map, f, ensure_ascii=False)
    return downloaded


def analyze_tracks(tracks, temp_dir):
    """分析所有已下载曲目的BPM和RMS，并关联原始歌名"""
    if not tracks:
        return []
    files = " ".join(f'"{t["path"]}"' for t in tracks)
    cmd = f'"{PYTHON_VENV}" "{BPM_SCRIPT}" {files}'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        analyzed = json.loads(result.stdout)
    except Exception as e:
        print(f"  ✗ BPM分析失败: {e}", file=sys.stderr)
        return []

    # 加载歌名映射和URL映射
    map_file = os.path.join(temp_dir, "name_map.json")
    name_map = {}
    if os.path.exists(map_file):
        with open(map_file) as f:
            name_map = json.load(f)

    url_file = os.path.join(temp_dir, "url_map.json")
    url_map = {}
    if os.path.exists(url_file):
        with open(url_file) as f:
            url_map = json.load(f)

    # 关联原始歌名和URL
    for item in analyzed:
        fname = os.path.basename(item.get("file", ""))
        item["name"] = name_map.get(fname, fname)
        item["url"] = url_map.get(fname, "")

    return analyzed


def classify_candidates(analyzed):
    """根据BPM和RMS筛选轻柔候选"""
    candidates = []
    for track in analyzed:
        if "error" in track:
            continue
        bpm = track.get("bpm", 999)
        rms = track.get("rms_avg", 1)
        duration = track.get("duration", 0)

        if duration < 60:
            continue

        is_gentle = bpm < 100 and rms < 0.08
        is_maybe = bpm < 110 and rms < 0.10

        name_lower = track.get("name", "").lower()
        has_prefer = any(kw in name_lower for kw in PREFER_KEYWORDS)

        track["is_gentle"] = is_gentle
        track["is_maybe"] = is_maybe
        track["has_prefer"] = has_prefer
        candidates.append(track)

    candidates.sort(key=lambda t: (
        not t["is_gentle"],
        not t["has_prefer"],
        t.get("bpm", 999),
        t.get("rms_avg", 1),
    ))
    return candidates


def print_candidate_table(candidates, game_name, version, region):
    """打印候选清单表格"""
    print(f"\n{'='*60}")
    print(f"{game_name} {version} 版本 BGM 候选清单")
    print(f"地区: {region}")
    print(f"{'='*60}")
    print(f"{'#':<4} {'BPM':<7} {'时长':<7} {'RMS':<8} {'标签':<10} {'名称'}")
    print("─" * 70)

    for i, c in enumerate(candidates):
        tags = []
        if c.get("is_gentle"):
            tags.append("✅轻柔")
        elif c.get("is_maybe"):
            tags.append("⚠️可能")
        if c.get("has_prefer"):
            tags.append("⭐")
        tag_str = " ".join(tags)

        # 格式化时长
        dur = c.get("duration", 0)
        dur_str = f"{int(dur//60)}:{int(dur%60):02d}"

        print(f"{i+1:<4} {c.get('bpm','?'):<7} {dur_str:<7} {c.get('rms_avg','?'):<8} {tag_str:<10} {c.get('name','?')[:38]}")

    # 统计
    gentle_count = sum(1 for c in candidates if c.get("is_gentle"))
    maybe_count = sum(1 for c in candidates if c.get("is_maybe") and not c.get("is_gentle"))
    print(f"\n轻柔候选(✅): {gentle_count} 首 | 可能适合(⚠️): {maybe_count} 首 | 共 {len(candidates)} 首")
    print(f"{'='*60}")


def download_confirmed(candidates, indices, prefix, version, region, albums):
    """下载用户确认的曲目到正式目录"""
    dir_name = f"{prefix}-{version}"
    output_dir = os.path.join(DOWNLOADS_DIR, dir_name, "tracks")
    os.makedirs(output_dir, exist_ok=True)

    to_download = []
    for idx in indices:
        if 1 <= idx <= len(candidates):
            to_download.append(candidates[idx - 1])

    print(f"\n下载 {len(to_download)} 首到 {output_dir}/")

    # 加载临时目录的歌名映射
    temp_dir = os.path.join(DOWNLOADS_DIR, f".tmp-{prefix}-{version}")
    name_map = {}
    map_file = os.path.join(temp_dir, "name_map.json")
    if os.path.exists(map_file):
        with open(map_file) as f:
            name_map = json.load(f)
    reverse_map = {v: k for k, v in name_map.items()}

    downloaded = []
    for i, song in enumerate(to_download):
        name = song.get("name", f"track_{i+1}.mp3")
        url = song.get("url", "")
        local_file = song.get("file", "")

        # 清理文件名
        safe_name = name.split(" - ")[0].strip()
        safe_name = "".join(c for c in safe_name if c not in r'/:*?"<>|')
        filepath = os.path.join(output_dir, f"{i+1:02d}-{safe_name}.mp3")

        print(f"  [{i+1}/{len(to_download)}] {name[:50]}...")
        try:
            src = None
            if url and url.startswith("http"):
                src = "remote"
            elif local_file and os.path.exists(local_file):
                src = "local"
            elif name in reverse_map:
                candidate = os.path.join(temp_dir, reverse_map[name])
                if os.path.exists(candidate):
                    local_file = candidate
                    src = "local"

            if src == "remote":
                req = urllib.request.Request(url)
                resp = urllib.request.urlopen(req, timeout=30)
                with open(filepath, "wb") as f:
                    f.write(resp.read())
            elif src == "local":
                import shutil
                shutil.copy2(local_file, filepath)
            else:
                print(f"       ✗ 无可用源")
                continue

            size = os.path.getsize(filepath)
            if size > 1000:
                downloaded.append({"path": filepath, "name": name, "bpm": song.get("bpm"), "size": size})
                print(f"       ✓ {size/1024/1024:.1f}MB")
            else:
                os.remove(filepath)
                print(f"       ✗ 文件过小")
        except Exception as e:
            print(f"       ✗ 下载失败: {e}")
        time.sleep(0.5)

    # 保存 metadata
    meta_dir = os.path.join(DOWNLOADS_DIR, dir_name)
    metadata = {
        "prefix": prefix,
        "game": GAME_PREFIXES.get(prefix, prefix),
        "version": version,
        "region": region,
        "albums": albums,
        "total_downloaded": len(downloaded),
        "tracks": [{"name": d["name"], "bpm": d.get("bpm"), "file": os.path.basename(d["path"])} for d in downloaded],
    }
    with open(os.path.join(meta_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 下载完成！目录: {meta_dir}/")
    return downloaded


def generate_preview_html(candidates, prefix, version, region, albums, output_file, temp_dir):
    game_name = GAME_PREFIXES.get(prefix, prefix)
    """生成可试听的 HTML 预览页（使用远程 URL）"""
    rows = []
    for i, c in enumerate(candidates):
        dur = c.get("duration", 0)
        dur_str = f"{int(dur//60)}:{int(dur%60):02d}"
        bpm = c.get("bpm", "?")
        rms = c.get("rms_avg", "?")
        name = c.get("name", "?")
        url = c.get("url", "")
        tags = []
        if c.get("is_gentle"):
            tags.append('<span class="tag gentle">✅轻柔</span>')
        elif c.get("is_maybe"):
            tags.append('<span class="tag maybe">⚠️可能</span>')
        if c.get("has_prefer"):
            tags.append('<span class="tag prefer">⭐推荐</span>')
        tag_html = " ".join(tags)
        if not url:
            continue
        rows.append(f"""
        <tr data-idx="{i}">
          <td class="icon">▶</td>
          <td class="idx">{i+1}</td>
          <td class="name">{name}</td>
          <td class="bpm">{bpm}</td>
          <td class="dur">{dur_str}</td>
          <td class="rms">{rms}</td>
          <td class="tags">{tag_html}</td>
        </tr>""")

    # 构建 JS 曲目数据
    tracks_js = json.dumps([
        {
            "name": c.get("name", "?"),
            "url": c.get("url", ""),
            "bpm": c.get("bpm", "?"),
            "dur": f"{int(c.get('duration',0)//60)}:{int(c.get('duration',0)%60):02d}",
            "tag": "✅轻柔" if c.get("is_gentle") else ("⚠️可能" if c.get("is_maybe") else ""),
        }
        for c in candidates if c.get("url")
    ], ensure_ascii=False)

    gentle_count = sum(1 for c in candidates if c.get("is_gentle"))
    maybe_count = sum(1 for c in candidates if c.get("is_maybe") and not c.get("is_gentle"))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{game_name} {version} BGM 候选预览</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; padding-bottom: 80px; }}
  h1 {{ color: #58a6ff; margin-bottom: 4px; }}
  .meta {{ color: #8b949e; margin-bottom: 16px; }}
  .stats {{ margin-bottom: 16px; color: #8b949e; }}
  .stats .gentle {{ color: #3fb950; }}
  .stats .maybe {{ color: #d29922; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #161b22; color: #8b949e; text-align: left; padding: 8px 12px; border-bottom: 1px solid #30363d; position: sticky; top: 0; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; cursor: pointer; }}
  tr:hover {{ background: #161b22; }}
  tr.playing {{ background: #1a2332; }}
  .idx {{ color: #8b949e; width: 40px; }}
  .name {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .bpm {{ font-family: monospace; }}
  .dur {{ font-family: monospace; color: #8b949e; }}
  .rms {{ font-family: monospace; color: #8b949e; }}
  .tags {{ white-space: nowrap; }}
  .tag {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-right: 4px; }}
  .tag.gentle {{ background: #1a3a2a; color: #3fb950; }}
  .tag.maybe {{ background: #2d2200; color: #d29922; }}
  .tag.prefer {{ background: #1a1a3a; color: #a5b4fc; }}
  .icon {{ color: #8b949e; width: 30px; text-align: center; }}
  tr.playing .icon {{ color: #58a6ff; }}
  .tip {{ color: #8b949e; font-size: 13px; margin-top: 16px; }}
  /* 底部固定播放器 */
  .player-bar {{ position: fixed; bottom: 0; left: 0; right: 0; background: #161b22; border-top: 1px solid #30363d; padding: 10px 20px; display: flex; align-items: center; gap: 16px; z-index: 100; }}
  .player-bar .track-info {{ flex: 1; overflow: hidden; }}
  .player-bar .track-name {{ color: #c9d1d9; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .player-bar .track-meta {{ color: #8b949e; font-size: 12px; }}
  .player-bar audio {{ flex: 1; height: 40px; min-width: 300px; }}
</style>
</head>
<body>
<h1>🎵 {game_name} {version} BGM 候选预览</h1>
<div class="meta">地区: {region} | OST: {', '.join(albums)}</div>
<div class="stats">
  轻柔候选 <span class="gentle">{gentle_count} 首</span> |
  可能适合 <span class="maybe">{maybe_count} 首</span> |
  共 {len(rows)} 首
</div>
<table>
  <thead>
    <tr><th></th><th>#</th><th>名称</th><th>BPM</th><th>时长</th><th>RMS</th><th>标签</th></tr>
  </thead>
  <tbody id="track-list">
    {"".join(rows)}
  </tbody>
</table>
<div class="tip">💡 点击行播放/暂停。确认编号后执行：<br>
<code>python3 scripts/crawl_version.py {prefix} {version} --download &lt;编号&gt;</code></div>

<div class="player-bar" id="player-bar">
  <div class="track-info">
    <div class="track-name" id="player-name">点击上方曲目开始试听</div>
    <div class="track-meta" id="player-meta"></div>
  </div>
  <audio id="global-player" controls></audio>
</div>

<script>
const tracks = {tracks_js};
const player = document.getElementById('global-player');
const playerName = document.getElementById('player-name');
const playerMeta = document.getElementById('player-meta');
let currentIdx = -1;

document.querySelectorAll('#track-list tr').forEach((row, i) => {{
  row.addEventListener('click', () => {{
    if (currentIdx === i && !player.paused) {{
      player.pause();
      row.classList.remove('playing');
      return;
    }}
    document.querySelectorAll('#track-list tr.playing').forEach(r => r.classList.remove('playing'));
    currentIdx = i;
    row.classList.add('playing');
    const t = tracks[i];
    player.src = t.url;
    player.play();
    playerName.textContent = t.name;
    playerMeta.textContent = `BPM ${{t.bpm}} · ${{t.dur}} · ${{t.tag}}`;
  }});
}});

player.addEventListener('pause', () => {{
  document.querySelectorAll('#track-list tr.playing').forEach(r => r.classList.remove('playing'));
}});

player.addEventListener('ended', () => {{
  document.querySelectorAll('#track-list tr.playing').forEach(r => r.classList.remove('playing'));
}});
</script>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description="游戏版本BGM采集器")
    parser.add_argument("prefix", choices=GAME_PREFIXES.keys(), help="游戏 code（genshin/zzz/starrail/wave/endfield，绝区零/终末地映射待补充）")
    parser.add_argument("version", help="版本号，如 2.1、1.5")
    parser.add_argument("--service", default="wangyi", help="音乐源 (default: wangyi)")
    parser.add_argument("--dry-run", action="store_true", help="只搜索分析不下载（阶段一）")
    parser.add_argument("--download", type=str, help="下载指定编号，逗号分隔，或 'all'（阶段二）")
    parser.add_argument("--page-size", type=int, default=50, help="每专辑搜索数量")
    args = parser.parse_args()

    prefix = args.prefix
    version = args.version
    game_name = GAME_PREFIXES.get(prefix, prefix)

    # 查版本映射
    version_maps = VERSION_MAPS.get(prefix)
    if not version_maps:
        print(f"✗ 游戏 {game_name} 的版本映射尚未配置", file=sys.stderr)
        sys.exit(1)

    if version not in version_maps:
        print(f"✗ 未知版本: {prefix} {version}", file=sys.stderr)
        known = sorted(version_maps.keys())
        print(f"  已知版本: {', '.join(known)}")
        sys.exit(1)

    info = version_maps[version]

    # 检查 musicn
    if not check_musicn():
        print("✗ musicn Web 服务未运行！", file=sys.stderr)
        print("  请先启动: msc -q -P 18080 &")
        sys.exit(1)

    # ── 阶段一：搜索 + 分析 ──
    if args.dry_run:
        print(f"{'='*60}")
        print(f"{game_name} {version} 版本 BGM 采集（阶段一：搜索分析）")
        print(f"{'='*60}")
        print(f"地区: {info['region']}")
        print(f"OST专辑: {', '.join(info['albums'])}")

        # 搜索所有专辑
        all_songs = []
        for album in info["albums"]:
            keyword = f"{game_name} {album}"
            print(f"\n搜索: {keyword}")
            songs, total = search_album(keyword, args.service, args.page_size)
            print(f"  找到 {total} 首，获取 {len(songs)} 首")
            all_songs.extend(songs)

        # 去重
        seen = set()
        unique_songs = []
        for s in all_songs:
            name = s.get("name", "")
            if name not in seen:
                seen.add(name)
                unique_songs.append(s)
        print(f"\n去重后: {len(unique_songs)} 首")

        # 过滤
        filtered, excluded = filter_songs(unique_songs)
        print(f"过滤后: {len(filtered)} 首 (排除 {len(excluded)} 首战斗/无效)")

        # 下载到临时目录分析
        temp_dir = os.path.join(DOWNLOADS_DIR, f".tmp-{prefix}-{version}")
        print(f"\n临时下载到: {temp_dir}")
        downloaded = download_temp(filtered, temp_dir)
        print(f"下载完成: {len(downloaded)} 首")

        if not downloaded:
            print("无可用曲目")
            return

        # BPM 分析
        print(f"\nBPM + RMS 分析...")
        analyzed = analyze_tracks(downloaded, temp_dir)

        # 筛选候选
        candidates = classify_candidates(analyzed)

        # 保存候选数据到临时文件（阶段二需要）
        candidate_file = os.path.join(DOWNLOADS_DIR, f".tmp-{prefix}-{version}-candidates.json")
        with open(candidate_file, "w") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)

        # 输出候选清单
        print_candidate_table(candidates, game_name, version, info['region'])

        # 生成 HTML 预览页（放在版本目录，供下游软链接）
        version_dir = os.path.join(DOWNLOADS_DIR, f"{prefix}-{version}")
        os.makedirs(version_dir, exist_ok=True)
        preview_file = os.path.join(version_dir, "preview.html")
        generate_preview_html(candidates, prefix, version, info['region'], info['albums'], preview_file, temp_dir)
        print(f"\n🔊 预览页已生成: {preview_file}")
        print(f"   用浏览器打开即可试听")

        print(f"\n📋 确认后请执行:")
        print(f"   python3 scripts/crawl_version.py {prefix} {version} --download <编号,如 1,3,5 或 all>")
        return

    # ── 阶段二：下载 ──
    if args.download:
        # 加载候选数据
        candidate_file = os.path.join(DOWNLOADS_DIR, f".tmp-{prefix}-{version}-candidates.json")
        if not os.path.exists(candidate_file):
            print(f"✗ 未找到候选数据: {candidate_file}", file=sys.stderr)
            print(f"  请先执行阶段一: python3 scripts/crawl_version.py {prefix} {version} --dry-run")
            sys.exit(1)

        with open(candidate_file) as f:
            candidates = json.load(f)

        # 解析下载编号
        if args.download.lower() == "all":
            indices = list(range(1, len(candidates) + 1))
        else:
            indices = [int(x.strip()) for x in args.download.split(",")]

        download_confirmed(candidates, indices, prefix, version, info['region'], info['albums'])

        # 清理临时文件
        temp_dir = os.path.join(DOWNLOADS_DIR, f".tmp-{prefix}-{version}")
        candidate_file = os.path.join(DOWNLOADS_DIR, f".tmp-{prefix}-{version}-candidates.json")
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        if os.path.exists(candidate_file):
            os.remove(candidate_file)
        return

    # 无操作参数
    parser.print_help()


if __name__ == "__main__":
    main()
