"""
This module contains the definition of the MyParser class, which is responsible for parsing command line arguments
and config file arguments for a script.

Classes:
- Parsley: A class for parsing command line arguments and config file arguments.

"""

import logging

import os
from dataclasses import asdict
from enum import Enum
from typing import Any, Type

import dacite
import yaml

from parsley_coco.alternative_dataclasses import (
    make_partial_dataclass,
    make_partial_dataclass_with_optional_paths,
)
from parsley_coco.recursive_dataclass_with_path_to_yaml import (
    resolve_dict_to_base_dataclass,
    resolve_extended_dict_to_dict_allow_notfilled,
    resolve_yaml_file_to_base_dataclass,
    resolve_extended_object_to_dict,
    resolve_yaml_file_to_dict_allow_notfilled,
)
from parsley_coco.utils import (
    extend_with_config,
    remove_notfilled_values,
    unflatten,
    IsDataclass,
    remove_none,
    merge_nested_dicts,
)


from parsley_coco.logger import get_parsley_logger, set_verbosity

parsley_logger = get_parsley_logger()


class Parsley[T_Dataclass: IsDataclass]:
    """
    A class for parsing command line arguments and config file arguments.

    Attributes:
        parser (Any): The parser object used for parsing command line arguments.
        args_command_line (dict[str, Any] | None): The parsed command line arguments.
        args_config_file (dict[str, Any] | None): The parsed config file arguments.
        merged_args (dict[str, Any] | None): The merged arguments from command line, config file, and extra arguments.
        should_parse_command_line_arguments (bool): Whether to parse command line arguments or not.

    Methods:
        __init__(self, parser: Any, should_parse_command_line_arguments: bool = True) -> None:
            Initialize the MyParser object.
        parse_command_line_arguments(self) -> dict[str, Any]:
            Parse the command line arguments using the parser object.
        parse_config_file_arguments(self, config_file_path: str) -> None:
            Parse the config file arguments from the specified config file.
        parse_arguments(self, base_experiment_output_folder: path, extra_args: dict[str, Any] | None = None) -> dict[str, Any]:
            Parse the command line arguments, config file arguments, and extra arguments.
        log_parser_info(self, output_folder: str) -> None:
            Log the parser information to a file.
    """

    parser: Any
    args_config_file: dict[str, Any] | None
    merged_args: dict[str, Any] | None
    should_parse_command_line_arguments: bool = True
    args_dataclass_name: Type[T_Dataclass]

    def __init__(
        self,
        parser: Any,
        args_dataclass_name: Type[T_Dataclass],
        should_parse_command_line_arguments: bool = True,
    ) -> None:
        """
        Initialize the MyParser object.

        Args:
            parser (Any): The parser object used for parsing command line arguments.
            should_parse_command_line_arguments (bool, optional): Whether to parse command line arguments or not.
                Defaults to True.
        """
        self.parser = parser
        self.should_parse_command_line_arguments = should_parse_command_line_arguments
        self.args_dataclass_name = args_dataclass_name

        # attributes to be set and saved at runtime
        self.args_config_file = None
        self.merged_args = None

    def parse_command_line_arguments(
        self, args: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Parse the command line arguments using the parser object.

        Returns:
            dict[str, Any]: A dictionary containing the parsed command line arguments.
        """

        args_obj, _ = self.parser.parse_known_args(args=args)

        args_command_line = vars(args_obj)  # converting into dictionary format
        args_command_line_without_none: dict[str, Any] = {
            key: value for key, value in args_command_line.items() if value is not None
        }

        args_command_line_without_none_unflatten = unflatten(
            args_command_line_without_none
        )

        parsed_command_line_dict = resolve_extended_dict_to_dict_allow_notfilled(
            dicto=args_command_line_without_none_unflatten,
            base_cls=extend_with_config(cls=self.args_dataclass_name),
            raise_error_with_nones=False,
        )

        parsed_command_line_dict = remove_notfilled_values(d=parsed_command_line_dict)

        return parsed_command_line_dict

    def parse_config_file_arguments(self, config_file_path: str) -> None:
        """
        Parse the config file arguments from the specified config file.

        Args:
            config_file_path (str): The path to the config file.
        """
        parsley_logger.info(
            "parse_config_file_arguments,self.args_dataclass_name: %s",
            self.args_dataclass_name,
        )
        try:
            with open(config_file_path, "r", encoding="utf-8") as _:
                try:
                    ## read the data from the yaml file and make the magic recursion so that recursive files are complied into one dataclass
                    # dataclass_from_conf_file: T_Dataclass = (
                    #    resolve_yaml_file_to_base_dataclass(
                    #        yaml_path=config_file_path,
                    #        base_cls=self.args_dataclass_name,
                    #    )
                    # )

                    args_config_file: dict[str, Any] = (
                        resolve_yaml_file_to_dict_allow_notfilled(
                            yaml_path=config_file_path,
                            base_cls=self.args_dataclass_name,
                            raise_error_with_nones=False,
                        )
                    )

                    ## transforming back to dictionary to ease the potential future merges
                    # args_config_file: dict[str, Any] = asdict(dataclass_from_conf_file)

                    args_config_file = remove_notfilled_values(d=args_config_file)

                    parsley_logger.info(
                        "Here are the yaml file arguments of the script: %s",
                        args_config_file,
                    )
                except yaml.YAMLError as exc:
                    parsley_logger.error(exc)
        except IOError as exc:
            raise ValueError(
                "Could not process file:",
                config_file_path,
                "as ",
                self.args_dataclass_name,
            ) from exc
        self.args_config_file = args_config_file

    def parse_arguments_with_command_line_args(
        self,
        extra_args: IsDataclass | None = None,
        config_file_path: str | None = None,
        args_command_line: dict[str, Any] | None = None,
    ) -> T_Dataclass:
        """
        Parse the command line arguments, config file arguments, and extra arguments.

        Args:
            extra_args (dict[str, Any], optional): Extra arguments to be merged with the parsed arguments.
            Defaults to None.

        Returns:
            dict[str, Any]: A dictionary containing the merged arguments.
        """

        parsley_logger.info(
            "Parsing arguments with command line args %s", args_command_line
        )
        if args_command_line is None:
            args_command_line = {}

        extra_args_dict: dict[str, Any]
        if extra_args is None:
            extra_args_dict = {}
        else:

            extra_args_dict = resolve_extended_object_to_dict(
                extended_obj=extra_args,
                base_cls=make_partial_dataclass_with_optional_paths(
                    self.args_dataclass_name
                ),
                raise_error_with_notfilled=False,
            )

            extra_args_dict = remove_notfilled_values(d=extra_args_dict)

        #  the gui/external input  overwrite  the command line arguments
        #  that will overwrite the config file arguments that will overwrite the default arguments

        first_merged_args = merge_nested_dicts(args_command_line, extra_args_dict)

        # 'config_file_name' is a specific input that can be specified either in extra_args or in the command line
        # and that gives the path to a yaml file containing more args

        if config_file_path is None and "config_file_name" in first_merged_args:
            config_file_path = first_merged_args["config_file_name"]
        if config_file_path is None:
            try:
                self.args_config_file = asdict(self.args_dataclass_name())
            except TypeError as exc:
                raise ValueError(
                    "The Args dataclass should have all its attributes "
                    "set to default values to allow default instantiation. "
                    f"When dealing with {self.args_dataclass_name}()"
                ) from exc
        else:

            self.parse_config_file_arguments(config_file_path)
        assert self.args_config_file is not None

        #  the gui input  overwrite  the command line arguments
        #  that overwrite the config file arguments that overwrite the default arguments

        self.merged_args = merge_nested_dicts(self.args_config_file, first_merged_args)

        assert self.merged_args is not None

        parsley_logger.info("Merged args %s", self.merged_args)

        # Converting the args in the standardized dataclass
        dataclass_args: T_Dataclass = dacite.from_dict(
            data_class=self.args_dataclass_name,
            data=self.merged_args,
            config=dacite.Config(cast=[Enum]),
        )

        # passing one more time in the machine as we may still have some unresolved tags due to default values
        new_dict = resolve_extended_dict_to_dict_allow_notfilled(
            dicto=asdict(dataclass_args),
            base_cls=self.args_dataclass_name,
            raise_error_with_nones=False,
        )
        new_dict = remove_notfilled_values(new_dict)
        parsley_logger.info("Final Merged args %s", new_dict)

        # Converting the args in the standardized dataclass
        dataclass_args_final: T_Dataclass = dacite.from_dict(
            data_class=self.args_dataclass_name,
            data=new_dict,
            config=dacite.Config(cast=[Enum]),
        )

        return dataclass_args_final

    def parse_arguments(
        self, extra_args: IsDataclass | None = None, config_file_path: str | None = None
    ) -> T_Dataclass:
        """
        Parse the command line arguments, config file arguments, and extra arguments.

        Args:
            extra_args (dict[str, Any], optional): Extra arguments to be merged with the parsed arguments.
            Defaults to None.

        Returns:
            dict[str, Any]: A dictionary containing the merged arguments.
        """

        args_command_line: dict[str, Any]
        if self.should_parse_command_line_arguments:
            args_command_line = self.parse_command_line_arguments()
        else:
            args_command_line = {}

        return self.parse_arguments_with_command_line_args(
            extra_args=extra_args,
            config_file_path=config_file_path,
            args_command_line=args_command_line,
        )

    def log_parser_info(self, output_folder: str) -> None:
        """
        Log the parser information to a file.

        Args:
            output_folder (str): The output folder where the log file will be saved.
        """
        with open(
            os.path.join(output_folder, "inputs_and_parsing/base_script_merge.yaml"),
            "w",
            encoding="utf-8",
        ) as base_merge:
            yaml.dump(self.merged_args, base_merge, default_flow_style=False)
