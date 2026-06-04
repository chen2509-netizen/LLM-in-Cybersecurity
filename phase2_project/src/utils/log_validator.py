def validate_logs(raw_logs: list) -> tuple:
    """
    執行日誌 Schema 驗證與補值。
    
    回傳:
        tuple: (valid_logs, summary_dict)
        - valid_logs: 通過驗證並處理完成的日誌列表
        - summary_dict: 包含統計數據的字典
    """
    valid_logs = []
    invalid_log_count = 0
    fallback_count = 0
    replacement_counts = {
        "source_ip": 0,
        "dest_ip": 0,
        "actor_user": 0,
        "event_id": 0
    }

    for log in raw_logs:
        # 1. 硬性過濾：缺失 log_id 或 timestamp 則剔除
        if not log.get("log_id") or not log.get("timestamp"):
            invalid_log_count += 1
            continue

        validated_log = log.copy()

        # 2. process_action_details 缺失與異常處理規則
        if not validated_log.get("process_action_details"):
            if validated_log.get("raw_message"):
                validated_log["process_action_details"] = validated_log["raw_message"]
                fallback_count += 1
            else:
                invalid_log_count += 1
                continue

        # 3. 允許缺失的欄位自動補值為 "unknown"
        for field in ["source_ip", "dest_ip", "actor_user", "event_id"]:
            if not validated_log.get(field):
                validated_log[field] = "unknown"
                replacement_counts[field] += 1

        valid_logs.append(validated_log)

    # 彙整統計摘要
    summary = {
        "input_summary": {
            "input_log_count": len(raw_logs),
            "valid_log_count": len(valid_logs),
            "invalid_log_count": invalid_log_count
        },
        "validation_details": {
            "fallback_to_raw_message_count": fallback_count,
            "field_replacements": replacement_counts
        }
    }

    return valid_logs, summary

def validate_logs(raw_logs: list) -> tuple:
    """
    執行日誌 Schema 驗證與補值。

    Returns:
        tuple:
            valid_logs (list)
            summary_dict (dict)
    """
    if not isinstance(raw_logs, list):
        raise ValueError("raw_logs 必須為 list")

    valid_logs = []
    invalid_log_count = 0
    fallback_count = 0

    replacement_counts = {
        "source_ip": 0,
        "dest_ip": 0,
        "actor_user": 0,
        "event_id": 0
    }

    for idx, log in enumerate(raw_logs):

        # 防止非 dict 結構混入
        if not isinstance(log, dict):
            invalid_log_count += 1
            continue

        # 1. 必要欄位檢查
        log_id = log.get("log_id")
        timestamp = log.get("timestamp")

        if not log_id or not isinstance(log_id, str):
            invalid_log_count += 1
            continue

        if not timestamp or not isinstance(timestamp, str):
            invalid_log_count += 1
            continue

        validated_log = log.copy()

        # 2. 主語意欄位處理
        process_text = validated_log.get("process_action_details")

        if not process_text:
            raw_message = validated_log.get("raw_message")

            if raw_message:
                validated_log["process_action_details"] = raw_message
                fallback_count += 1
            else:
                invalid_log_count += 1
                continue

        # 3. 可缺失欄位補值
        for field in ["source_ip", "dest_ip", "actor_user", "event_id"]:
            value = validated_log.get(field)

            if not value:
                validated_log[field] = "unknown"
                replacement_counts[field] += 1

        valid_logs.append(validated_log)

    input_log_count = len(raw_logs)
    valid_log_count = len(valid_logs)

    # invariant 檢查（文件要求）
    if input_log_count != (valid_log_count + invalid_log_count):
        raise RuntimeError("Invariant violated: input_log_count != valid + invalid")

    summary = {
        "input_summary": {
            "input_log_count": input_log_count,
            "valid_log_count": valid_log_count,
            "invalid_log_count": invalid_log_count
        },
        "validation_details": {
            "fallback_to_raw_message_count": fallback_count,
            "field_replacements": replacement_counts
        }
    }

    return valid_logs, summary