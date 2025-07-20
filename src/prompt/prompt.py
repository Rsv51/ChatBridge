# copy from https://linux.do/t/topic/769154
TOOLCALL_PRMPT = """你可以使用以下工具来帮助你解决问题：

工具列表：

{TOOLS_LIST}

当你判断需要使用工具时，必须严格遵循以下格式：

1. 回答的第一行必须是：
FC_USE
没有任何前、尾随空格，全大写。

2. 然后，在回答的最后，请使用如下格式输出函数调用（使用 XML 语法）：

<function_call>
  <tool>tool_name</tool>
  <args>
    <key1>value1</key1>
    <key2>value2</key2>
  </args>
</function_call>

注意事项：
- 如果你不需要调用工具，请直接回答问题。
- 除非你确定需要调用工具，否则不要输出 FC_USE。
- 你只能调用一个工具。
- 保证输出的 XML 是有效的、严格符合上述格式。
- 不要随便更改格式。
- 你单回合只能调用一次工具。

现在请准备好遵循以上规范。
"""
