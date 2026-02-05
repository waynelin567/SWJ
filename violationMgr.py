from violators.violationRecorder import ViolationRecorder
from pyshacl import ValidatorMgr, Shape
from pyshacl.consts import SH, RDF_type
import os
import csv
from datetime import datetime
from rdflib import Graph
SH_qualifiedValueShape = SH.qualifiedValueShape
SH_qualifiedValueShapesDisjoint = SH.qualifiedValueShapesDisjoint
SH_qualifiedMinCount = SH.qualifiedMinCount
SH_qualifiedMaxCount = SH.qualifiedMaxCount
import random
from violators.vioShape import violate_all_constraints_of_shape
class ViolationMgr():
    def __init__(self, manifest_graph:Graph, model):
        self.sg = ValidatorMgr()._validator.shacl_graph.graph 
        self.violation_record = set()
        self.tvs = []
        ViolationRecorder().init(ValidatorMgr()._validator.shacl_graph.shapes)
        ViolationRecorder().set_manifest_graph(manifest_graph)
        ViolationRecorder().set_model(model)
        self.setup_output_dir()

    def setup_output_dir(self):
        if not os.path.exists("./test_violation"):
            os.makedirs("./test_violation")
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        directory_name = f"./test_violation/{current_time}"
        os.makedirs(directory_name)
        ValidatorMgr()._output_dir = directory_name

    def should_skip_shape(self, shape) -> bool:
        if len(list(shape.fvcs)) == 0:
            return True
        if shape.is_property_shape:
            return True
        def has_target(s):
            sh_targets = [SH.targetClass,SH.targetNode,SH.targetObjectsOf,SH.targetSubjectsOf]
            for sh_target in sh_targets:
                if len(list(self.sg.triples((s,sh_target,None))))>0:
                    return True
            if len(list(ValidatorMgr()._data_graph.triples((None, RDF_type, s))))>0:
                return True
            return False
        if not shape.is_property_shape and not has_target(shape.node):
            return True
        if len(list(ViolationRecorder().remaining_sg.triples((shape.node, None, None)))) == 0:
            return True
        return False

    def sort_shapes(self, shapes):
        shape:Shape
        sorted_shapes = []
        non_root_shapes = []
        for shape in shapes:
            if len(list(self.sg.triples((None, None, shape.node)))) == 0:
                sorted_shapes.append(shape)
            else:
                non_root_shapes.append(shape)
        sorted_shapes.extend(non_root_shapes)
        return sorted_shapes
    def introduce_violations(self, shapes):
#        for (s, p, o) in ViolationRecorder().remaining_sg.triples((None, None, None)):
#            print(s, p, o)
#        print("\n\n\n")
        shape:Shape
        sorted_shapes = self.sort_shapes(shapes)
        for shape in sorted_shapes:
            if self.should_skip_shape(shape): 
                continue
            fvc = random.choice(list(shape.fvcs))
            violate_all_constraints_of_shape(shape, fvc.focus_node, list(fvc.value_nodes))
#        print("remaining triples")
#        for (s, p, o) in ViolationRecorder().remaining_sg.triples((None, None, None)):
#            print(s, p, o)
        self.write_expression()
    def write_expression(self):
        with open(f"{ValidatorMgr()._output_dir}/expression.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=["file name", "expression"])
            writer.writeheader()

            # Write the data
            for row in ViolationRecorder().expressions:
                writer.writerow(row)
