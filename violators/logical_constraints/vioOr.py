## for or (shape1, shape2, ..., shapen), handle the case that only one shape is satisfied
## so, identify the satisfied shape and violate it

from ..vioConstraint import VioConstraint
from pyshacl import Shape
from pyshacl.consts import SH
from ..vioShape import violate_all_constraints_of_shape 
from ..violationRecorder import ViolationRecorder
from ..vioShape import choose_property_shape_constraint_component_to_violate, choose_node_shape_constraint_component_to_violate 

class VioOr(VioConstraint):
    def __init__(self, focus, values, shape:Shape, value_list):
        super().__init__(focus, values, shape)
        self.value_shapes:list[Shape] = [shape.get_other_shape(v) for v in value_list]
    def identify_satisfied_shape(self):
        all_satisfied_shapes = []
        for value_shape in self.value_shapes:
            for fvc in value_shape.fvcs:
                if fvc.focus_node in self.values:
                    all_satisfied_shapes.append({"shape":value_shape, "fvc":fvc})
        if len(all_satisfied_shapes) == 1:
            return all_satisfied_shapes[0]
        else:
            print("Error: only exactly one satisfied shape is supported")
            print("satisfied shape len:", len(all_satisfied_shapes))
            for element in all_satisfied_shapes:
                print(element["shape"], element["fvc"])
            assert False
    def introduce_violation(self):
        tmp = self.identify_satisfied_shape()
        satisfied_shape:Shape = tmp["shape"]
        fvc = tmp["fvc"]
        print("satisfied_shape:", satisfied_shape, "fvc:", fvc)
        if ViolationRecorder().do_export_graph:
            violate_all_constraints_of_shape(satisfied_shape, fvc.focus_node, fvc.value_nodes)
        else:
            if not satisfied_shape.is_property_shape:
                ViolationRecorder().remaining_sg.add((self.shape.node, SH["node"], satisfied_shape.node))
                choose_node_shape_constraint_component_to_violate(satisfied_shape, fvc.focus_node)
            else:
                ViolationRecorder().remaining_sg.add((self.shape.node, SH["property"], satisfied_shape.node))
                choose_property_shape_constraint_component_to_violate(satisfied_shape, fvc.focus_node, fvc.value_nodes)