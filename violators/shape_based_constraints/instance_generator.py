from rdflib import URIRef, Literal, Graph
import json
from pyshacl import ValidatorMgr, validate
from rdflib.namespace import RDF, SH
from time import sleep
from buildingmotif.namespaces import OWL
APIKEY = "your_api_key"
class InstanceGenerator():
    def __init__(self, mapping:dict, sub_graph:Graph, template:Graph, manifest_graph:Graph, value_shape_name:URIRef, subgraph_examples:list[Graph]):
        print("shape template",template.serialize())
        self.head_name = self.get_head_name(mapping)
        self.sg = sub_graph
        self.manifest_graph = Graph() + manifest_graph
        self.template = Graph() + template
        self.subgraph_examples:list[Graph] = subgraph_examples
        for prefix, namespace in ValidatorMgr()._ont_graph.namespace_manager.namespaces():
            self.manifest_graph.bind(prefix, namespace)
            self.sg.bind(prefix, namespace)
            self.template.bind(prefix, namespace)
        for prefix, namespace in ValidatorMgr()._data_graph.namespace_manager.namespaces():
            self.manifest_graph.bind(prefix, namespace)
            self.sg.bind(prefix, namespace)
            self.template.bind(prefix, namespace)
        self.value_shape_name = value_shape_name
        self.ent_names_to_gen:list = [] 
    def get_head_name(self, mapping):
        param_name = None
        for k, v in mapping.items():
            if v == URIRef("urn:___param___#name"):
                param_name = k
        return param_name
    def get_unmatched_objects_of_sub(self, templ_sub, matched_sub):
        tmp_ls = []
        for _, p, o in self.template.triples((templ_sub, None, None)):
            if str(o).startswith("urn:___param___") and len(list(self.sg.triples((matched_sub, p, None)))) == 0:
                tmp_ls.append(o)
        if len(tmp_ls) == 0:
            should_continue = False
            return should_continue
        else: 
            self.ent_names_to_gen.append(tmp_ls)
            should_continue = True
            return should_continue
    def gen_instance(self):
        self.get_unmatched_objects_of_sub(URIRef("urn:___param___#name"), self.head_name)
        if len(self.ent_names_to_gen) > 0:
            while True:
                should_continues = []
                for element in self.ent_names_to_gen[-1]:
                    should_continue = self.get_unmatched_objects_of_sub(element, element)
                    should_continues.append(should_continue)
                if True in should_continues:
                    pass
                else:
                    break
    def get_unmatched_objects_of_sub_wo_subgraph(self, templ_sub):
        tmp_ls = []
        for _, p, o in self.template.triples((templ_sub, None, None)):
            if str(o).startswith("urn:___param___"):
                tmp_ls.append(o)
        if len(tmp_ls) == 0:
            should_continue = False
            return should_continue
        else:
            self.ent_names_to_gen.append(tmp_ls)
            should_continue = True
            return should_continue
    def gen_instance_wo_subgraph(self):
        self.get_unmatched_objects_of_sub_wo_subgraph(URIRef("urn:___param___#name"))
        if len(self.ent_names_to_gen) > 0:
            while True:
                should_continues = []
                for k in self.ent_names_to_gen[-1]:
                    should_continue = self.get_unmatched_objects_of_sub_wo_subgraph(k)
                    should_continues.append(should_continue)
                if True in should_continues:
                    pass
                else:
                    break
    def gen_ent_names(self):
        for k in self.ent_names_to_gen:
            ng = NameGenerator(k, self.sg, self.template, self.subgraph_examples)
            name = ng.run()
            self.change_name(k, name)
            if k == URIRef("urn:___param___#name"):
                self.head_name = name
    def change_name(self, key, name):
        for s, p, o in self.sg.triples((None, None, None)):
            if s == key:
                self.sg.remove((s, p, o))
                self.sg.add((name, p, o))
            if o == key:
                self.sg.remove((s, p, o))
                self.sg.add((s, p, name))
    def check_sat_value_shape(self):
        self.manifest_graph.add((self.value_shape_name, SH.targetNode, self.head_name))
        conforms, report_graph, report_text = validate(self.sg, shacl_graph=self.manifest_graph, ont_graph=ValidatorMgr()._ont_graph)
        assert conforms, report_text
    def run(self):
        if self.head_name:
            self.gen_instance()
        else: 
            self.gen_instance_wo_subgraph()
            #head_name_context = list(self.template.objects(URIRef("urn:___param___#name"), RDF.type))
            self.ent_names_to_gen.append([URIRef("urn:___param___#name")])
        self.ent_names_to_gen = [x for ls in self.ent_names_to_gen for x in ls]
        self.ent_names_to_gen = sorted(self.ent_names_to_gen, key=lambda x: len(str(x)))
        self.gen_ent_names()
        if self.subgraph_examples and len(self.subgraph_examples[0])!=len(self.sg):
            sf = SubgraphFixer(self.sg, self.subgraph_examples[0])
            self.sg = sf.fix_graph()
        self.check_sat_value_shape()
        return self.sg, self.head_name

