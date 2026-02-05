from ..vioConstraint import VioConstraint
from rdflib import Graph
from pyshacl import ValidatorMgr
import random
from pyshacl.consts import SH
from ..violationRecorder import ViolationRecorder
class VioMinCount(VioConstraint):
    def __init__(self, focus, values, shape, min_count):
        super().__init__(focus, values, shape)
        self.min_count = int(min_count)
    def introduce_violation(self):
        to_violate_cnt = len(self.values) - self.min_count + 1
        vio_idxs = random.sample(range(len(self.values)), to_violate_cnt)
        values = [self.values[idx] for idx in vio_idxs]
        self.rm_triple(values)
        self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")