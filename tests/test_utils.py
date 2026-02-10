from parsley.sentinels import notfilled
from parsley.utils import remove_notfilled_values


def test_remove_notfilled_values():
    """Test the creation of the Parsley object."""
    dicto = {
        "deep": {
            "sub": {},
            "sub_path_to_yaml_file": notfilled,
            "sub_overwrite": {},
            "preset": {"discriminator": "A", "value": 42, "flag": notfilled},
            "preset_path_to_yaml_file": notfilled,
            "preset_overwrite": {},
            "threshold": 0.2,
        },
        "deep_path_to_yaml_file": notfilled,
        "deep_overwrite": {},
        "count": 99,
        "tag": notfilled,
    }
    dicta = remove_notfilled_values(dicto)

    assert dicta == {
        "deep": {"preset": {"discriminator": "A", "value": 42}, "threshold": 0.2},
        "count": 99,
    }


if __name__ == "__main__":
    test_remove_notfilled_values()
