from ..vioConstraint import VioConstraint
from rdflib import Graph
from pyshacl import ValidatorMgr
from rdflib import Literal
import random
from ..violationRecorder import ViolationRecorder
from pyshacl.consts import SH, RDF_type
class VioClass(VioConstraint):
    #TODO: implement adding superclass RDF_type
    def __init__(self, focus, values, shape, class_rule):
        super().__init__(focus, values, shape)
        self.class_rule = class_rule
    def violate_for_node_shape(self):
        self.rm_type(self.class_rule, self.focus)
    def create_literal(self):
        for s, p, o in ValidatorMgr()._data_graph.triples((self.focus, None, None)):
            if isinstance(o, Literal):
                return o
        for s, p, o in ValidatorMgr()._data_graph.triples((None, None, None)):
            if isinstance(o, Literal):
                return o
        assert False, "No literal found"
    def violate_for_property_shape(self):
        if len(self.values)==0:
            o = self.create_literal()
            ViolationRecorder().output_graph.add((self.focus, self.shape._path, o))
            return
        value_node = random.choice(self.values)
        operation = random.choice(["add_literal", "rm_type"])
        if operation=="add_literal":
            self.add_literal(self.focus, self.shape._path, value_node)
        else:
            self.rm_type(self.class_rule, value_node)

    def add_literal(self, focus, path, value_node):
        ViolationRecorder().output_graph.add((focus, path, Literal(value_node)))

    def rm_type(self, class_rule, value_node):
        ViolationRecorder().output_graph.remove((value_node, RDF_type, class_rule))

    def introduce_violation(self):
        if self.shape.is_property_shape:
            self.violate_for_property_shape()
        else:
            self.violate_for_node_shape()
        self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")