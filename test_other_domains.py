from rdflib import Namespace, Graph, RDF, Literal
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library, Template
from buildingmotif.namespaces import SH, RDFS
from pyshacl import ValidatorMgr
from violationMgr import ViolationMgr
import shutil
import argparse 
from dedup_mgr import DeDupMgr
def fix_qudt_model_bug(g:Graph):
    QUDT = Namespace("http://qudt.org/schema/qudt/")
    g.remove((QUDT.IntervalScale, RDFS.comment, Literal("median, percentile & Monotonic increasing (order (<)) & totally ordered set", datatype=RDF.HTML)))
    g.add((QUDT.IntervalScale, RDFS.comment, Literal("median, percentile & Monotonic increasing (order (&lt;)) & totally ordered set", datatype=RDF.HTML)))
def get_ns_bindings(path:str, tgt_g:Graph):
    src_g = Graph()
    src_g.parse(path, format="ttl")

    for prefix, namespace in src_g.namespace_manager.namespaces():
        tgt_g.namespace_manager.bind(prefix, namespace)
def main(model_path, manifest_path, ontology):
    bm = BuildingMOTIF("sqlite://")
    Ont_IRI = Namespace('urn:bldg/')
    if ontology == "brick":
        constraints = Library.load(ontology_graph="constraints/constraints.ttl")
        ont = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")
        g36 = Library.load(directory="../../libraries/ashrae/guideline36")
        description = "This is a test model for a simple building"
    
        model = Model.create(Ont_IRI, description=description)
        model.graph.parse(model_path, format="ttl")
        g = Graph() + model.graph
    elif ontology == "lubm":
        ont = Library.load(ontology_graph="../../libraries/LUBM/univ-bench.owl")
        description = "This is a test model for a simple university"
    
        model = Model.create(Ont_IRI, description=description)
        model.graph.parse(model_path, format="ttl")
        g = Graph() + model.graph
    elif ontology == "qudt":
        from ontoenv import Config, OntoEnv
        ont = Library.load(ontology_graph="../../libraries/QUDT/qudt_ontology.ttl")
        description = "This is a test model"
        cfg = Config(["valid_models/qudt"], strict=False, offline=False)
        env = OntoEnv(cfg)
        g = Graph()
        env.get_closure("http://qudt.org/2.1/vocab/constant", g)
        get_ns_bindings(model_path, ont.get_shape_collection().graph)
        model = Model.create(Ont_IRI, description=description)
        fix_qudt_model_bug(g) 
        model.graph = g
    else:
        raise NotImplementedError()
    ValidatorMgr().set_ont_graph(ont.get_shape_collection().graph)
    
    if ontology == "qudt":
        manifest = ont
    else:
        manifest = Library.load(ontology_graph=manifest_path)
    model.update_manifest(manifest.get_shape_collection())

    validation_result = model.validate(intro_vio=True)
    print(f"Model is valid? {validation_result.valid}")
    if not validation_result.valid:
        print(validation_result.report_string)
        print("The original model must be valid")
        assert False

    shapes = ValidatorMgr()._validator.shacl_graph.shapes
    vioMgr = ViolationMgr(manifest.get_shape_collection().graph, model)

    get_ns_bindings(model_path, g)
    g.serialize(f"{ValidatorMgr()._output_dir}/original_model.ttl", format="turtleDT")

    shutil.copyfile(manifest_path, f"{ValidatorMgr()._output_dir}/manifest.ttl")
    vioMgr.introduce_violations(shapes)
    dedupMgr = DeDupMgr(ValidatorMgr()._output_dir)
    dedupMgr.dedup()
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Your program description')
    parser.add_argument('--model', type=str, help='ttl model file')
    parser.add_argument('--manifest', type=str, help='shacl manifest file')
    parser.add_argument('--ontology', type=str, help='brick or lubm')
    args = parser.parse_args()

    model_path = args.model
    manifest_path = args.manifest
    ontology = args.ontology

    #model_path = "valid_models/LUBM2_grad_student/test1/model.ttl"
    #manifest_path = "valid_models/LUBM2_grad_student/test1/manifest.ttl"
    main(model_path, manifest_path, ontology)