# SemanticDataModel
### Remember to fill in the APIKEY in violators/shape_based_constraints/instance_generator.py 
### How To Run

```
git checkout intro_vios
cd BuildingMOTIF
python3.10 -m venv .venv
source .venv/bin/activate
poetry install --with dev
cd ..
python3 test_other_domains.py --model valid_models/demo/model.ttl --manifest valid_models/demo/manifest.ttl  --ontology brick
```
