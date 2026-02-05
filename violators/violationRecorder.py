from rdflib import URIRef
from pyshacl import Shape
from pyshacl.constraints.constraint_component import ConstraintComponent
from pyshacl import ValidatorMgr
from pyshacl.consts import SH
from rdflib import Graph
from buildingmotif.dataclasses import Model
class FV():
    def __init__(self, focus_node, value_nodes):
        self.focus_node = focus_node
        self.value_nodes = value_nodes
    def __str__(self):
        return f"focus: {self.focus_node}, value: {self.value_nodes}"
class ViolationRecorder():
    _instance = None
    shape_constraints:dict[URIRef:dict[str:ConstraintComponent]] = None 
    violation_cnt = 0
    remaining_sg = None
    frozen_sg = None
    violation_record:dict[URIRef:list[FV]] = {}
    violation_record_not_exported_yet:dict[URIRef:list[FV]] = {}
    do_export_graph: bool = True
    output_graph:Graph = None
    expression:str = ""
    expressions:list = []
    manifest_graph:Graph = None
    model:Model = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ViolationRecorder, cls).__new__(cls)
            cls.shape_constraints = {}
        return cls._instance
    def set_manifest_graph(cls, manifest_graph):
        cls.manifest_graph = manifest_graph
    def set_model(cls, model:Model):
        cls.model = model
    def init(cls, shapes):
        cls._init_remaining_sg()
        cls.violation_record = {}
        cls._preprocess_constraints_of_shapes(shapes)
        cls.reset_output_graph()
        cls.expressions=[]
        cls.print()
    def _init_remaining_sg(cls):
        cls.remaining_sg = Graph() + ValidatorMgr()._validator.shacl_graph.graph
        for (s, p, o) in cls.remaining_sg.triples((None, None, None)):
            if p in [SH.targetClass, SH.targetNode, SH.targetObjectsOf, SH.targetSubjectsOf, SH.path]:
                cls.remaining_sg.remove((s, p, o))
            if not str(p).startswith(SH):
                cls.remaining_sg.remove((s, p, o)) 
            if p == SH["minCount"] and int(o) == 0:
                cls.remaining_sg.remove((s, p, o))
            if p == SH["qualifiedMinCount"] and int(o) == 0:
                if (s, SH["qualifiedMaxCount"], None) in cls.remaining_sg:
                    cls.remaining_sg.remove((s, SH["qualifiedMinCount"], o))
                else:
                    cls.remaining_sg.remove((s, SH["qualifiedMinCount"], o))
                    cls.remaining_sg.remove((s, SH["qualifiedValueShape"], None))
        cls.frozen_sg = Graph() + cls.remaining_sg
    def _preprocess_constraints_of_shapes(cls, shapes):
        for shape in shapes:
            new_list = []
            exists = set()
            qv_shape_id = -1
            for constraint in shape.constraint_components:
                if not constraint.constraint_name() in exists:
                    if constraint.constraint_name() == "QualifiedValueShapeConstraintComponent":
                        qv_shape_id = len(new_list)
                    new_list.append(constraint)
                    exists.add(constraint.constraint_name())
                else:
                    if constraint.constraint_name() == "QualifiedValueShapeConstraintComponent":
                        new_list[qv_shape_id].conformant_focus_value_nodes.update(constraint.conformant_focus_value_nodes)
                        new_list[qv_shape_id].non_conformant_focus_value_nodes.update(constraint.non_conformant_focus_value_nodes)
            shape.constraint_components = new_list
    def random_choose_constraint_to_violate(cls, shape:Shape):
        shape_triples = list(cls.remaining_sg.triples((shape.node, None, None)))
        def determine_min_or_max(g, s):
            value_shape = list(g.objects(s, SH.qualifiedValueShape))
            min_count = list(g.objects(s, SH.qualifiedMinCount))
            max_count = list(g.objects(s, SH.qualifiedMaxCount))
            if len(value_shape) == 0:
                value_shape = list(cls.frozen_sg.objects(s, SH.qualifiedValueShape))
            print("value_shape", value_shape)
            if len(min_count) > 0:
                print(g.cbd(s).serialize())
                return (s, SH.qualifiedValueShape, value_shape[0]), "qualifiedMinCount"
            if len(max_count) > 0:
                print(g.cbd(s).serialize())
                return (s, SH.qualifiedValueShape, value_shape[0]), "qualifiedMaxCount"
        if len(shape_triples) == 0:
            (s, p, o) = list(cls.frozen_sg.triples((shape.node, None, None)))[0]
            if p == SH.qualifiedValueShape or p == SH.qualifiedMinCount or p == SH.qualifiedMaxCount: 
                return determine_min_or_max(cls.frozen_sg, s)
            return (s, p, o), None 
        else:
            (s, p, o) = shape_triples[0]
            if p == SH.qualifiedValueShape or p == SH.qualifiedMinCount or p == SH.qualifiedMaxCount: 
                return determine_min_or_max(cls.remaining_sg, s)
            return (s, p, o), None 
    def should_skip(cls, shape:Shape, object_shape_uri:URIRef):
        print("determine ", shape, object_shape_uri, "should skip")
        values = set([value_node for fvc in shape.fvcs for value_node in fvc.value_nodes])
        print("values", values)
        if object_shape_uri in cls.violation_record:
            violated_focuses = set([fv.focus_node for fv in cls.violation_record[object_shape_uri]])
            print("violated_focuses", violated_focuses)
            if len(values.intersection(violated_focuses)) > 0:
                return True
        return False
    def record_violation(cls, shape:Shape, focus, values):
        fv = FV(focus, values)
        if shape.node in cls.violation_record:
            cls.violation_record[shape.node].append(fv)
        else:
            cls.violation_record[shape.node] = [fv]
        if shape.node in cls.violation_record_not_exported_yet:
            cls.violation_record_not_exported_yet[shape.node].append(fv)
        else:
            cls.violation_record_not_exported_yet[shape.node] = [fv]
    def reset_output_graph(cls):
        cls.violation_record_not_exported_yet = {}
        cls.output_graph = Graph() + ValidatorMgr()._data_graph
        cls.finalize_expression()
    def finalize_expression(cls):
        d = {"file name": f"{cls.violation_cnt}.ttl", "expression": cls.expression}
        cls.expressions.append(d)
        cls.expression = ""
    def print(cls):
        return
    def shape_is_violated_by_focus_and_not_exported_yet(cls, shape:Shape, focus):
        print(f"checking if {shape.node} is violated by {focus} and not exported yet")
        for shape_node in cls.violation_record_not_exported_yet.keys():
            for fv in cls.violation_record_not_exported_yet[shape_node]:
                if fv.focus_node == focus:
                    print(f"YES. {focus} is used to violate {shape_node} and not exported yet")
                    return True
        print(f"No.")
        return False