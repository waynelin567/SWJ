import random
from .violationRecorder import ViolationRecorder 
from rdflib import URIRef
from pyshacl import Shape
from pyshacl.consts import SH, RDF
from pyshacl import ValidatorMgr
def get_fvc_with_focus(focus, fvcs):
    for fvc in fvcs:
        if fvc.focus_node == focus:
            return fvc
    return None
def get_fvc_with_value(focus, fvcs):
    for fvc in fvcs:
        if focus in fvc.value_nodes:
            return fvc
    return None
def get_constraint_component(shape:Shape,constraint_name:str):
    for constraint in shape.constraint_components:
        if constraint.constraint_name() == constraint_name:
            return constraint
    assert False
def choose_node_shape_constraint_component_to_violate(shape:Shape, focus_node):
    print("choose_node_shape_constraint_component_to_violate")  
    if ViolationRecorder().shape_is_violated_by_focus_and_not_exported_yet(shape, focus_node):
        return
    (s, p, o), _ = ViolationRecorder().random_choose_constraint_to_violate(shape)
    if p == SH.property:
        property_shape_violate = shape.get_other_shape(o) 
        fvc = get_fvc_with_focus(focus_node, property_shape_violate.fvcs)
        choose_property_shape_constraint_component_to_violate(property_shape_violate, fvc.focus_node, fvc.value_nodes)
        if len(list(ViolationRecorder().remaining_sg.triples((o, None, None)))) == 0:
            ViolationRecorder().remaining_sg.remove((s, p, o))
            print("remove triple", s, p, o)
    elif p == SH.node:
        node_shape_violate = shape.get_other_shape(o) 
        choose_node_shape_constraint_component_to_violate(node_shape_violate, focus_node)
        if len(list(ViolationRecorder().remaining_sg.triples((o, None, None)))) == 0:
            ViolationRecorder().remaining_sg.remove((s, p, o))
            print("remove triple", s, p, o)
    else:
        handle_non_shape_based_constraints(focus_node, [focus_node], shape, p, o)
        ViolationRecorder().remaining_sg.remove((s, p, o))
        print("remove triple", s, p, o)
    ViolationRecorder().record_violation(shape, focus_node, [focus_node])

def choose_property_shape_constraint_component_to_violate(shape:Shape, focus_node, value_nodes):
    print("choose_property_shape_constraint_component_to_violate")
    if ViolationRecorder().shape_is_violated_by_focus_and_not_exported_yet(shape, focus_node):
        return
    (s, p, o), min_or_max = ViolationRecorder().random_choose_constraint_to_violate(shape)
    if p == SH.node:
        node_shape_violate = shape.get_other_shape(o) 
        choose_node_shape_constraint_component_to_violate(node_shape_violate, random.choice(value_nodes))
        if len(list(ViolationRecorder().remaining_sg.triples((o, None, None)))) == 0:
            ViolationRecorder().remaining_sg.remove((s, p, o))
            print("remove triple", s, p, o)
    elif p == SH.qualifiedValueShape:
        if min_or_max == "qualifiedMinCount":
            from violators.shape_based_constraints.vioQualifiedMinCount import VioQualifiedMinCount
            vqmc = VioQualifiedMinCount(focus_node, value_nodes, shape)
            vqmc.introduce_violation()
            if len(list(ViolationRecorder().remaining_sg.triples((o, None, None)))) == 0:
                if not (s, SH.qualifiedMaxCount, None) in ViolationRecorder().remaining_sg:
                    ViolationRecorder().remaining_sg.remove((s, p, o))
                    print("remove triple", s, p, o)
                ViolationRecorder().remaining_sg.remove((shape.node, SH.qualifiedMinCount, None))
                print("remove triple", shape.node, SH.qualifiedMinCount, None)
        else:
            from violators.shape_based_constraints.vioQualifiedMaxCount import VioQualifiedMaxCount
            vqmc = VioQualifiedMaxCount(focus_node, value_nodes, shape)
            vqmc.introduce_violation()
            if len(list(ViolationRecorder().remaining_sg.triples((o, None, None)))) == 0:
                if not (s, SH.qualifiedMinCount, None) in ViolationRecorder().remaining_sg:
                    ViolationRecorder().remaining_sg.remove((s, p, o))
                    print("remove triple", s, p, o)
                ViolationRecorder().remaining_sg.remove((shape.node, SH.qualifiedMaxCount, None))
                print("remove triple", shape.node, SH.qualifiedMaxCount, None)
    elif p == SH.property:
        property_shape_violate = shape.get_other_shape(o) 
        fvc = get_fvc_with_focus(random.choice(value_nodes), property_shape_violate.fvcs)
        choose_property_shape_constraint_component_to_violate(property_shape_violate, fvc.focus_node, fvc.value_nodes)
        if len(list(ViolationRecorder().remaining_sg.triples((o, None, None)))) == 0:
            ViolationRecorder().remaining_sg.remove((s, p, o))
            print("remove triple", s, p, o)
    else:
        handle_non_shape_based_constraints(focus_node, value_nodes, shape, p, o)
        ViolationRecorder().remaining_sg.remove((s, p, o))
        print("remove triple", s, p, o)
    ViolationRecorder().record_violation(shape, focus_node, value_nodes)

