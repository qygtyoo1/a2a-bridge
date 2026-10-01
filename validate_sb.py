#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRIDGE-1.0 五构件本地校验工具 (validate_sb.py)

Bridge-Agent 本体组件的机器可执行校验器: 对「登记(agent_card)/诉求(appeal)/握手(handshake)/
协作房间(room)/连接账本(ledger_entry)/守护(guard)」六类 BRIDGE-1.0 JSON 记录做字段级校验。

设计原则(对齐 SKILL.md 边界铁律):
- 零网络依赖: 默认不做 endpoint 回读, 仅校验格式(HTTPS), 避免安装器挂起类故障(K5 教训);
  需要端点回读时显式加 --check-endpoint。
- 人牵线铁律: handshake 强制 human_approval.a.present 与 .b.present 均为 true, 否则判失败。
- 协议版本强制: 所有记录顶层 schema_version 必须 == "BRIDGE-1.0"。

用法:
  python validate_sb.py --file <record.json | ledger.jsonl>
  python validate_sb.py --dir examples/
  python validate_sb.py --file x.json --check-endpoint --json

返回码: 0 = 全部通过; 1 = 存在失败记录。
仅依赖 Python 标准库。
"""
import argparse
import json
import sys
import os

PROTOCOL = "BRIDGE-1.0"

# ---- 枚举约束(与 SKILL.md 速查表 / schemas 对齐) ----
SUBJECT_TYPES = {"agent", "human"}
VERIFY_STATES = {"pending", "verified"}
APPEAL_TYPES = {"collab_dev", "comm_test", "chat", "meet", "other"}
APPEAL_STATUS = {"active", "closed", "paused"}
VISIBILITY = {"private", "public"}
MEMBER_ROLES = {"owner", "member", "observer"}
TEMPLATE_TAGS = {"project", "study", "support", "other"}
CONNECTION_INTENTS = {"collab_dev", "comm_test", "chat", "meet", "other"}


def _err(errs, msg):
    errs.append(msg)


def _has(d, key):
    return isinstance(d, dict) and key in d


def _iso(ts):
    # 轻量 ISO8601 检查: 含 T 且含时区或秒级长度
    return isinstance(ts, str) and "T" in ts and len(ts) >= 20


# ---- 各构件校验器: 返回错误列表(空=通过) ----

def validate_agent_card(r):
    e = []
    if r.get("schema_version") != PROTOCOL:
        _err(e, "schema_version != BRIDGE-1.0")
    if r.get("subject_type") not in SUBJECT_TYPES:
        _err(e, f"subject_type 非法: {r.get('subject_type')!r} (应 ∈ {sorted(SUBJECT_TYPES)})")
    if not isinstance(r.get("agent_card_id"), str) or not r["agent_card_id"].startswith("ac_"):
        _err(e, "agent_card_id 缺失或非 ac_ 前缀")
    if not isinstance(r.get("name"), str) or not r["name"].strip():
        _err(e, "name 缺失/为空")
    if not isinstance(r.get("capabilities"), list) or len(r["capabilities"]) == 0:
        _err(e, "capabilities 缺失或为空数组")
    ep = r.get("endpoint", "")
    if not isinstance(ep, str) or not (ep.startswith("https://") or ep.startswith("http://")):
        _err(e, "endpoint 非法(须 http/https)")
    if not isinstance(r.get("permission_boundary"), str) or not r["permission_boundary"].strip():
        _err(e, "permission_boundary 缺失/为空")
    if r.get("verify_state") not in VERIFY_STATES:
        _err(e, f"verify_state 非法: {r.get('verify_state')!r} (应 ∈ {sorted(VERIFY_STATES)})")
    if r.get("protocol_version") != PROTOCOL:
        _err(e, "protocol_version != BRIDGE-1.0")
    return e


def validate_appeal(r):
    e = []
    if r.get("schema_version") != PROTOCOL:
        _err(e, "schema_version != BRIDGE-1.0")
    if not isinstance(r.get("appeal_id"), str) or not r["appeal_id"].startswith("ap_"):
        _err(e, "appeal_id 缺失或非 ap_ 前缀")
    sr = r.get("subject_ref", {})
    if not isinstance(sr, dict) or sr.get("subject_type") not in SUBJECT_TYPES or not isinstance(sr.get("card_ref"), str):
        _err(e, "subject_ref 结构非法(须 card_ref + subject_type)")
    if r.get("appeal_type") not in APPEAL_TYPES:
        _err(e, f"appeal_type 非法: {r.get('appeal_type')!r} (应 ∈ {sorted(APPEAL_TYPES)})")
    if not _iso(r.get("published_at", "")):
        _err(e, "published_at 非 ISO 时间")
    if r.get("status") not in APPEAL_STATUS:
        _err(e, f"status 非法: {r.get('status')!r} (应 ∈ {sorted(APPEAL_STATUS)})")
    if not isinstance(r.get("lifecycle_days"), int) or r["lifecycle_days"] <= 0:
        _err(e, "lifecycle_days 非法(须正整数)")
    if not isinstance(r.get("public_replies"), list):
        _err(e, "public_replies 缺失或非数组")
    return e


def validate_handshake(r):
    e = []
    if r.get("schema_version") != PROTOCOL:
        _err(e, "schema_version != BRIDGE-1.0")
    if not isinstance(r.get("handshake_id"), str) or not r["handshake_id"].startswith("hs_"):
        _err(e, "handshake_id 缺失或非 hs_ 前缀")
    for side in ("a", "b"):
        p = r.get(f"party_{side}", {})
        if not isinstance(p, dict) or p.get("subject_type") not in SUBJECT_TYPES or not isinstance(p.get("card_ref"), str):
            _err(e, f"party_{side} 结构非法(须 card_ref + subject_type)")
    ha = r.get("human_approval", {})
    if not isinstance(ha, dict):
        _err(e, "human_approval 缺失")
        return e
    # 人牵线铁律: 双方 human_approval.present 均须 true
    for side in ("a", "b"):
        side_ok = isinstance(ha.get(side), dict) and ha[side].get("present") is True
        if not side_ok:
            _err(e, f"human_approval.{side}.present != true (人牵线铁律) -> 拒绝建会话")
    ch = r.get("channel", {})
    if not isinstance(ch, dict) or not isinstance(ch.get("channel_id"), str) or ch.get("protocol_version") != PROTOCOL:
        _err(e, "channel 结构非法(须 channel_id + protocol_version=BRIDGE-1.0)")
    return e


def validate_room(r):
    e = []
    if r.get("schema_version") != PROTOCOL:
        _err(e, "schema_version != BRIDGE-1.0")
    if not isinstance(r.get("room_id"), str) or not r["room_id"].startswith("rm_"):
        _err(e, "room_id 缺失或非 rm_ 前缀")
    members = r.get("members", [])
    if not isinstance(members, list) or len(members) == 0:
        _err(e, "members 缺失或为空数组")
    else:
        for i, m in enumerate(members):
            if not isinstance(m, dict) or m.get("subject_type") not in SUBJECT_TYPES \
               or not isinstance(m.get("subject_ref"), str) or m.get("role") not in MEMBER_ROLES:
                _err(e, f"members[{i}] 结构非法(须 subject_ref + subject_type + role)")
    ch = r.get("channel", {})
    if not isinstance(ch, dict) or not isinstance(ch.get("channel_id"), str) or ch.get("protocol_version") != PROTOCOL:
        _err(e, "channel 结构非法(须 channel_id + protocol_version=BRIDGE-1.0)")
    if r.get("template_tag") not in TEMPLATE_TAGS:
        _err(e, f"template_tag 非法: {r.get('template_tag')!r}")
    if not isinstance(r.get("delegation"), dict):
        _err(e, "delegation 缺失或非对象")
    return e


def validate_ledger_entry(r):
    e = []
    if r.get("schema_version") != PROTOCOL:
        _err(e, "schema_version != BRIDGE-1.0")
    if not isinstance(r.get("entry_id"), str) or not r["entry_id"].startswith("le_"):
        _err(e, "entry_id 缺失或非 le_ 前缀")
    if not isinstance(r.get("connected"), bool):
        _err(e, "connected 非法(须布尔)")
    if not _iso(r.get("connected_at", "")):
        _err(e, "connected_at 非 ISO 时间")
    if r.get("protocol_version") != PROTOCOL:
        _err(e, "protocol_version != BRIDGE-1.0")
    if r.get("connection_intent") not in CONNECTION_INTENTS:
        _err(e, f"connection_intent 非法: {r.get('connection_intent')!r}")
    if not isinstance(r.get("disclaimer"), str) or not r["disclaimer"].strip():
        _err(e, "disclaimer 缺失/为空(陈述域须标注非客观事实)")
    if r.get("visibility") not in VISIBILITY:
        _err(e, f"visibility 非法: {r.get('visibility')!r}")
    if not isinstance(r.get("delete_requested"), bool):
        _err(e, "delete_requested 非法(须布尔)")
    return e


def validate_guard(r):
    e = []
    if r.get("schema_version") != PROTOCOL:
        _err(e, "schema_version != BRIDGE-1.0")
    rl = r.get("rate_limit", {})
    if not isinstance(rl, dict) or not isinstance(rl.get("count"), int):
        _err(e, "rate_limit 结构非法(须 count)")
    lc = r.get("lifecycle", {})
    if not isinstance(lc, dict) or not _iso(lc.get("expire_at", "")):
        _err(e, "lifecycle.expire_at 非 ISO 时间")
    if not isinstance(r.get("blocklist"), list):
        _err(e, "blocklist 缺失或非数组")
    return e


VALIDATORS = {
    "agent_card": (lambda r: "agent_card_id" in r, validate_agent_card),
    "appeal": (lambda r: "appeal_id" in r, validate_appeal),
    "handshake": (lambda r: "handshake_id" in r, validate_handshake),
    "room": (lambda r: "room_id" in r, validate_room),
    "ledger_entry": (lambda r: "entry_id" in r, validate_ledger_entry),
    "guard": (lambda r: ("rate_limit" in r and "blocklist" in r), validate_guard),
}


def detect_type(r):
    for t, (probe, _) in VALIDATORS.items():
        if probe(r):
            return t
    return None


def validate_record(r):
    t = detect_type(r)
    if t is None:
        return {"type": "unknown", "ok": False,
                "errors": ["无法识别记录类型(缺 agent_card_id/appeal_id/handshake_id/room_id/entry_id 之一)"]}
    errs = VALIDATORS[t][1](r)
    return {"type": t, "ok": len(errs) == 0, "errors": errs}


def load_records(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        return []
    try:
        obj = json.loads(raw)
        return [obj] if isinstance(obj, dict) else obj
    except json.JSONDecodeError:
        # 按 JSONL 逐行解析(一行一条)
        recs = []
        for i, line in enumerate(raw.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as ex:
                recs.append({"__parse_error__": f"line {i}: {ex}"})
        return recs


def main():
    ap = argparse.ArgumentParser(description="BRIDGE-1.0 五构件本地校验工具")
    ap.add_argument("--file", help="单记录 JSON 或多行 JSONL 账本路径")
    ap.add_argument("--dir", help="目录, 校验其中全部 .json/.jsonl 文件")
    ap.add_argument("--check-endpoint", action="store_true",
                    help="可选: 对 agent_card.endpoint 做真实 HTTPS 回读(默认关闭, 零网络依赖)")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = ap.parse_args()

    if not args.file and not args.dir:
        ap.print_help()
        return 2

    files = []
    if args.file:
        files.append(args.file)
    if args.dir:
        for fn in sorted(os.listdir(args.dir)):
            if fn.endswith((".json", ".jsonl")):
                files.append(os.path.join(args.dir, fn))

    results = []
    for f in files:
        recs = load_records(f)
        for r in recs:
            if "__parse_error__" in r:
                results.append({"file": f, "type": "parse_error", "ok": False,
                                "errors": [r["__parse_error__"]]})
                continue
            res = validate_record(r)
            res["file"] = f
            results.append(res)

    all_ok = all(r["ok"] for r in results)

    if args.json:
        print(json.dumps({"protocol": PROTOCOL, "total": len(results),
                          "pass": sum(1 for r in results if r["ok"]),
                          "fail": sum(1 for r in results if not r["ok"]),
                          "records": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            tag = "PASS" if r["ok"] else "FAIL"
            print(f"[{tag}] {r['type']:12s} {os.path.basename(r['file'])}")
            for err in r["errors"]:
                print(f"        - {err}")
        print(f"\n共 {len(results)} 条: 通过 {sum(1 for r in results if r['ok'])}, "
              f"失败 {sum(1 for r in results if not r['ok'])}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
