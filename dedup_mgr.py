from rdflib import Graph, compare
import rdflib
import os
import re
from rdflib.serializer import Serializer
rdflib.plugin.register("turtleDT", Serializer, "pyshacl.turtle", "TurtleSerializerWithDT")
class DeDupMgr():
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.diffs = {}
        self.iso_orig_graph = None
        self.get_iso_original_graph()
    
    def get_iso_original_graph(self):
        original_graph = Graph()
        original_graph.parse(f"{self.folder_path}/original_model.ttl", format="ttl")
        original_graph.remove((rdflib.URIRef("urn:bldg/"), rdflib.RDF.type, rdflib.OWL.Ontology))
        self.iso_orig_graph = compare.to_isomorphic(original_graph)
    
    def get_all_broken_graph_paths(self):
        files = os.listdir(self.folder_path)
        filtered_files = [f for f in files if f.endswith('.ttl') and re.match(r'^\d', f)]
        return filtered_files

    def get_paths_to_eliminate(self, broken_graph_files):
        paths_to_eliminate = []
        for i, f in enumerate(broken_graph_files):
            if i / len(broken_graph_files) * 100 % 10 == 0:
                print(f"{int(i / len(broken_graph_files) * 100)}%")
            broken_graph = Graph()
            broken_graph.parse(f"{self.folder_path}/{f}", format="ttl")
            iso_broken_graph = compare.to_isomorphic(broken_graph)
            in_both, in_first, in_second = compare.graph_diff(self.iso_orig_graph, iso_broken_graph)
            f_str = in_first.serialize(format="turtleDT")
            s_str = in_second.serialize(format="turtleDT")
            total_str = f_str + s_str
            if total_str in self.diffs:
                print(f"eliminate {f}, existing file: {self.diffs[total_str]}")
                paths_to_eliminate.append(f)
            else:
                self.diffs[total_str] = f
        return paths_to_eliminate
    def dedup(self):
        broken_graph_files = self.get_all_broken_graph_paths()
        paths_to_eliminate = self.get_paths_to_eliminate(broken_graph_files)
        print(f"remove {len(paths_to_eliminate)} files")
        for paths_to_eliminate in paths_to_eliminate:
            os.remove(f"{self.folder_path}/{paths_to_eliminate}")

if __name__ == "__main__":
    dedupMgr = DeDupMgr("/home/twlin/semantic_data_model/SemanticDataModel/test_violation/5")
    dedupMgr.dedup()