"""Refresh the LFM template and verify empty/nonempty intent spans for both job templates."""
from data_v2_verify3_rules import ROOT, BASE, CACHE, af
from check_template_rendering import CaptureGeneration
from reference_trl_multimodal import prepare_multimodal_messages
from jinja2 import Environment
import hashlib, json, requests

info=requests.get('https://huggingface.co/api/models/LiquidAI/LFM3-VL-2B',timeout=60)
info.raise_for_status(); revision=info.json()['sha']
url=f'https://huggingface.co/LiquidAI/LFM3-VL-2B/resolve/{revision}/chat_template.jinja'
response=requests.get(url,timeout=60); response.raise_for_status()
path=CACHE/'lfm3_chat_template.jinja'; path.write_bytes(response.content)
source={'revision':revision,'url':url,'sha256':hashlib.sha256(response.content).hexdigest(),
        'equal_second_audit_template':response.content==(BASE/'verify_d33cb3c217/lfm3_chat_template.jinja').read_bytes()}
(CACHE/'model_template_source.json').write_text(json.dumps(source,indent=2))
cases=[]
for template_path in [path,ROOT/'train/qwen35_chat_template_gen.jinja']:
    for intent in ['', 'Type Art into the focused field.']:
        env=Environment(extensions=[CaptureGeneration,'jinja2.ext.loopcontrols']);env.captured=[]
        template=env.from_string(template_path.read_text())
        action='{"action_type":"input_text","text":"Art"}'
        msgs=af.build_messages('Find Art',[],for_trl=True)+[{'role':'assistant','content':action,'reasoning_content':intent}]
        training=template.render(messages=prepare_multimodal_messages(msgs,images=['placeholder']),add_generation_prompt=False,bos_token='')
        spans=list(env.captured); assert len(spans)==1
        span=spans[0];assert action in span and '<think>' in span and '</think>' in span and '<|im_end|>' in span
        assert (intent in span) if intent else not span.split('<think>',1)[1].split('</think>',1)[0].strip()
        prompt=template.render(messages=af.build_messages('Find Art',[],image='placeholder'),add_generation_prompt=True,bos_token='',enable_thinking=True)
        assert training.startswith(prompt)
        cases.append({'template':str(template_path.relative_to(ROOT)),'template_sha256':hashlib.sha256(template_path.read_bytes()).hexdigest(),
                      'intent':intent,'generation_span':span,'training_starts_with_inference_prompt':True})
(CACHE/'template_render.json').write_text(json.dumps({'cases':cases,'scope':'Character spans and TRL message-shape reference; no GPU or tokenizer-mask run.'},indent=2))
print(json.dumps({'source':source,'cases':cases},indent=2))
