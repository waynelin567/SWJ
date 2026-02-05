from buildingmotif.dataclasses import Library
from ..vioConstraint import VioConstraint
from typing import Tuple
from rdflib import Graph, URIRef, BNode
from pyshacl import ValidatorMgr, Shape
from pyshacl.consts import SH
from buildingmotif.namespaces import RDF, OWL, SH
from ..violationRecorder import ViolationRecorder
from .instance_generator import InstanceGenerator
import copy
class VioQualifiedMaxCount(VioConstraint):
    def __init__(self, focus, values, shape):
        self.old_model_graph = Graph() + ViolationRecorder().model.graph
        for prefix, namespace in ViolationRecorder().model.graph.namespace_manager.namespaces():
            self.old_model_graph.bind(prefix, namespace)
        super().__init__(focus, values, shape)
        self.constraint_component = self.get_constraint("QualifiedValueShapeConstraintComponent")
        if focus in self.constraint_component.conformant_focus_value_nodes:
            value_nodes = self.constraint_component.conformant_focus_value_nodes[focus]
        else:
            value_nodes = []
        self.values = value_nodes
        self.subgraph_examples:list[Graph] = []
    def get_value_shape_dependencies(self, value_shape:Shape):
        manifest_graph = Graph() + ViolationRecorder().manifest_graph.cbd(value_shape.node)
        while True:
            old_length = len(manifest_graph)
            for s, p, o in manifest_graph.triples((None, None, None)):
                if isinstance(o, URIRef) and (o, RDF["type"], SH["NodeShape"]) in ViolationRecorder().manifest_graph:
                    manifest_graph += ViolationRecorder().manifest_graph.cbd(o)
            if old_length == len(manifest_graph):
                break
        return manifest_graph
    def get_lib(self):
        value_shape = self.shape.get_other_shape(list(self.constraint_component.value_shapes)[0])
        if value_shape.is_property_shape:
            assert False, "value shape can not be property shape"
        manifest_graph:Graph = self.get_value_shape_dependencies(value_shape) 
        if isinstance(value_shape.node, BNode):
            value_shape_name = URIRef("urn:my_temp_shape_name")
            for _, p, o in manifest_graph.triples((value_shape.node, None, None)):
                manifest_graph.remove((value_shape.node, p, o))
                manifest_graph.add((value_shape_name, p, o))
        else:
            value_shape_name = value_shape.node
        manifest_graph.add((value_shape_name, RDF["type"], OWL["Class"]))
        manifest_graph.add((value_shape_name, RDF["type"], SH["NodeShape"]))
        manifest_graph.add((URIRef("urn:unnamed/"),RDF.type,OWL.Ontology))

        for s, p, o in manifest_graph.triples((None, None, None)):
            if isinstance(s, URIRef) and (s, RDF["type"], SH["NodeShape"]) in manifest_graph:
                manifest_graph.add((s, RDF["type"], OWL["Class"]))
        manifest_graph.serialize("/tmp/manifest.ttl", format="ttl")
        lib = Library.load(ontology_graph="/tmp/manifest.ttl")
        return lib, value_shape_name, manifest_graph
    def get_sat_subgraph(self) -> Tuple[Graph, URIRef]:
        lib, value_shape_name, manifest_graph = self.get_lib()
        shape_templ = lib.get_template_by_name(str(value_shape_name)).inline_dependencies()
        res = shape_templ.find_subgraphs(ViolationRecorder().model, manifest_graph)

        try:
            mapping, sub_graph, _ = next(res)
        except StopIteration:
            mapping = {}
            sub_graph = Graph() + shape_templ.body
        ins_gen = InstanceGenerator(mapping, sub_graph, shape_templ.body, manifest_graph, value_shape_name, self.subgraph_examples)
        sub_graph_to_add, head_name = ins_gen.run()
        print("subgraph to add", sub_graph_to_add.serialize())
        print("head name", head_name)
        return sub_graph_to_add, head_name
    def introduce_violation(self):
        print("====introducing maxcount violation====")
        max_count = self.constraint_component.max_count 
        to_satisfy_cnt = max_count + 1 
        self._remove_existing_values()

        while len(self.subgraph_examples) < to_satisfy_cnt:
            subgraph, value = self.get_sat_subgraph()
            self.add_subgraph(subgraph, value)
            self.subgraph_examples.append(subgraph)
            self.remove_subgraph(subgraph.cbd(value)) 
        
        print("total added subgraphs")
        for sg in self.subgraph_examples:
            print(sg.serialize())
        ViolationRecorder().model.graph = self.old_model_graph
        ViolationRecorder().expression+=f"VIO(({self.shape.node}, {SH['qualifiedMaxCount']}, {max_count}), {self.focus}, {self.values})"
        self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")
    def remove_subgraph(self, subgraph:Graph):
        ViolationRecorder().model.graph -= subgraph
    def _remove_existing_values(self):
        for v in list(self.values):
            to_rm = Graph() + ViolationRecorder().model.graph.cbd(v)
            for prefix, namespace in ValidatorMgr()._ont_graph.namespace_manager.namespaces():
                to_rm.bind(prefix, namespace)
            for prefix, namespace in ValidatorMgr()._data_graph.namespace_manager.namespaces():
                to_rm.bind(prefix, namespace)
            while True:
                old_length = len(to_rm)
                for s, p, o in to_rm.triples((None, None, None)):
                    if isinstance(o, URIRef):
                        to_rm += ViolationRecorder().model.graph.cbd(o)
                if old_length == len(to_rm):
                    break
            self.subgraph_examples.append(copy.deepcopy(to_rm))
            to_rm.add((self.focus, self.shape._path, v))
            self.remove_subgraph(to_rm.cbd(v))
            print("to remove",to_rm.serialize())
    def add_subgraph(self, subgraph:Graph, value_node):
        subgraph.remove((None, None, URIRef("urn:my_temp_shape_name")))
        ViolationRecorder().output_graph += subgraph
        ViolationRecorder().output_graph.add((self.focus, self.shape._path, value_node))
