import json
import os

def load_logs(file_path: str) -> list:
    """
    讀取外部 JSON Array 檔案。
    
    Returns:
        list: 原始 log list
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到輸入的日誌檔案: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 格式解析失敗: {e}")

    if not isinstance(data, list):
        raise ValueError("輸入的日誌格式錯誤，必須為 JSON Array。")

    # 基本 sanity check：每筆需為 dict
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"第 {i} 筆資料不是 JSON object")

    return data
