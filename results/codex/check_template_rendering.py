"""Character-level template verification, not a live GPU/token-mask test.

Uses the actual local served GGUF template and the checked-in Qwen template,
plus a verbatim excerpt of TRL 1.16's multimodal preparation helper.
"""
import importlib.util
import json
from pathlib import Path
import sys
from jinja2 import Environment, nodes
from jinja2.ext import Extension
from reference_trl_multimodal import prepare_multimodal_messages

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "train"))
import agent_format


class CaptureGeneration(Extension):
    tags = {"generation"}

    def parse(self, parser):
        start = next(parser.stream)
        body = parser.parse_statements(["name:endgeneration"],drop_needle=True)
        return nodes.CallBlock(self.call_method("capture"),[],[],body).set_lineno(start.lineno)

    def capture(self, caller):
        content = caller()
        self.environment.captured.append(content)
        return content


def main():
    goal, intent = "Open Settings", "Tap the Settings icon."
    action = '{"action_type":"click","point_2d":[500,500]}'
    data_messages = agent_format.build_messages(goal,[],for_trl=True)
    data_messages.append({"role":"assistant","content":action,"reasoning_content":intent})
    train_messages = prepare_multimodal_messages(data_messages,images=["placeholder"])
    inference_messages = agent_format.build_messages(goal,[],image="placeholder")
    assert train_messages[:-1] == inference_messages
    rows = []
    for path in (ROOT / "results/codex/served_gguf_chat_template.jinja",ROOT / "train/qwen35_chat_template_gen.jinja"):
        env = Environment(extensions=[CaptureGeneration,"jinja2.ext.loopcontrols"])
        env.captured = []
        template = env.from_string(path.read_text())
        training = template.render(messages=train_messages,add_generation_prompt=False)
        assistant_spans = list(env.captured)
        assert len(assistant_spans)==1 and intent in assistant_spans[0] and action in assistant_spans[0]
        assert "<think>" in assistant_spans[0] and "</think>" in assistant_spans[0] and "<|im_end|>" in assistant_spans[0]
        assert goal not in assistant_spans[0]
        for thinking in (True,False):
            env.captured=[]
            prompt=template.render(messages=inference_messages,add_generation_prompt=True,enable_thinking=thinking)
            assert not env.captured
            if thinking:
                assert training.startswith(prompt)
            rows.append({"template":str(path.relative_to(ROOT)),"enable_thinking":thinking,
                         "training_starts_with_inference_prompt":training.startswith(prompt),
                         "inference_suffix":prompt[-85:],"generation_span":assistant_spans[0]})
    (ROOT / "results/codex/template_render_checks.json").write_text(json.dumps({
        "trl_prepared_prompt_equals_offline_prompt":True,"cases":rows,
        "scope":"Character spans only. Does not verify tokenizer-level assistant_masks, GPU execution, or the training VM revision."
    },indent=2)+"\n")
    print(json.dumps(rows,indent=2))


if __name__=="__main__":
    main()
