def build_feature_texts(valid_logs: list, template_version: str = "v1") -> tuple:
    """
    將結構化日誌欄位轉換為富含語意的連續特徵文本。
    
    回傳:
        tuple: (feature_texts, text_builder_summary)
        - feature_texts: list of str, 生成的特徵文本列表
        - text_builder_summary: dict, 包含截斷統計的摘要
    """
    feature_texts = []
    truncated_count = 0
    max_token_threshold = 256

    for log in valid_logs:
        # 1. 根據版本選擇樣板 (目前僅支援 v1)
        if template_version == "v1":
            # 預設樣板 (v1) 欄位提取
            timestamp = log.get("timestamp", "unknown")
            actor_user = log.get("actor_user", "unknown")
            event_id = log.get("event_id", "unknown")
            process_action_details = log.get("process_action_details", "")
            source_ip = log.get("source_ip", "unknown")
            dest_ip = log.get("dest_ip", "unknown")
            
            # 組裝富含上下文語意的連續文字
            text = f"At {timestamp}, user {actor_user} triggered event {event_id}: {process_action_details}. Source IP: {source_ip}. Destination IP: {dest_ip}."
        else:
            # 未知版本預留相容性處理，預設回退至 process_action_details
            text = log.get("process_action_details", "")

        # 2. 長度估算與截斷控制 (使用 whitespace token count 估算)
        tokens = text.split()
        if len(tokens) > max_token_threshold:
            # 截斷至 256 tokens 並重新用空格組合
            text = " ".join(tokens[:max_token_threshold])
            truncated_count += 1

        feature_texts.append(text)

    # 3. 彙整特徵建立摘要
    summary = {
        "feature_template_version": template_version,
        "truncated_count_estimate": truncated_count
    }

    return feature_texts, summary

def build_feature_texts(valid_logs: list, template_version: str = "v1") -> tuple:
    """
    將結構化日誌欄位轉換為語意特徵文本。

    Returns:
        (feature_texts, summary)
    """

    if not isinstance(valid_logs, list):
        raise ValueError("valid_logs 必須為 list")

    feature_texts = []
    truncated_count = 0
    max_token_threshold = 256

    for idx, log in enumerate(valid_logs):

        if not isinstance(log, dict):
            raise ValueError(f"第 {idx} 筆 log 非 dict")

        # v1 template（不允許 fallback）
        if template_version == "v1":
            text = (
                f"At {log['timestamp']}, user {log['actor_user']} triggered event {log['event_id']}: "
                f"{log['process_action_details']}. "
                f"Source IP: {log['source_ip']}. "
                f"Destination IP: {log['dest_ip']}."
            )
        else:
            # 非 v1 僅允許直接使用語意欄位，不做補值
            text = log["process_action_details"]

        tokens = text.split()

        if len(tokens) > max_token_threshold:
            text = " ".join(tokens[:max_token_threshold])
            truncated_count += 1

        feature_texts.append(text)

    # invariant（硬性約束）
    if len(feature_texts) != len(valid_logs):
        raise RuntimeError("Invariant violated: feature_texts length mismatch")

    summary = {
        "feature_template_version": template_version,
        "truncated_count_estimate": truncated_count
    }

    return feature_texts, summary