"""MobileWorld's official MAI-UI agent (mobile_world.agents.implementations.mai_ui_agent, commit a026188) with ONE screenshot
per step (runtime_conf history_n=1; the official default is 3), matching the screenshot budget of the other arms: v4
(one screenshot), GUI-Owl's official MobileWorld agent (history_n=1 by default) and MAI-UI's AndroidWorld arm
(maiui_2b_matched_q8_0, --maiui_images=1). Everything else is the official agent unchanged (prompt, parsing, temperature 0,
top_p 1, max_tokens 2048, action mapping). The model server is MAI-UI-2B Q8_0 (its Q4_K_M output degenerates,
results/maiui_quant_check.md) with the same llama.cpp flags as its AndroidWorld arm.
Load with: mw eval --agent_type <this file> --model_name MAI-UI-2B ... (MobileWorld loads the first BaseAgent subclass
defined in this module; the official class is imported as a module attribute so it is not picked instead).
"""
from typing import Any

import mobile_world.agents.implementations.mai_ui_agent as _official


class MAIUIOneScreenshotAgent(_official.MAIUINaivigationAgent):
    def __init__(self, llm_base_url: str, model_name: str, api_key: str = "empty",
                 runtime_conf: dict[str, Any] | None = None, **kwargs):
        # file-loaded agents do not get `tools` from the registry; pass the env's tools as the registry path does
        if "tools" not in kwargs and kwargs.get("env") is not None:
            kwargs["tools"] = kwargs["env"].tools
        super().__init__(llm_base_url=llm_base_url, model_name=model_name, api_key=api_key,
                         runtime_conf={**(runtime_conf or {}), "history_n": 1}, **kwargs)
