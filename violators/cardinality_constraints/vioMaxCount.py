from ..vioConstraint import VioConstraint
from rdflib import Graph
from pyshacl import ValidatorMgr
import random
from pyshacl.consts import SH
from ..violationRecorder import ViolationRecorder
class VioMaxCount(VioConstraint):
    def __init__(self, focus, values, shape, max_count):
        super().__init__(focus, values, shape)
        self.max_count = int(max_count)
    def get_candidates(self, to_violate_cnt, candidates:set):
        for (s, p, o) in ValidatorMgr()._data_graph.triples((None, None, None)):
            if not (o in self.values):
                candidates.add(o)
            if len(candidates) >= to_violate_cnt:
               return 
        for (s, p, o) in ValidatorMgr()._data_graph.triples((None, None, None)):
            if not (s in self.values):
                candidates.add(s)
            if len(candidates) >= to_violate_cnt:
               return 
    def introduce_violation(self):
        to_violate_cnt = - len(self.values) + self.max_count + 1
        candidates = set()
        self.get_candidates(to_violate_cnt*10, candidates)
        candidates = list(set(candidates))
        if len(candidates) < to_violate_cnt:
            assert False, "Fail to introduce max count violation"
        random.shuffle(candidates)
        values_to_add = candidates[:to_violate_cnt]
        for value in values_to_add:
            ViolationRecorder().output_graph.add((self.focus, self.shape._path, value))
        self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")