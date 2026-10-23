import copy
import json
import unittest
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from app.models import Filters, SearchRequest, Answer
from app.retrieval import Index, matches
from app.agent import recommend, parse_json, validate_grounding, tool_product
from app.main import app


class Message:
    def __init__(self, content=None, calls=None):self.content=content;self.tool_calls=calls
    def model_dump(self, **kwargs):
        return {'role':'assistant','content':self.content,'tool_calls':[{'id':c.id,'type':'function','function':{'name':c.function.name,'arguments':c.function.arguments}} for c in self.tool_calls or []]}


def call(name='search_specs', args=None):
    return NS(id='call1',function=NS(name=name,arguments=json.dumps(args if args is not None else {'query':'Logitech M100'})))


class FakeClient:
    def __init__(self, messages):self.messages=iter(messages);self.calls=[];self.chat=NS(completions=self)
    def create(self, **kwargs):self.calls.append(copy.deepcopy(kwargs));return NS(choices=[NS(message=next(self.messages))])


def valid_answer(pid='logitech-m100'):
    return {'summary':'A documented wired option.','recommendations':[{'product_id':pid,'reason':'USB wired mouse in the catalog.','tradeoff':'No Bluetooth listed.','citation_ids':[pid]}],'limitations':['Reference price is not a live offer.'],'abstain':False}


class GearMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.index=Index()

    def test_data_provenance(self):
        self.assertEqual(len(self.index.products),21)
        for p in self.index.products:
            self.assertEqual(p['currency'],'USD');self.assertTrue(p['sources']);self.assertTrue(p['variant'])
            for s in p['sources']:self.assertTrue(s['url'].startswith('https://'))

    def test_tool_observation_has_single_citation_namespace(self):
        p=tool_product(self.index.products[0])
        self.assertEqual(p['citation_id'],p['id']);self.assertNotIn('source_ids',p)
        self.assertTrue(all('id' not in s for s in p['sources']))

    def test_unknown_weight_never_passes_weight_filter(self):
        p=self.index.by_id['keychron-m4-4k']
        self.assertIsNone(p['weight_g']);self.assertFalse(matches(p,Filters(max_weight=100)))

    def test_filters_are_conjunctive_and_unknown_hand_does_not_pass(self):
        for hit in self.index.search('gaming',Filters(budget=70,max_weight=60,connection='wired')):
            self.assertTrue(matches(hit['product'],Filters(budget=70,max_weight=60,connection='wired')))
        self.assertFalse(matches(self.index.by_id['keychron-m7-8k'],Filters(handedness='right')))

    def test_thai_query_and_impossible_constraints(self):
        ids=[h['product']['id'] for h in self.index.search('แนวตั้ง มือซ้าย',Filters(handedness='left',budget=100))]
        self.assertEqual(ids,['logitech-lift-left'])
        self.assertEqual(self.index.search('wireless mouse',Filters(budget=10,connection='bluetooth')),[])

    def test_schema_rejects_unknown_fields(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):SearchRequest(question='find mouse',filters={'execute':'shell'})
        with self.assertRaises(ValidationError):Filters(budget=-1)

    def test_json_fence(self):
        self.assertEqual(parse_json('```json\n{"x":1}\n```'),{'x':1})

    def test_valid_grounding(self):
        p=self.index.by_id['logitech-m100'];a=Answer.model_validate(valid_answer())
        self.assertEqual(validate_grounding(a,{p['id']:p},Filters(budget=10)),a)

    def test_hallucinated_or_overbudget_product_rejected(self):
        p=self.index.by_id['logitech-m100']
        with self.assertRaises(ValueError):validate_grounding(Answer.model_validate(valid_answer('invented')),{},Filters())
        with self.assertRaises(ValueError):validate_grounding(Answer.model_validate(valid_answer()),{p['id']:p},Filters(budget=1))

    def test_foreign_citation_and_duplicates_rejected(self):
        p=self.index.by_id['logitech-m100'];a=valid_answer();a['recommendations'][0]['citation_ids']=['invented']
        with self.assertRaises(ValueError):validate_grounding(Answer.model_validate(a),{p['id']:p},Filters())
        a=valid_answer();a['recommendations']*=2
        with self.assertRaises(ValueError):validate_grounding(Answer.model_validate(a),{p['id']:p},Filters())

    def test_agent_tool_round_trip_and_stop(self):
        client=FakeClient([Message(calls=[call()]),Message(content=json.dumps(valid_answer()))])
        out=recommend(SearchRequest(question='USB mouse',filters=Filters(budget=10)),self.index,client)
        self.assertEqual(out['answer']['recommendations'][0]['product_id'],'logitech-m100')
        self.assertEqual(out['mode'],'live_llm');self.assertEqual(len(client.calls),2)
        self.assertEqual(client.calls[1]['messages'][-1]['role'],'tool')

    def test_unknown_tool_is_not_executed(self):
        client=FakeClient([Message(calls=[call('shell',{'query':'rm -rf anything'})]),Message(content=json.dumps({'summary':'No evidence','recommendations':[],'limitations':[],'abstain':True}))])
        out=recommend(SearchRequest(question='find mouse'),self.index,client)
        self.assertIn('error',out['trace'][0]);self.assertTrue(out['answer']['abstain'])

    def test_step_cap(self):
        client=FakeClient([Message(content='I promise it works')]*2)
        with self.assertRaisesRegex(RuntimeError,'STEP_LIMIT'):recommend(SearchRequest(question='find mouse'),self.index,client,max_steps=2)

    def test_repeated_queries_blocked(self):
        client=FakeClient([Message(calls=[call()]),Message(calls=[call()]),Message(content=json.dumps(valid_answer()))])
        out=recommend(SearchRequest(question='M100'),self.index,client)
        self.assertIn('Repeated query',out['trace'][1]['error'])

    def test_http_catalog_validation_and_search(self):
        client=TestClient(app)
        self.assertEqual(client.get('/api/catalog').status_code,200)
        self.assertEqual(client.post('/api/search',json={'question':'a'}).status_code,422)
        response=client.post('/api/search',json={'question':'Bluetooth','filters':{'budget':10,'connection':'bluetooth'}})
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['hits'],[])


if __name__=='__main__':unittest.main(verbosity=2)
