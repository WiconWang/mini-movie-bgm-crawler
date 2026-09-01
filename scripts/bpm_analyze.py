#!/usr/bin/env python3
"""
原神OST BPM + RMS 分析脚本
用法: python3 bpm_analyze.py <file1.mp3> [file2.mp3 ...]
输出: JSON 数组，每个元素包含文件名、BPM、时长、RMS等指标
"""
import sys
import json
import os

def analyze(filepath):
    """分析单个音频文件的BPM和RMS"""
    import librosa
    import numpy as np

    y, sr = librosa.load(filepath)

    # BPM 检测
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])

    # RMS 响度
    rms = librosa.feature.rms(y=y)[0]
    avg_rms = float(np.mean(rms))
    max_rms = float(np.max(rms))

    # 动态范围
    dynamic_range = 20 * np.log10(max_rms / avg_rms) if avg_rms > 0 else 0

    # 时长
    duration = float(librosa.get_duration(y=y, sr=sr))

    return {
        "file": filepath,
        "name": os.path.basename(filepath),
        "bpm": round(bpm, 1),
        "duration": round(duration, 1),
        "rms_avg": round(avg_rms, 4),
        "rms_max": round(max_rms, 4),
        "dynamic_range_db": round(dynamic_range, 1),
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 bpm_analyze.py <file1.mp3> [file2.mp3 ...]", file=sys.stderr)
        sys.exit(1)

    results = []
    for filepath in sys.argv[1:]:
        if not os.path.exists(filepath):
            results.append({"file": filepath, "error": "文件不存在"})
            continue
        try:
            result = analyze(filepath)
            results.append(result)
        except Exception as e:
            results.append({"file": filepath, "error": str(e)})

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
