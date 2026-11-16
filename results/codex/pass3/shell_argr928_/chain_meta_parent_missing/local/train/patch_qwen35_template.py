"""Add {% generation %} markers to Qwen3.5's chat template (needed by TRL assistant_only_loss).
Usage: python patch_qwen35_template.py in.jinja out.jinja"""
import sys
s = open(sys.argv[1]).read()
a = """        {%- if loop.index0 > ns.last_query_index %}
            {{- '<|im_start|>' + message.role + '\\n<think>\\n' + reasoning_content + '\\n</think>\\n\\n' + content }}
        {%- else %}
            {{- '<|im_start|>' + message.role + '\\n' + content }}
        {%- endif %}"""
b = """        {{- '<|im_start|>' + message.role + '\\n' }}
        {%- generation %}
        {%- if loop.index0 > ns.last_query_index %}
            {{- '<think>\\n' + reasoning_content + '\\n</think>\\n\\n' + content }}
        {%- else %}
            {{- content }}
        {%- endif %}"""
assert s.count(a) == 1, "assistant branch not found"
s = s.replace(a, b)
c = """            {%- endfor %}
        {%- endif %}
        {{- '<|im_end|>\\n' }}
    {%- elif message.role == "tool" %}"""
d = """            {%- endfor %}
        {%- endif %}
        {{- '<|im_end|>' }}
        {%- endgeneration %}
        {{- '\\n' }}
    {%- elif message.role == "tool" %}"""
assert s.count(c) == 1, "assistant end not found"
s = s.replace(c, d)
open(sys.argv[2], "w").write(s)
print("patched")
