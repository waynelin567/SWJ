from pyshacl import Shape
from rdflib import Graph
from pyshacl import ValidatorMgr
from pyshacl.consts import SH
from .violationRecorder import ViolationRecorder
class VioConstraint():
    def __init__(self, focus, values, shape:Shape):
        self.focus = focus
        self.values = values
        self.shape:Shape = shape
    def export_graph(self, graph:Graph, path):
        if not ViolationRecorder().do_export_graph:
            return
        for prefix, namespace in ValidatorMgr()._ont_graph.namespace_manager.namespaces():
            graph.bind(prefix, namespace)
        for prefix, namespace in ValidatorMgr()._data_graph.namespace_manager.namespaces():
            graph.bind(prefix, namespace)
        graph.serialize(destination=path, format="turtleDT")
        ViolationRecorder().reset_output_graph()
        ViolationRecorder().violation_cnt += 1
        print("exporting graph .......................")
    def get_constraint(self, constraint_name):
        for constraint in self.shape.constraint_components:
            if constraint.constraint_name() == constraint_name:
                return constraint
    def rm_triple(self, values:list):
        assert self.shape.is_property_shape
        minCount = list(self.shape.objects(SH['minCount']))
        qualifiedMinCount = list(self.shape.objects(SH['qualifiedMinCount']))
        if len(minCount) > 0:
            ViolationRecorder().expression+=f"VIO(({self.shape.node}, {SH['minCount']}, {int(minCount[0])}), {self.focus}, {values})"
        else:
            ViolationRecorder().expression+=f"VIO(({self.shape.node}, {SH['qualifiedMinCount']}, {int(qualifiedMinCount[0])}), {self.focus}, {values})"
        for value in values:
            print(">>>>>>remove triple", self.focus, self.shape._path, value)
            ViolationRecorder().output_graph.remove((self.focus, self.shape._path, value))