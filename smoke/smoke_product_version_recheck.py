#!/opt/uqa/.venv/bin/python

import uqa


containers = {
    "status": "ok",
    "containers": [
        {
            "name": "u_backend",
            "image": "registry.example/product/u-backend:4.10.0",
        },
        {
            "name": "frontend",
            "image": "registry.example/product/u-frontend-ui:2.22.0",
        },
        {
            "name": "database",
            "image": "registry.example/postgres:16",
        },
    ],
}

assert uqa._product_versions_from_containers(containers) == {
    "backend": "4.10.0",
    "frontend": "2.22.0",
}
assert uqa._container_image_version("registry:5000/team/app:1.2.3") == "1.2.3"
assert uqa._container_image_version("registry:5000/team/app") is None
assert uqa._container_image_version("team/app@sha256:abc") is None

captured = {}


def fake_execute_tool(name, arguments):
    captured["tool"] = (name, arguments)
    return containers


def fake_mark(versions):
    captured["versions"] = versions
    return ["blk-one"]


uqa.execute_tool = fake_execute_tool
uqa.mark_product_blockers_for_version_change = fake_mark

result = uqa.recheck_product_blockers_for_stand("qa.example")
assert result == {
    "status": "ok",
    "versions": {"backend": "4.10.0", "frontend": "2.22.0"},
    "changed": ["blk-one"],
}
assert captured["tool"] == (
    "ssh_docker_ps",
    {"stand": "qa.example"},
)

checked = set()
assert uqa._recheck_product_blockers_once("qa.example", checked)["status"] == "ok"
assert checked == {"qa.example"}
assert uqa._recheck_product_blockers_once("qa.example", checked) is None

print("smoke_product_version_recheck: PASS")
