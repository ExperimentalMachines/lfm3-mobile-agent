"""Reproduce native empty-think rendering and the new filter-failure fixtures."""
from data_v2_verify_rules import ROOT, CACHE, rules, af
from check_template_rendering import CaptureGeneration
from reference_trl_multimodal import prepare_multimodal_messages
from jinja2 import Environment
from unittest.mock import patch
import ast, hashlib, json, subprocess

p=CACHE/'lfm3_chat_template.jinja'
env=Environment(extensions=[CaptureGeneration,'jinja2.ext.loopcontrols']);env.captured=[]
action='{"action_type":"input_text","text":"Art"}'
msgs=af.build_messages('Find Art',[],for_trl=True)+[{'role':'assistant','content':action,'reasoning_content':''}]
template=env.from_string(p.read_text())
training=template.render(messages=prepare_multimodal_messages(msgs,images=['placeholder']),add_generation_prompt=False,bos_token='')
span=env.captured[0]
assert '<think></think>'+action in span and '<|im_end|>' in span
prompt=template.render(messages=af.build_messages('Find Art',[],image='placeholder'),add_generation_prompt=True,bos_token='',enable_thinking=True)
assert training.startswith(prompt)
render={'template_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'generation_span':span,
        'training_starts_with_thinking_inference_prompt':training.startswith(prompt),
        'scope':'Actual model template and TRL message-shape reference; character spans only, no tokenizer or GPU batch.'}
(CACHE/'empty_intent_render.json').write_text(json.dumps(render,indent=2))

tree=ast.parse((ROOT/'data/build_v2_mix.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_ocr_pending')
ns={'PENDING_RE':rules['PENDING_RE']}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'builder-ocr-rule','exec'),ns)
with patch('subprocess.run',return_value=subprocess.CompletedProcess(['tesseract'],7,stdout='',stderr='simulated OCR failure')):
    pending=ns['_ocr_pending'](('file',str(CACHE/'visual/odyssey_24.png')))
examples=[
('Chocolate chip cookies','Locate a chocolate chip cookie recipe, generate a shopping list of key ingredients using Google Keep, and proceed to add those items to your cart on Ebay, utilizing Opera for browsing.'),
('properties of cube','Open Chrome to search for information about the properties of a Cube and then use Google Docs to create a brief document summarizing your findings.')]
info=["Open Eventbrite. Search for events by 'Music' under online events. Choose the second event in the list. Get the event's duration information.",
      'Open IMDB. Search for celebrity "Leonardo DiCaprio". Go to his biography section. Check his birthdate and birthplace.']
out={'ocr_nonzero_exit_fixture':{'returncode':7,'stdout':'','pending_result':pending,'would_pass_worker_pending_check':not pending},
     'benign_near_miss_rejections':[{'text':t,'goal':g,'rejected':rules['near_miss'](t,g)} for t,g in examples],
     'info_goal_misses':[{'goal':g,'regex_matches':bool(rules['INFO_GOAL_RE'].search(g))} for g in info]}
(CACHE/'new_filter_probes.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'render':render,'filters':out},indent=2))