class NameGenerator():
    def __init__(self, param_name, subgraph, templ:Graph, subgraph_examples:list[Graph]):
        self.template:Graph = templ
        self.param_name = param_name
        self.sg:Graph = subgraph
        self._post_process_sg()
        self.subgraph_examples:list[Graph] = subgraph_examples
        self.prompt = self.gen_prompt()
        self.system_msg = "You are a creative expert in generating unique names for entities." 
        self.apikey = APIKEY 
        self.model_name = "openai/gpt-4o"
    def _post_process_sg(self):
        self.sg.remove((None, None, URIRef("urn:my_temp_shape_name")))
        self.sg.remove((URIRef("urn:my_temp_shape_name"), None, None))
        for s, p, o in self.sg.triples((None, None, None)):
            if str(s).startswith("http://example.org"):
                self.sg.remove((s, p, o))
            if str(o).startswith("http://example.org"):
                self.sg.remove((s, p, o))
            if str(s).startswith("urn:my_site_constraints"):
                self.sg.remove((s, p, o))
            if str(o).startswith("urn:my_site_constraints"):
                self.sg.remove((s, p, o))
    def gen_prompt(self):
        s = f"Generate an entity name to replace {self.param_name} in the following graph\n"
        s += self.sg.serialize()
        s += f"Your answer must be semantically similar to the corresponding entity in the following example but not exactly identical\n"
        for sg in self.subgraph_examples:
            sg_serialized = sg.serialize()
            filtered_lines = [line for line in sg_serialized.split("\n") if not line.startswith("@prefix")]
            s += "\n".join(filtered_lines)
        s += f"Compare with the example, observe if {self.param_name} should be a URIRef. If so, make it a valid URIRef; Otherwise, make it a Literal\n"
        s += "Return your answer in json without explanations. {\"answer\":your answer, \"is URIRef\":true/false}"
        print(s)
        return s
    def run(self):
        from openai import OpenAI
        sleep(3)
        self.client = OpenAI(api_key=self.apikey)
        completion = self.client.chat.completions.create(
            model = self.model_name,
            messages = [
                {"role":"system", "content":self.system_msg}, 
                {"role":"user", "content":self.prompt}
            ],
            temperature=0.2
        )
        print("completion", completion)
        try:
            raw_response = completion.choices[0].message.content
            response = raw_response.replace("\n", " ")
            response_json:dict = json.loads(response[response.find("{"):response.rfind("}")+1])
            answer = response_json.get("answer", "No answer found")
            is_URIRef = response_json.get("is URIRef", False)
        except:
            answer = "Error decoding JSON. "
            is_URIRef = False
        if is_URIRef:
            return URIRef(answer)
        else:
            return Literal(answer)
class SubgraphFixer():
    def __init__(self, sg, sg_example):
        self.sg:Graph = sg
        self.sg_example:Graph = sg_example
        self.system_msg = "You are an expert in adding missing triples to make graphs isomorphic to a given graph." 
        self.apikey = APIKEY 
        self.model_name = "openai/gpt-4o"
        self.prompt = self.gen_prompt()
    def gen_prompt(self):
        s = f"Add triples to the following graph\n"
        s += self.sg.serialize()
        s += f"so that it becomes isomorphic to the following graph except for the entity names\n"
        ex_serialized = self.sg_example.serialize()
        #filtered_lines = [line for line in ex_serialized.split("\n") if not line.startswith("@prefix")]
        #s += "\n".join(filtered_lines)
        s += ex_serialized
        s += "Return your answer in json and SPARQL without explanations. {\"answer\":INSERT DATA {...} }"
        print(s)
        return s
    def fix_graph(self) -> Graph:
        from openai import OpenAI
        sleep(3)
        self.client = OpenAI(api_key=self.apikey)
        completion = self.client.chat.completions.create(
            model = self.model_name,
            messages = [
                {"role":"system", "content":self.system_msg}, 
                {"role":"user", "content":self.prompt}
            ],
            temperature=0.2
        )
        print("completion", completion)
        try:
            raw_response = completion.choices[0].message.content
            response = raw_response.replace("\n", " ")
            response_json:dict = json.loads(response[response.find("{"):response.rfind("}")+1])
            answer = response_json.get("answer", "No answer found")
            self.sg.update(answer) 
        except:
            answer = "Error decoding JSON. "
        return self.sg
