from parsley_coco import create_parsley

from dataclasses import dataclass


@dataclass
class TesDataClass:
    first_attribute: int = 0


def test_creation():
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TesDataClass
    )
    parsley.parse_arguments(extra_args=None)
