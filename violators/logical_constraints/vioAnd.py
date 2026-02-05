## for and (shape1, shape2, ..., shapen), the assumption is that all shapes are satisfied
## so, iterate through all shapes and violate all of them individually

from ..vioConstraint import VioConstraint
from pyshacl import Shape
from pyshacl.consts import SH
from ..vioShape import violate_all_constraints_of_shape 

class VioAnd(VioConstraint):
    def __init__(self, focus, values, shape:Shape, value_list):
        super().__init__(focus, values, shape)
        self.value_shapes:list[Shape] = [shape.get_other_shape(v) for v in value_list]
    def get_fvc_of_shape(self, shape_to_violate):
        ret = None 
        for fvc in shape_to_violate.fvcs:
            if fvc.focus_node in self.values:
                ret = fvc
        assert ret is not None, f"Error: no fvc found for {shape_to_violate}"
        return ret
    def introduce_violation(self):
        for value_shape in self.value_shapes:
            fvc = self.get_fvc_of_shape(value_shape)
            violate_all_constraints_of_shape(value_shape, fvc.focus_node, fvc.value_nodes)