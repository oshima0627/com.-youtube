# -*- coding: utf-8 -*-
"""設定ファイルの読み込み。config/ 配下の YAML を辞書で返すだけの薄い層。"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data" / "videos"


def _load(name):
    with open(CONFIG_DIR / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def settings():
    return _load("settings")


def permission():
    return _load("permission")


def exclusions():
    return _load("exclusions")


def work_dir(video_id):
    p = ROOT / settings()["paths"]["work"] / video_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def out_dir():
    p = ROOT / settings()["paths"]["out"]
    p.mkdir(parents=True, exist_ok=True)
    return p