def violate_all_constraints_of_shape(shape:Shape, focus, values):
    print("violate all constraints of shape", shape, "using focus", focus, "and values", values)
    remaining_constraints = list(ViolationRecorder().remaining_sg.triples((shape.node, None, None)))
    if len(remaining_constraints) == 0:
        print(shape, "ran out of constraints")
        if shape.is_property_shape:
            choose_property_shape_constraint_component_to_violate(shape, focus, values)
        else:
            choose_node_shape_constraint_component_to_violate(shape, focus)
    for idx in range(len(remaining_constraints)):
        (s, p, o) = remaining_constraints[idx]
        if p == SH.qualifiedMinCount or p == SH.qualifiedMaxCount:
            continue
        if p == SH.property:
            print("remove triple", s, p, o)
            ViolationRecorder().remaining_sg.remove((s, p, o))
            ViolationRecorder().record_violation(shape, focus, values)
            if ViolationRecorder().should_skip(shape, o):
                continue
            property_shape = shape.get_other_shape(o)
            if shape.is_property_shape:
                fvc = get_fvc_with_focus(random.choice(values), property_shape.fvcs)
            else:
                fvc = get_fvc_with_focus(focus, property_shape.fvcs)
            violate_all_constraints_of_shape(property_shape, fvc.focus_node, list(fvc.value_nodes))
        elif p == SH.node:
            print("remove triple", s, p, o)
            ViolationRecorder().remaining_sg.remove((s, p, o))
            ViolationRecorder().record_violation(shape, focus, values)
            if ViolationRecorder().should_skip(shape, o):
                continue
            node_shape = shape.get_other_shape(o)
            if shape.is_property_shape:
                fvc = get_fvc_with_focus(random.choice(values), node_shape.fvcs)
                violate_all_constraints_of_shape(node_shape, fvc.focus_node, list(fvc.value_nodes))
            else:
                fvc = get_fvc_with_focus(focus, node_shape.fvcs)   
                violate_all_constraints_of_shape(node_shape, fvc.focus_node, list(fvc.value_nodes))
        elif p == SH.qualifiedValueShape:
            if ViolationRecorder().should_skip(shape, o):
                continue
            if (shape.node, SH.qualifiedMinCount, None) in ViolationRecorder().remaining_sg:
                ViolationRecorder().remaining_sg.remove((shape.node, SH.qualifiedMinCount, None))
                from violators.shape_based_constraints.vioQualifiedMinCount import VioQualifiedMinCount
                vqmc = VioQualifiedMinCount(focus, values, shape)
                vqmc.introduce_violation()
            if (shape.node, SH.qualifiedMaxCount, None) in ViolationRecorder().remaining_sg:
                ViolationRecorder().remaining_sg.remove((shape.node, SH.qualifiedMaxCount, None))
                from violators.shape_based_constraints.vioQualifiedMaxCount import VioQualifiedMaxCount
                vqmc = VioQualifiedMaxCount(focus, values, shape)
                vqmc.introduce_violation()
            print("remove triple", s, p, o)
            ViolationRecorder().remaining_sg.remove((shape.node, SH.qualifiedValueShape, None))
            ViolationRecorder().record_violation(shape, focus, values)
        else:
            print("remove triple", s, p, o)
            ViolationRecorder().remaining_sg.remove((s, p, o))
            ViolationRecorder().record_violation(shape, focus, values)
            handle_non_shape_based_constraints(focus, values, shape, p, o)

