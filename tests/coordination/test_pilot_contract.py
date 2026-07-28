from olympus_v3.coordination.pilot_compiler import compile_snake_manifest


def test_fixed_manifest_compiles():
    manifest = compile_snake_manifest()
    assert manifest.pilot_id == "snake-r8"
    assert len(manifest.tasks) == 5


def test_manifest_is_immutable():
    manifest = compile_snake_manifest()
    try:
        manifest.pilot_id = "other"
    except Exception:
        pass
    else:
        raise AssertionError("manifest mutable")
