from ..vioConstraint import VioConstraint
from rdflib import Graph
from pyshacl import ValidatorMgr, Shape
import random
from pyshacl.consts import SH
from ..violationRecorder import ViolationRecorder
from ..vioShape import get_fvc_with_focus, choose_property_shape_constraint_component_to_violate, choose_node_shape_constraint_component_to_violate 
class VioQualifiedMinCount(VioConstraint):
    def __init__(self, focus, values, shape):
        super().__init__(focus, values, shape)
        self.constraint_component = self.get_constraint("QualifiedValueShapeConstraintComponent")
        value_nodes = self.constraint_component.conformant_focus_value_nodes[focus]
        self.values = value_nodes
        self.sample_at_least_one_to_violate = False
    def _helper(self):
        to_remove_values, to_violate_values = self.get_to_rm_values_and_to_violate_values()
        if len(to_remove_values) > 0:
            self.rm_triple(to_remove_values)
        for value in to_violate_values:
            value_shape = self.shape.get_other_shape(list(self.constraint_component.value_shapes)[0])
            if not value_shape.is_property_shape:
                choose_node_shape_constraint_component_to_violate(value_shape, value)
            else:
                fvc = get_fvc_with_focus(value, value_shape.fvcs)
                choose_property_shape_constraint_component_to_violate(value_shape, fvc.focus_node, fvc.value_nodes)
        repeat = False
        if len(to_violate_values) == 0:
            repeat = True
        return repeat
    def get_to_rm_values_and_to_violate_values(self):
        min_count = self.constraint_component.min_count 
        value_shapes = self.constraint_component.value_shapes
        assert (len(list(value_shapes)) == 1)

        to_violate_cnt = len(self.values) - min_count + 1
        vio_idxs = random.sample(range(len(self.values)), to_violate_cnt)
        random.shuffle(vio_idxs)
        if self.sample_at_least_one_to_violate:
            to_rm_cnt = random.choice(range( len(vio_idxs) ))
        else: 
            to_rm_cnt = random.choice(range( len(vio_idxs)+1 ))
        to_remove_values = [self.values[idx] for idx in vio_idxs[:to_rm_cnt]]
        to_violate_values = [self.values[idx] for idx in vio_idxs[to_rm_cnt:]]
        return to_remove_values, to_violate_values
    def graph_was_altered(self):
        diff1 = ViolationRecorder().output_graph - ValidatorMgr()._data_graph
        if len(diff1) > 0:
            return True
        diff2 = ValidatorMgr()._data_graph - ViolationRecorder().output_graph
        if len(diff2) > 0:
            return True
        return False
    def introduce_violation(self):
        if not ViolationRecorder().do_export_graph:
            self.sample_at_least_one_to_violate = True
            self._helper()
        else:
            value_shape = self.shape.get_other_shape(list(self.constraint_component.value_shapes)[0])
            while self.keep_violating(value_shape):
                ViolationRecorder().do_export_graph = False
                repeat = self._helper()
                self.sample_at_least_one_to_violate = self.sample_at_least_one_to_violate or repeat
                ViolationRecorder().do_export_graph = True
                if self.graph_was_altered():
                    self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")

    def keep_violating(self, shape:Shape):
        from rdflib import URIRef
        keep = False
#        tmp_g = Graph() + ViolationRecorder().remaining_sg.cbd(self.shape.node)
#        while True:
#            old_ln = len(tmp_g)
#            for s, p, o in tmp_g.triples((None, None, None)):
#                if isinstance(o, URIRef):
#                    tmp_g += ViolationRecorder().remaining_sg.cbd(o)
#            if len(tmp_g) == old_ln:
#                break
#        print(tmp_g.serialize())
#        print("shape node", shape.node, ViolationRecorder().remaining_sg.cbd(shape.node).serialize())
#        if len(list(ViolationRecorder().remaining_sg.triples((shape.node, None, None)))) == 0:
#            parent_node = list(ViolationRecorder().remaining_sg.subjects(SH.qualifiedValueShape, shape.node))[0]
#            if ViolationRecorder().remaining_sg.value(parent_node, SH.qualifiedMaxCount) and len(list(ViolationRecorder().remaining_sg.value(parent_node, SH.qualifiedMaxCount))) > 0:
#                print("parent node", list(ViolationRecorder().remaining_sg.triples((parent_node, None, None))))
#                keep = True
        for (s, p, o) in ViolationRecorder().remaining_sg.triples((shape.node, None, None)):
            if p == SH.qualifiedValueShape or p == SH.property or p == SH.node:
                if self.keep_violating(shape.get_other_shape(o)):
                    keep = True
                    break
                else:
                    if ViolationRecorder().should_skip(shape, o):
                        ViolationRecorder().remaining_sg.remove((s, p, o))
                    else:
                        keep = True
                        break
            else:
                keep = True
                break
        return keep