def handle_non_shape_based_constraints(focus, values, shape, p, o):
    if p == SH["class"]:
        print(">>>>>>>> violate class")
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['class']}, {o}), {focus}, {values})"
        from violators.value_type_constraints.vioClass import VioClass
        vc = VioClass(focus, values, shape, class_rule=o)
        vc.introduce_violation()
    elif p == SH["datatype"]:
        print(">>>>>>>> violate datatype")
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['datatype']}, {o}), {focus}, {values})"
        from violators.value_type_constraints.vioDatatype import VioDatatype
        vd = VioDatatype(focus, values, shape, datatype_rule=o)
        vd.introduce_violation()
    elif p == SH["nodeKind"]:
        print(">>>>>>>> violate nodeKind")
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['nodeKind']}, {o}), {focus}, {values})"
        from violators.value_type_constraints.vioNodeKind import VioNodeKind
        vnk = VioNodeKind(focus, values, shape, nodekind_rule=o)
        vnk.introduce_violation()
    elif p == SH["minCount"]:
        print(">>>>>>>> violate minCount")
#        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH["minCount"]}, {o}), {focus}, {values})"
#        this is handled in vioConstraint.py def rm_triple(self, values)
        from violators.cardinality_constraints.vioMinCount import VioMinCount
        vmc = VioMinCount(focus, values, shape, min_count=o)
        vmc.introduce_violation()
    elif p == SH["maxCount"]:
        print(">>>>>>>> violate maxCount")
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['maxCount']}, {o}), {focus}, {values})"
        from violators.cardinality_constraints.vioMaxCount import VioMaxCount
        vmc = VioMaxCount(focus, values, shape, max_count=o)
        vmc.introduce_violation()
    elif p == SH["hasValue"]:
        print(">>>>>>>> violate hasValue")
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['hasValue']}, {o}), {focus}, {values})"
        from violators.other_constraints.vioHasValue import VioHasValue
        vhv = VioHasValue(focus, values, shape, has_value=[o])
        vhv.introduce_violation()
    elif p == SH["in"]:
        print(">>>>>>>> violate in")
        from violators.other_constraints.vioHasValue import VioHasValue
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['in']}, {o}), {focus}, {values})"
        value_list = get_list_elements(ValidatorMgr()._validator.shacl_graph.graph, o)
        vi = VioHasValue(focus, values, shape, has_value=value_list)
        vi.introduce_violation()
    elif p == SH["minLength"]:
        print(">>>>>>>> violate minLength")
        from violators.string_based_constraints.vioMinLength import VioMinLength
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['minLength']}, {o}), {focus}, {values})"
        vm = VioMinLength(focus, values, shape, min_length=o)
        vm.introduce_violation()
    elif p == SH["or"]:
        print(">>>>>>>> violate or")
        from violators.logical_constraints.vioOr import VioOr
        ViolationRecorder().expression+=f"VIO(({shape.node}, {SH['or']}, {o}), {focus}, {values})"
        value_list = get_list_elements(ValidatorMgr()._validator.shacl_graph.graph, o)
        vo = VioOr(focus, values, shape, value_list)
        vo.introduce_violation()
    elif p == SH["and"]:
        print(">>>>>>>> violate and")
        from violators.logical_constraints.vioAnd import VioAnd
        value_list = get_list_elements(ValidatorMgr()._validator.shacl_graph.graph, o)
        va = VioAnd(focus, values, shape, value_list)
        va.introduce_violation()
    else:
        print("not implemented", p)
        return
        raise NotImplementedError(p)
def get_list_elements(graph, head):
    elements = []
    current = head
    while current != RDF.nil:
        first = graph.value(current, RDF.first)
        elements.append(first)
        current = graph.value(current, RDF.rest)
    return elements