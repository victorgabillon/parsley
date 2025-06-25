"""
This module provides a function to create an argument parser for command line arguments.

The `create_parser` function takes in the name of a dataclass, which represents the arguments
that can be parsed from the command line. It creates an instance of `argparse.ArgumentParser`
and adds arguments based on the fields of the dataclass.

The function also allows specifying a YAML file that contains additional arguments, which can
be turned into the dataclass using the `dacite` library. These arguments can be overwritten
by specifying them directly on the command line.

The function returns an instance of `MyParser`, which is a custom wrapper around
`argparse.ArgumentParser`. This wrapper provides additional functionality for parsing
and accessing the command line arguments.

Example usage:
    # Create an argument parser for MyArgs dataclass
    parser = create_parser(MyArgs)

    # Parse command line arguments
    args = parser.parse_args()

    # Access the parsed arguments
    print(args.my_argument)
"""

import argparse
import logging
from dataclasses import Field, fields
from typing import Any, Type

from parsley_coco.logger import set_verbosity

from parsley_coco.alternative_dataclasses import (
    make_partial_dataclass,
    make_partial_dataclass_notfilled,
    make_partial_dataclass_with_optional_paths,
)
from parsley_coco.parser import Parsley
from parsley_coco.utils import IsDataclass, add_arguments_from_dataclass
from parsley_coco.logger import set_parsley_logger

from parsley_coco.logger import get_parsley_logger


def create_parsley[DataclassType: IsDataclass](
    args_dataclass_name: Type[DataclassType],
    should_parse_command_line_arguments: bool = True,
    logger: logging.Logger | None = None,
    verbosity: int = 0,
) -> Parsley[DataclassType]:
    """
    Create an argument parser for command line arguments.

    Args:
        args_class_name: The name of the dataclass representing the arguments.
        should_parse_command_line_arguments: Whether to parse command line arguments.

    Returns:
        An instance of MyParser, which is a custom wrapper around argparse.ArgumentParser.

    """

    if logger is not None:
        set_parsley_logger(new_logger=logger)

    set_verbosity(verbosity)

    parser: argparse.ArgumentParser = argparse.ArgumentParser()

    # one can specify a path to a yaml file containing parameters
    # that can be turned into the class named args_class_name (with dacite)
    parser.add_argument(
        "--config_file_name",
        type=str,
        default=None,
        help="path to a yaml file with arguments for the script",
    )

    # data_class = make_partial_dataclass(cls=args_dataclass_name)
    add_arguments_from_dataclass(
        parser=parser,
        cls=make_partial_dataclass_with_optional_paths(cls=args_dataclass_name),
    )

    # add_arguments_from_dataclass(parser=parser, cls=args_dataclass_name)

    my_parser: Parsley[DataclassType] = Parsley(
        parser=parser,
        args_dataclass_name=args_dataclass_name,
        should_parse_command_line_arguments=should_parse_command_line_arguments,
    )

    return my_parser
