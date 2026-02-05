from ..vioConstraint import VioConstraint
from rdflib import Graph
from pyshacl import ValidatorMgr
from rdflib import Literal, URIRef, XSD, RDF, RDFS
import random
from ..violationRecorder import ViolationRecorder
from pyshacl.consts import SH, RDF_type
from decimal import Decimal
from datetime import datetime, date, time
def filter_alphanumeric(input_string):
    # Use list comprehension to filter out non-alphanumeric characters
    filtered_string = ''.join([char for char in input_string if char.isalnum()])
    return filtered_string
class VioDatatype(VioConstraint):
    def __init__(self, focus, values, shape, datatype_rule):
        super().__init__(focus, values, shape)
        self.datatype_rule = datatype_rule
    def introduce_violation(self):
        if self.shape.is_property_shape:
            self.violate_for_property_shape()
        else:
            self.violate_for_node_shape()
        self.export_graph(ViolationRecorder().output_graph, f"{ValidatorMgr()._output_dir}/{ViolationRecorder().violation_cnt}.ttl")

    def create_URI(self):
        for s, p, o in ValidatorMgr()._data_graph.triples((self.focus, None, None)):
            if isinstance(o, URIRef):
                return o
        for s, p, o in ValidatorMgr()._data_graph.triples((None, None, None)):
            if isinstance(o, URIRef):
                return o
            elif isinstance(s, URIRef):
                return s
        assert False, "No URIRef found"

    def violate_for_property_shape(self):
        if len(self.values)==0:
            o = self.create_URI()
            ViolationRecorder().output_graph.add((self.focus, self.shape._path, o))
            return 
        value_node = random.choice(self.values)
        operation = random.choice(["add_URIRef", "change_data_type"])
        if operation=="add_URIRef":
            self.change_literal_to_URIRef_for_property_shape(self.focus, self.shape._path, value_node)
        else:
            self.change_data_type_for_property_shape(self.datatype_rule, self.focus, self.shape._path, value_node)

    def change_literal_to_URIRef_for_property_shape(self, focus, path, value_node):
        ViolationRecorder().output_graph.remove((focus, path, value_node))
        ViolationRecorder().output_graph.add((focus, path, URIRef(filter_alphanumeric(str(value_node)))))
    
    def change_data_type_for_property_shape(self, datatype_rule, focus, path, value_node):
        new_value, new_datatype_rule = self.convert_value(value_node, datatype_rule)
        if new_value is not None:
            new_literal = Literal(new_value, datatype=new_datatype_rule)
            ViolationRecorder().output_graph.remove((focus, path, value_node))
            ViolationRecorder().output_graph.add((focus, path, new_literal))
        else:
            self.change_literal_to_URIRef_for_property_shape(focus, path, value_node)

    def violate_for_node_shape(self):
        operation = random.choice(["add_URIRef", "change_data_type"])
        if operation=="add_URIRef":
            self.change_literal_to_URIRef_for_node_shape(self.focus)
        else:
            self.change_data_type_for_node_shape(self.datatype_rule, self.focus)

    def change_literal_to_URIRef_for_node_shape(self, value_node):
        for s, p, o in ViolationRecorder().output_graph.triples((None, None, value_node)):
            ViolationRecorder().output_graph.remove((s, p, value_node))
            ViolationRecorder().output_graph.add((s, p, URIRef(filter_alphanumeric(str(value_node)))))
    
    def change_data_type_for_node_shape(self, datatype_rule, value_node):
        new_value, new_datatype_rule = self.convert_value(value_node, datatype_rule)
        if new_value is not None:
            new_literal = Literal(new_value, datatype=new_datatype_rule)

            for s, p, o in ViolationRecorder().output_graph.triples((None, None, value_node)):
                ViolationRecorder().output_graph.remove((s, p, value_node))
                ViolationRecorder().output_graph.add((s, p, new_literal))
        else:
            self.change_literal_to_URIRef_for_node_shape(value_node)
    

    def convert_value(self, val, datatype_rule):
        possible_datatypes = [XSD.string, XSD.integer, XSD.float, XSD.decimal, XSD.boolean, XSD.date, XSD.time, XSD.dateTime, XSD.anyURI]
        if datatype_rule in possible_datatypes:
            possible_datatypes.remove(datatype_rule)
        random.shuffle(possible_datatypes)
        while len(possible_datatypes)>0:
            new_type = possible_datatypes.pop()
            try:
                if new_type == XSD.string:
                    return str(val), XSD.string
                elif new_type == XSD.anyURI:
                    return str(val), XSD.anyURI
                elif new_type == XSD.integer:
                    return int(val), XSD.integer
                elif new_type == XSD.float:
                    return float(val), XSD.float
                elif new_type == XSD.decimal:
                    return Decimal(val), XSD.decimal
                elif new_type == XSD.boolean:
                    if str(val).lower() in ['true', 'false', '1', '0']:
                        return bool(val), XSD.boolean
                    else:
                        raise ValueError(f"Cannot convert {val} to boolean")
                elif new_type == XSD.date:
                    if isinstance(val, str):
                        return datetime.strptime(val, "%Y-%m-%d").date(), XSD.date
                    elif isinstance(val, datetime):
                        return val.date(), XSD.date
                    return date(val), XSD.date
                elif new_type == XSD.time:
                    if isinstance(val, str):
                        return datetime.strptime(val, "%H:%M:%S").time(), XSD.time
                    elif isinstance(val, datetime):
                        return val.time(), XSD.time
                    return time(val), XSD.time
                elif new_type == XSD.dateTime:
                    if isinstance(val, str):
                        return datetime.fromisoformat(val), XSD.dateTime
                    return datetime(val), XSD.dateTime
                else:
                    raise ValueError(f"Unsupported new datatype: {new_type}")
            except:
                pass
                #print(f"Error converting value {val} to {new_type}")
                #print(f"Trying another datatype...")

        return None, None

