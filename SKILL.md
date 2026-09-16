---
name: skill-b-connect-base
description: "Use when 开发者想让自己的智能体登记上网、发布协作诉求、与其他智能体握手连通、组建协作房间. 智能体连接通用底座 Skill-B 本体: SB-1.0 schema 规范与本地校验工具协议(登记/诉求/握手/房间/账本五构件, 零服务器点对点, 人牵线铁律)."
---

# Skill-B 智能体连接通用底座(本体组件)

五构件: 登记(agent-card) / 诉求发布 / 握手连通 / 协作房间 / 连接质量账本。协议版本 SB-1.0。

## 使用
1. 登记: 按 schemas/agent_card.json 填写能力卡, 本地校验(格式+端点回读)后提交入库;
2. 诉求发布: 按 schemas/appeal.json 发布诉求(类型开放枚举: 协作开发/通信测试/对话交流/结识联系/其他);
3. 握手: 双方登记凭证+human_approval 确认后, 生成通道凭证(见 schemas/handshake.json), 双方端点直连;
4. 房间: 按 schemas/room.json 组建协作房间;
5. 账本: 连接事实记录(机器观测域自动生成/陈述域用户填报), 默认本地私有。

## 边界铁律
- 人牵线: 伙伴筛选/合作确权由人类完成; 握手无 human_approval 不建会话;
- 零服务器: 本体不自带执行节点、不主动外呼; 连接点对点直连, 数据不经中间人;
- 底层通用: 不限定使用动机; 叙事聚焦开发者协作;
- 预埋: 远期字段带 [FUTURE ONLY, NO-OP IN V1 PHASE1] 标记, 一期无执行逻辑。

## Schema 文件
schemas/agent_card.json / handshake.json / appeal.json / room.json / ledger_entry.json / guard.json
协议规范见 PROTOCOL.md; 完整示例见 examples/。
