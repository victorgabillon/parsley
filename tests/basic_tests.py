from parlsey import create_parsley

from dataclasses import dataclass

@dataclass
class TestDataClass:
    first_attribute : int

def test_creation():
    parsley = create_parsley(args_class_name=TestDataClass,should_parse_command_line_arguments=False)
    parsley.parse_arguments(extra_args={})

