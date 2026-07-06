"""验证包可以从 code 目录正常导入。"""

def test_package_imports() -> None:
    import hcz_road_void

    assert hcz_road_void.Coordinate3D(0.0, 0.0, 0.0).xyz == (0.0, 0.0, 0.0)
