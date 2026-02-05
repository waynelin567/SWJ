from ..vioConstraint import VioConstraint
from pyshacl import ValidatorMgr
from rdflib import Literal, URIRef, BNode, Graph
import random
from ..violationRecorder import ViolationRecorder
from pyshacl.consts import (
    SH_IRI,
    SH_BlankNode,
    SH_BlankNodeOrIRI,
    SH_BlankNodeORLiteral,
    SH_IRIOrLiteral,
    SH_Literal,
)
class VioNodeKind(VioConstraint):
    def __init__(self, focus, values, shape, nodekind_rule):
        super().__init__(focus, values, shape)
        self.nodekind_rule = nodekind_rule
    def violate_for_node_shape(self):
        new_value = self.change_value_node_kind(self.determine_final_node_kind(), self.focus)
        for s, p, o in ViolationRecorder().output_graph.triples((None, None, self.focus)):
            ViolationRecorder().output_graph.remove((s, p, o))
            ViolationRecorder().output_graph.add((s, p, new_value))
        
        new_value = self.change_value_node_kind(self.determine_final_node_kind(is_subject=True), self.focus)
        for s, p, o in ViolationRecorder().output_graph.triples((self.focus, None, None)):
            ViolationRecorder().output_graph.remove((s, p, o))
            ViolationRecorder().output_graph.add((new_value, p, o))

    def violate_for_property_shape(self):
        value_node = random.choice(self.values)
        ViolationRecorder().output_graph.remove((self.focus, self.shape._path, value_node))
        new_value = self.change_value_node_kind(self.determine_final_node_kind(),value_node)
        ViolationRecorder().output_graph.add((self.focus, self.shape._path, new_value))

    def determine_final_node_kind(self, is_subject=False):
        final_nodekind = None
        if self.nodekind_rule == SH_BlankNode:
            final_nodekind = random.choice([Literal, URIRef])
            if is_subject:
                final_nodekind = URIRef
        elif self.nodekind_rule == SH_Literal:
            final_nodekind = random.choice([BNode, URIRef])
        elif self.nodekind_rule == SH_IRI:
            final_nodekind = random.choice([Literal, BNode])
            if is_subject:
                final_nodekind = BNode
        elif self.nodekind_rule == SH_BlankNodeOrIRI:
            final_nodekind = Literal
        elif self.nodekind_rule == SH_BlankNodeORLiteral:
            final_nodekind = URIRef
        elif self.nodekind_rule == SH_IRIOrLiteral:
            final_nodekind = BNode
        else:
            assert False
        return final_nodekind

    def change_value_node_kind(self, final_nodekind, value_node):
        if isinstance(value_node, URIRef):
            if final_nodekind == Literal:
                return Literal(str(value_node))
            elif final_nodekind == BNode:
                return BNode()
        elif isinstance(value_node, Literal):
            if final_nodekind == BNode:
                return BNode()
            elif final_nodekind == URIRef:
                return URIRef(f"http://example.org/{value_node}")
        elif isinstance(value_node, BNode):
            if final_nodekind == Literal:
                return Literal(str(value_node))
            elif final_nodekind == URIRef:
                return URIRef(f"http://example.org/{value_node}")

    def introduce_violation(self):
        if self.shape.is_property_shape:
            self.violate_for_property_shape()
        else:
            self.violate_for_node_shape()
        self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")