# Skill-B: 智能体连接通用底座

让开发者三分钟内把智能体登记上网、连上别的智能体。零账号、零自建业务服务器、连接不经我手。

## 这是什么

一套纯数据 schema 规范（SB-1.0）+ 本地校验工具协议，覆盖智能体协作全链：登记 → 发布诉求 → 握手连通 → 协作房间 → 连接账本。

## 安装

Hermes 用户执行：hermes skills install skill-b-connect-base <SKILL.md 直链>
（其他 Agent 框架：直接引用 schemas/ 下 JSON 规范，无运行依赖）

## 3 分钟上手

1. 复制 examples/agent_card.example.json 改好你的智能体能力卡；
2. 本地校验通过后提交登记；
3. 找到想连的智能体，双方确认（人牵线）→ 生成握手凭证 → 双方端点直连，完事。

## 文档

- SKILL.md 本体说明
- PROTOCOL.md 协议版本规范 SB-1.0
- schemas/ 六套 schema 规范（agent_card / handshake / appeal / room / ledger_entry / guard）
- examples/ 对应示例

## 边界

人牵线铁律（智能体不脱离人管控）/ 零服务器（点对点直连）/ 不限定使用动机。详见 SKILL.md。
