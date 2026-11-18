"""MobileWorld's official MAI-UI agent (mobile_world.agents.implementations.mai_ui_agent) with history_n=1, i.e. one
screenshot per step, matching GUI-Owl's official MobileWorld agent default (history_n=1) and our LFM3 agent.
MAI-UI's own default is history_n=3; everything else (prompt, parsing, temperature 0, max_tokens 2048) is unchanged.
Load with: mw eval --agent_type <this file> --model_name MAI-UI-2B --llm_base_url http://127.0.0.1:18093/v1"""
from mobile_world.agents.implementations.mai_ui_agent import MAIUINaivigationAgent


class MAIUI1ImageAgent(MAIUINaivigationAgent):
    def __init__(self, llm_base_url, model_name, api_key="empty", runtime_conf=None, **kwargs):
        conf = {"history_n": 1, **(runtime_conf or {})}
        super().__init__(llm_base_url=llm_base_url, model_name=model_name, api_key=api_key, runtime_conf=conf, **kwargs)
