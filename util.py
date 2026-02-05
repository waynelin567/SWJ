from rdflib import Graph, URIRef, BNode
from pyshacl.consts import SH, RDF_type, RDF

def copy_graph(graph: Graph) -> Graph:
    ret = Graph() + graph
    for prefix, uri in graph.namespaces():
        ret.bind(prefix, uri)
    return ret

def serialize_data_graph(datagraph:Graph) -> str:
    filtered_output = "\n".join(line for line in str(datagraph.serialize(format="turtleDT")).splitlines())
    s = filtered_output.replace("\n\n", "\n") 
    return s 

def serialize_shape_graph(shapegraph:Graph) -> str:
    filtered_output = "\n".join(line for line in str(shapegraph.serialize()).splitlines() if not line.startswith("@prefix"))
    s = filtered_output.replace("\n\n", "\n") 
    return s
def _primer():
    return "You are an expert in repairing SHACL violations of a knowledge graph built from a corpus.\n"
def _data_graph_context(dg:Graph):
    s = "Invalid knowledge graph:\n"
    s += serialize_data_graph(dg)
    return s
def _shape_graph_context(sg:Graph):
    s = "SHACL shapes:"
    filter_target_syntax(sg)
    s += serialize_shape_graph(sg)
    return s
def _instructions():
    s = "There are two information retrieval tools you can use. Both are interfaced with the corpus from which the knowledge graph is built.\n"
    s += "Tool 1: A fact checking tool that returns whether or not a triple (S, P, O) is true.\n"
    s += "Tool 2: A retrieval tool that can query (S, P, ?), (S, ?, O), or (?, P, O). It returns the set of entities {e} or properties {p} that will make (S, P, e), (S, p, O), or (e, P, O) true.\n"
    s += "Leverage the naming patterns in the knowledge graph and your common sense to minimize the number of calls to the fact checking and retrieval tool. Because the calls are expensive.\n"
    s += "Only make necessary calls. Once you call the tool, make sure to ground your repairs by the tool outputs.\n"
    s += "You must use the graph edit tool to repair the knowledge graph. You can add (ADD=True) or delete (ADD=False) one triple (S, P, O) at a time in the knowledge graph to repair the violation.\n"
    s += "When using the tools, use the correct prefix and explicitly fill in the reasoning in the form: Thinking... Because... I need to...\n"
    return s
def filter_target_syntax(graph:Graph):
    target_syntax = [SH["targetNode"], SH["targetClass"], SH["targetObjectsOf"], SH["targetSubjectsOf"]]
    for target in target_syntax:
        to_rm = list(graph.triples((None,target,None)))
        for s, p, o in to_rm:
            graph.remove((s, p, o))
