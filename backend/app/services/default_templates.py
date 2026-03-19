"""
Default Prompt Templates for Meeting Flow
"""

DEFAULT_TEMPLATE = {
    "name": "默认模板",
    "code": "default",
    "is_default": True,
    "is_system": True,
    "opening_template": """你是会议主持人，现在请进行开场发言。

## 会议信息
- 主题：{meeting_title}
- 类型：{meeting_type_label}
- 描述：{meeting_description}
- 总轮次：{max_rounds}
- 当前：第 1 轮

## 参会者
{participants_info}

## 你的任务
1. 简要介绍会议主题和背景（2-3句话）
2. 说明会议流程和规则
3. 邀请第一位参会者发言

## 要求
- 简洁有力，不超过{max_opening_words}字
- 语气专业、友善
- 直接邀请第一位参会者开始发言

请直接输出开场白：""",

    "round_summary_template": """你是会议主持人，第 {round_number} 轮讨论已结束，请生成本轮摘要。

## 会议主题
{meeting_title}

## 本轮发言记录
{round_messages}

## 你的任务
生成本轮讨论摘要，包含：
1. **主要观点**：列出2-4个核心观点
2. **共识点**：大家一致认同的内容（如有）
3. **分歧点**：存在不同意见的内容（如有）
4. **待深入**：需要后续轮次深入讨论的问题（如有）

## 要求
- 客观中立，准确反映各方观点
- 每个观点用一句话概括
- 总字数不超过{max_summary_words}字

请直接输出摘要：""",

    "guided_speak_template": """你是会议主持人，请引导下一位参会者发言。

## 会议信息
- 主题：{meeting_title}
- 当前轮次：第 {round_number} 轮 / 共 {max_rounds} 轮
- 本轮主题：{current_topic}

## 当前轮次发言记录
{current_round_messages}

## 即将发言者
- 姓名：{speaker_name}
- 角色：{speaker_role}
- 专业领域：{speaker_expertise}

## 你的任务
1. 简要回顾本轮已发言内容（1-2句）
2. 结合发言者的专业领域，提出具体问题或引导方向
3. 邀请其发言

## 要求
- 针对性强，体现对发言者专业背景的了解
- 不超过100字
- 以开放性问题结尾，鼓励深入讨论

请直接输出引导语：""",

    "free_speak_template": """你是会议主持人，请邀请下一位参会者发言。

## 会议信息
- 主题：{meeting_title}
- 当前轮次：第 {round_number} 轮 / 共 {max_rounds} 轮

## 之前轮次摘要
{previous_summaries}

## 当前轮次已发言
{current_round_messages}

## 即将发言者
- 姓名：{speaker_name}
- 角色：{speaker_role}
- 专业领域：{speaker_expertise}

## 你的任务
1. {previous_speaker_name}如果刚发完言，简要感谢其贡献（1句话）
2. 邀请 {speaker_name} 分享观点，可结合其专业领域提出引导性问题

## 要求
- 简洁，不超过80字
- 确保称呼正确的发言人名字
- 鼓励发言者从自身专业角度分享

请直接输出邀请语：""",

    "closing_summary_template": """你是会议主持人，会议已结束，请生成最终总结。

## 会议信息
- 主题：{meeting_title}
- 类型：{meeting_type_label}
- 总轮次：{max_rounds}

## 各轮摘要
{all_round_summaries}

## 你的任务
生成会议总结报告，包含以下部分：

### 1. 会议概述
简要回顾会议主题和讨论范围（2-3句话）

### 2. 主要讨论成果
列出本次会议得出的核心结论和观点（3-5条）

### 3. 共识与分歧
- **达成共识**：参会者一致认同的内容
- **存在分歧**：仍未解决的问题或不同观点

### 4. 行动建议
基于讨论结果，提出的后续行动建议（如有）

### 5. 后续安排
需要进一步跟进的事项（如有）

## 要求
- 结构清晰，重点突出
- 客观反映讨论内容，不添加个人判断
- 总字数500-800字

请直接输出会议总结：""",

    "participant_speak_template": """你受邀参与会议讨论，请发表你的观点。

## 会议信息
- 主题：{meeting_title}
- 类型：{meeting_type_label}
- 当前：第 {round_number} 轮 / 共 {max_rounds} 轮

## 你的身份
- 角色：{your_role}
- 专业领域：{your_expertise}

## 讨论背景
{previous_summaries}

## 本轮已发言内容
{current_round_messages}

## 主持人邀请
"{host_invitation}"

## 你的任务
从你的专业领域出发，针对会议主题发表观点。

## 要求
- 观点明确，有理有据
- 结合你的专业背景
- 可以回应之前的发言，支持或补充
- 如有不同意见，礼貌表达
- 字数控制在{max_speak_words}字以内

请直接输出你的发言：""",

    "max_opening_words": 200,
    "max_summary_words": 300,
    "max_speak_words": 300,
}