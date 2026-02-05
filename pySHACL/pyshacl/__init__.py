# -*- coding: latin-1 -*-
#
from .shape import Shape
from .shapes_graph import ShapesGraph
from .validate import Validator, validate
from .validate import ValidatorMgr, validate_with_validator_recorded
# version compliant with https://www.python.org/dev/peps/pep-0440/
__version__ = '0.26.0'
# Don't forget to change the version number in pyproject.toml, Dockerfile, and CITATION.cff along with this one

__all__ = ['validate', 'validate_with_validator_recorded', 'Validator', 'ValidatorMgr', '__version__', 'Shape', 'ShapesGraph']
