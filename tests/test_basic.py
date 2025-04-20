from parsley_coco import create_parsley

from dataclasses import dataclass

@dataclass
class TestDataClass:
    first_attribute : int =0

def test_creation():
    parsley = create_parsley(args_dataclass_name=TestDataClass,should_parse_command_line_arguments=False)
    parsley.parse_arguments(extra_args={})

