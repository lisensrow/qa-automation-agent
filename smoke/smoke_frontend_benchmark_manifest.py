from run_frontend_benchmark import BENCHMARK, validate_manifest

names = validate_manifest()
assert len(BENCHMARK) == 8, BENCHMARK.keys()
assert len(names) == 40, len(names)
assert all(len(cases) == 5 for cases in BENCHMARK.values())
print("frontend benchmark manifest smoke: PASS (8 categories, 40 cases)")
