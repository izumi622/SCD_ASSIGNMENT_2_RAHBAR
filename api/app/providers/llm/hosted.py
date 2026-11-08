"""OpenAI-compatible hosted chat provider; keys are supplied only via Secret."""
from __future__ import annotations
import httpx
from ...config import Settings
from ...schemas import Answer, Passage
from .ollama import make_prompt, _SYSTEM

class HostedProvider:
    name='hosted'
    def __init__(self,settings: Settings) -> None: self.settings=settings
    def generate(self,question: str,passages: list[Passage]) -> Answer:
        if not self.settings.hosted_base_url or not self.settings.llm_api_key:
            raise RuntimeError('Hosted provider needs HOSTED_BASE_URL and LLM_API_KEY Secret')
        url=self.settings.hosted_base_url.rstrip('/')+'/chat/completions'
        req={'model':self.settings.llm_model,'temperature':self.settings.temperature,
             'response_format':{'type':'json_object'},
             'messages':[{'role':'system','content':_SYSTEM},
                         {'role':'user','content':make_prompt(question,passages)}]}
        with httpx.Client(timeout=httpx.Timeout(90,connect=5)) as http:
            for attempt in range(2):
                try:
                    response=http.post(url,json=req,headers={'Authorization':f'Bearer {self.settings.llm_api_key}'})
                    response.raise_for_status()
                    raw=response.json()['choices'][0]['message']['content']
                    return Answer.model_validate_json(raw)
                except (ValueError,KeyError,TypeError):
                    if attempt: break
                req['messages'].append({'role':'user','content':'Return only schema-valid JSON.'})
        return Answer(reasoning='validation fallback',answer='Unable to validate the generated response.',
                      citations=[],answered_from_context=False,confidence='low')
