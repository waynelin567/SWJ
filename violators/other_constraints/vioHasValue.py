from ..vioConstraint import VioConstraint
from rdflib import Graph, URIRef, Literal
from pyshacl import ValidatorMgr
import random
from pyshacl.consts import SH
import string
from ..violationRecorder import ViolationRecorder
class VioHasValue(VioConstraint):
    def __init__(self, focus, values, shape, has_value):
        super().__init__(focus, values, shape)
        def get_specified_values(sp_values:list):
            ret = []
            for sp_value in sp_values:
                if isinstance(sp_value, URIRef):
                    ns = self.get_namespace_from_graph(sp_value)
                    if ns:
                        ret.append(str(sp_value)[len(ns):])
                    else: 
                        ret.append(str(sp_value))
                else:
                    ret.append(str(sp_value))
            return ret
        self.has_value:list = get_specified_values(has_value)
    def get_namespace_from_graph(self, uri_ref:str):
        namespace_manager = ValidatorMgr()._ont_graph.namespace_manager
        for prefix, namespace in namespace_manager.namespaces():
            if uri_ref.startswith(namespace):
                return namespace
        return None
    def simulate_typo(self, text, typo_type=None):
        new_text = text
        while True:
            typo_type = typo_type or random.choice(['substitution', 'insertion', 'deletion', 'transposition'])
            pos = random.randint(0, len(text) - 1)

            if typo_type == 'substitution' and len(text) > 1:
                new_char = random.choice(string.ascii_letters)
                new_text = text[:pos] + new_char + text[pos + 1:]
            elif typo_type == 'insertion':
                new_char = random.choice(string.ascii_letters)
                new_text = text[:pos] + new_char + text[pos:]
            elif typo_type == 'deletion' and len(text) > 1:
                new_text = text[:pos] + text[pos + 1:]
            elif typo_type == 'transposition' and len(text) > 1:
                if pos == len(text) - 1:
                    pos -= 1
                new_text = text[:pos] + text[pos + 1] + text[pos] + text[pos + 2:]
            if not (new_text in self.has_value):
                break
        return new_text
    def violate_for_node_shape(self):
        new_value = self.get_new_value(self.focus)
        for s, p, o in ViolationRecorder().output_graph.triples((None, None, self.focus)):
            ViolationRecorder().output_graph.remove((s, p, o))
            ViolationRecorder().output_graph.add((s, p, new_value))
        
        for s, p, o in ViolationRecorder().output_graph.triples((self.focus, None, None)):
            ViolationRecorder().output_graph.remove((s, p, o))
            ViolationRecorder().output_graph.add((new_value, p, o))
    def violate_for_property_shape(self):
        if len(self.values)==0:
            value_node = random.choice(self.has_value)
        else:
            value_node = random.choice(self.values)
        new_value = self.get_new_value(value_node)
        ViolationRecorder().output_graph.remove((self.focus, self.shape._path, value_node))
        ViolationRecorder().output_graph.add((self.focus, self.shape._path, new_value))
    def introduce_violation(self):
        if self.shape.is_property_shape:
            self.violate_for_property_shape()
        else:
            self.violate_for_node_shape()
        self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")
    def get_new_value(self, value_node):
        if isinstance(value_node, URIRef):
            ns = self.get_namespace_from_graph(value_node)
            if ns:
                new_value = URIRef(f"{ns}{self.simulate_typo(str(value_node)[len(ns):])}")
            else:
                new_value = URIRef(self.simulate_typo(str(value_node)))
        else:
            new_value = Literal(self.simulate_typo(str(value_node)))
        return new_value