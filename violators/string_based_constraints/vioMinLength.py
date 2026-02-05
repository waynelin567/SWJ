from ..vioConstraint import VioConstraint
from rdflib import Graph, URIRef, Literal
from pyshacl import ValidatorMgr
import random
from pyshacl.consts import SH
from ..violationRecorder import ViolationRecorder
class VioMinLength(VioConstraint):
    def __init__(self, focus, values, shape, min_length):
        super().__init__(focus, values, shape)
        self.min_length:int = int(min_length) 
    def get_namespace_from_graph(self, uri_ref:str):
        namespace_manager = ValidatorMgr()._ont_graph.namespace_manager
        for prefix, namespace in namespace_manager.namespaces():
            if uri_ref.startswith(namespace):
                return namespace
        return None
    def violate_for_node_shape(self):
        new_value = self.get_new_value(self.focus)
        for s, p, o in ViolationRecorder().output_graph.triples((None, None, self.focus)):
            ViolationRecorder().output_graph.remove((s, p, o))
            ViolationRecorder().output_graph.add((s, p, new_value))
        
        for s, p, o in ViolationRecorder().output_graph.triples((self.focus, None, None)):
            ViolationRecorder().output_graph.remove((s, p, o))
            ViolationRecorder().output_graph.add((new_value, p, o))
    def violate_for_property_shape(self):
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
            new_value = self.get_short_node(value_node, self.min_length)
        else:
            new_value = self.remove_random_chars(str(value_node), self.min_length)
        return new_value
    def get_short_node(self, value_node, x):
        for s, p, o in ValidatorMgr()._data_graph.triples((None, None, None)):
            if isinstance(s, URIRef) and len(str(s)) < self.min_length:
                return s
        for s, p, o in ValidatorMgr()._data_graph.triples((None, None, None)):
            if isinstance(o, URIRef) and len(str(o)) < self.min_length:
                return o
        assert False, "Could not find a short enough URIRef"

    def remove_random_chars(self, s, target_length):
        if len(s) < target_length:
            return ""
        
        char_list = list(s)
        num_chars_to_remove = len(s) - target_length + 1
        indices_to_remove = random.sample(range(len(s)), num_chars_to_remove)
        indices_to_remove.sort(reverse=True)
        for index in indices_to_remove:
            char_list.pop(index)
        return ''.join(char_list)
