# Parsley Coco

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
[![Tests](https://github.com/victorgabillon/parsley/actions/workflows/ci.yaml/badge.svg)](https://github.com/victorgabillon/parsley/actions)

## Overview

Parsley Coco is a Python library that combines the power of `dacite` and `argparse` to provide a flexible and extensible parser for command-line arguments and configuration files. It supports recursive YAML parsing, dataclass-based argument definitions, and merging of arguments from multiple sources.


## Release 0.2.0

This release requires Python 3.14 and resolves deferred annotations before
building dataclass and CLI schemas. Nested YAML configuration, command-line
overrides, forward references, and packaged YAML data retain their validated
behavior. Runtime and development dependencies use the validated toolchain.

## Features

- **Recursive YAML Parsing**: Parse nested YAML files into Python dataclasses.
- **Dataclass-Based Argument Parsing**: Define arguments using Python dataclasses for type safety and clarity.
- **Command-Line and Config File Integration**: Merge arguments from command-line inputs, YAML config files, and extra arguments.
- **`extra_args` Support**: Programmatically provide additional arguments using an extended version of the base dataclass, allowing for flexible overrides and dynamic configurations.
- **Overwrite Functionality**: Automatically resolve nested configurations and apply overwrite values from YAML files or programmatically provided arguments.


## Requirements

- Python 3.14 or higher

## Installation

To install the library, use `pip`:

```bash
pip install parsley-coco==0.2.0
```

## Usage

### Table of Contents
- [Basic Example](#basic-example)
- [Input Arguments](#input-arguments)
- [Precedence of Arguments](#precedence-of-arguments)
- [Union Types, Defaults, and Discriminator Fields](#union-types-defaults-and-discriminator-fields)
- [Recursive YAML Parsing](#recursive-yaml-parsing)
- [Using Classes with a YAML Path Method (e.g., Enum Integration)](#using-classes-with-a-yaml-path-method-eg-enum-integration)
- [Default Behavior Without a Config File](#default-behavior-without-a-config-file)
- [Command-Line Arguments Handling](#command-line-arguments-handling)
- [Using `extra_args` with `parse_arguments`](#using-extra_args-with-parse_arguments)

---

### Basic Example

Define your dataclasses and use `create_parsley` to create a parser, then instantiate the dataclass from (for instance) a yaml conf file:

```python
from dataclasses import dataclass
from parsley import create_parsley, Parsley

@dataclass
class Config:
    x: int
    y: str

parser: Parsley[Config] = create_parsley(Config)
config: Config = parser.parse_arguments(config_file_path="path/to/config.yaml")
print(config)
```

### Input Arguments

#### `create_parsley`

The `create_parsley` function initializes a `Parsley` parser for a given dataclass.

- **Arguments**:
  1. **`dataclass_type`**:
     - The dataclass type you want to parse (e.g., `Config`).
     - This defines the structure of the configuration, including fields, types, and default values.
  2. **`should_parse_command_line_arguments`** (optional):
     - A boolean indicating whether command-line arguments should be parsed.
     - Defaults to `True`. If set to `False`, command-line arguments will be ignored.

- **Returns**:
  - A `Parsley` parser instance that can parse arguments based on the provided dataclass.

---

#### `parse_arguments`

The `parse_arguments` method of the `Parsley` parser parses arguments from multiple sources (command-line, YAML, `extra_args`).

- **Arguments**:
  1. **`extra_args`** (optional):
     - A dataclass instance or dictionary containing additional arguments.
     - These arguments take precedence over command-line arguments, YAML, and dataclass defaults.
  2. **`config_file_path`** (optional):
     - A string specifying the path to a YAML configuration file.
     - If not provided, the parser looks for a `config_file_name` key in `extra_args` or command-line arguments.
  3. **`argv`** (keyword-only, optional):
     - A `Sequence[str]` of CLI tokens without the program name. `None` uses `sys.argv[1:]`; `[]` supplies no tokens.
  4. **`strict`** (keyword-only, default `False`):
     - When `True`, unknown CLI arguments produce an argparse error. YAML and dictionary-key validation are unchanged.

- **Returns**:
  - An instance of the dataclass populated with the merged arguments from all sources.

---

### Precedence of Arguments

Parsley Coco merges arguments from multiple sources in a specific order of precedence. The final configuration is determined by the following hierarchy (from highest to lowest priority):

1. **`extra_args`**: Programmatically provided arguments via the `extra_args` parameter in `parse_arguments` take the highest priority. These values overwrite all other sources, including command-line arguments.
2. **Command-Line Arguments**: Arguments provided via the command line take precedence over YAML configuration files and default values in the dataclass.
3. **YAML Configuration File**: Values from the YAML configuration file are used if not overridden by `extra_args` or command-line arguments.
4. **Default Values in the Dataclass**: If no value is provided from `extra_args`, command-line arguments, or the YAML file, the default values defined in the dataclass are used.

This precedence ensures flexibility while maintaining a clear and predictable merging process.

---

#### Example

Consider the following setup:

- **Dataclass**:
  ```python
  from dataclasses import dataclass

  @dataclass
  class Config:
      x: int = 0
      y: str = "default"
  ```

- **YAML File (`config.yaml`)**:
  ```yaml
  x: 10
  y: "from_yaml"
  ```

- **Command-Line Arguments**:
  ```bash
  --x 42
  ```

- **`extra_args`**:
  ```python
  {"y": "from_extra"}
  ```

#### Code Example

```python
from parsley.alternative_dataclasses import make_dataclass_with_optional_paths_and_overwrite, make_partial_dataclass_with_optional_paths
from parsley.factory import create_parsley

parser = create_parsley(Config)

# creating an extented config dataclass that allows more flexibility (more later in the readme)
ExtendedConfig = make_partial_dataclass_with_optional_paths(Config)

# Parse arguments
config = parser.parse_arguments(
    config_file_path="tests/yaml_files/config.yaml",
    extra_args=ExtendedConfig(y= "from_extra")
)
```

#### Resulting Configuration

```python
Config(x=42, y="from_extra")
```

#### Explanation

1. The value of `x` is `42` because the command-line argument `--x 42` overrides the YAML file value (`10`).
2. The value of `y` is `"from_extra"` because `extra_args` takes precedence over the YAML file (`"from_yaml"`) and the default value (`"default"`).

---

This updated explanation reflects the correct precedence order based on the implementation in the library. Let me know if you need further clarification or adjustments!

### Union Types, Defaults, and Discriminator Fields

Parsley Coco uses [dacite](https://github.com/konradhalas/dacite) for parsing dictionaries into dataclasses, with `Config(strict=False)`. This means that if a dataclass field is a union of multiple types (e.g., `int | MyDataClass`), and the dataclass has default values, **any compatible type in the union can be used during parsing**. For example, if your YAML provides an integer, it will be parsed as an `int`; if it provides a mapping, it will be parsed as a dataclass.

**However, when using unions of dataclasses, we strongly recommend adding a discriminator field (such as `Literal["my_type"]`) to each dataclass.** This helps `dacite` and Parsley Coco reliably determine which dataclass to instantiate when parsing nested structures.

#### Example

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class OptionA:
    discriminator: Literal["A"]
    value: int

@dataclass
class OptionB:
    discriminator: Literal["B"]
    name: str

@dataclass
class Config:
    option: OptionA | OptionB | int = 0
```

**YAML Example:**
```yaml
option:
  discriminator: B
  name: "hello"
```

This will be parsed as `Config(option=OptionB(discriminator="B", name="hello"))`.

**YAML Example:**
```yaml
option: 42
```

This will be parsed as `Config(option=42)`.

**Recommendation:**
Always include a `discriminator` field (using `Literal[...]`) in each dataclass used in a union. This ensures robust and predictable parsing, especially when your configuration can match multiple types.

### Recursive YAML Parsing

A requested YAML file with invalid syntax raises
`parsley.parser.ConfigFileProcessingError`, including the offending file path
and chaining the original `yaml.YAMLError` as `__cause__`. This also applies
to nested YAML references and presets; malformed files never silently fall
back to dataclass defaults. Omitting a configuration file still uses defaults.

Parsley Coco supports recursive YAML parsing. For example:

```yaml
# config.yaml
x: 10
y: "hello"
nested_config_path_to_yaml_file: "nested_config.yaml"
```

```yaml
# nested_config.yaml
z: 42
```

To handle this, you need to define your `Config` dataclass to include a field for the nested configuration:

```python
from dataclasses import dataclass
from typing import Optional
from parsley import create_parsley, Parsley

@dataclass
class NestedConfig:
    z: int

@dataclass
class Config:
    x: int
    y: str
    nested_config: NestedConfig

parser: Parsley[Config] = create_parsley(Config)
config = parser.parse_arguments(config_file_path="path/to/config.yaml")
print(config)
```

In this example:
- The `Config` dataclass includes a field `nested_config` of type `Optional[NestedConfig]`.
- The `NestedConfig` dataclass defines the structure of the nested YAML file.
- Parsley Coco will automatically resolve the nested YAML file into the `nested_config` field.

This ensures that the recursive YAML parsing works seamlessly with your dataclass structure.

### Using Classes with a YAML Path Method (e.g., Enum Integration)

Parsley Coco supports advanced configuration patterns where a field in your dataclass can be an object (such as an Enum member) that provides a method to retrieve a YAML file path. If the class has a method (for example, `get_yaml_file_path`) that returns the path to a YAML file, Parsley will automatically load and parse the YAML file to instantiate the corresponding object.

This is especially useful for scenarios where you want to select a configuration "profile" or "preset" by name, and have the details loaded from a separate YAML file.

#### Example

Suppose you have an Enum for model presets, and each preset has a YAML file describing its configuration:

```python
from enum import Enum
from dataclasses import dataclass
from parsley import create_parsley, Parsley

class ModelPreset(str, Enum):
    small = "small"
    large = "large"

    def get_yaml_file_path(self) -> str:
        return f"presets/{self.value}.yaml"

@dataclass
class ModelConfig:
    preset: ModelPreset
    # other fields...

@dataclass
class AppConfig:
    model: ModelConfig
```

**YAML Example (`config.yaml`):**
```yaml
model:
  preset: large
```

**YAML Example (`presets/large.yaml`):**
```yaml
# Any fields for ModelConfig, e.g.:
layers: 24
hidden_size: 1024
```

#### How it works

- When you specify `preset: large` in your main YAML, Parsley will instantiate the `ModelPreset.large` enum.
- Since `ModelPreset` has a `get_yaml_file_path` method, Parsley will call this method to get the path (`presets/large.yaml`), load the YAML file, and use its contents to populate the `ModelConfig` dataclass.

#### Usage

```python
parser = create_parsley(AppConfig)
config = parser.parse_arguments(config_file_path="config.yaml")
print(config)
```

This pattern allows you to keep your main configuration clean and delegate detailed settings to separate YAML files, referenced by simple tags or enum values.

**Tip:**
You can use this approach with any class, not just Enums, as long as it provides a `get_yaml_file_path()` method returning the YAML path as a string.

### Default Behavior Without a Config File

Without a configuration file, Parsley composes CLI and programmatic input and
then fills omitted fields from dataclass defaults. A root dataclass does not
need to be default-constructible: required fields can come from any supported
input source, or from a combination of sources.

#### Example

```python
from dataclasses import dataclass
from parsley import create_parsley, Parsley

@dataclass
class Config:
    x: int = 0  # Default value
    y: str = "default"  # Default value

parser: Parsley[Config] = create_parsley(Config)

# No config file provided
config = parser.parse_arguments()
print(config)
```

#### Output

```python
Config(x=0, y="default")
```

#### Key Points:
1. **Default Values**: Defaults apply only to omitted fields. Explicit YAML `null` or programmatic `None` is preserved and must match the field's type.
2. **Required Values**: A field still missing after composition raises `dacite.MissingValueError`, with a path such as `child.x`.

An annotation such as `x: int | None` permits null but does not declare a
default. Omission still requires a value; declare `x: int | None = None` to
allow omission. This makes empty-YAML and no-YAML behavior consistent instead
of inferring `None` only on the YAML path.

### Configuration Construction and Factories

Parsley resolves supplied YAML references, presets, and overwrites as data,
combines sources, and selects declared dataclass/union schemas before constructing
the final objects. It does not instantiate the root just to inspect defaults.
Each selected user dataclass is constructed once; `__post_init__` runs normally
on the composed values, including for nested objects. For example:

```python
@dataclass
class Required:
    x: int

assert create_parsley(Required).parse_arguments(argv=["--x", "3"]).x == 3

@dataclass
class Increment:
    x: int = 0

    def __post_init__(self):
        self.x += 1

parser = create_parsley(Increment)
assert parser.parse_arguments(argv=[]).x == 1
assert parser.parse_arguments(argv=["--x", "7"]).x == 8
```

The same construction behavior applies to `parse_known_arguments`,
`parse_arguments_with_command_line_args`, `resolve_dict_to_base_dataclass`,
`resolve_yaml_file_to_base_dataclass`, and `resolve_extended_object`.
Data-only resolution does not run user constructors.

Factory behavior follows field omission:

- An omitted field uses its default or evaluates its `default_factory` once per
  parse. Supplied fields do not invoke that field's factory.
- A supplied nested mapping uses the nested type's declared field defaults;
  it does not evaluate the parent's factory to obtain a template. This applies
  equally to CLI, YAML, and programmatic input. `{}` supplies a nested mapping;
  `None` supplies null; an absent field uses the parent's default/factory.
- A dataclass type used directly as a factory, such as
  `field(default_factory=Child)`, is constructed after its own defaults and
  preset references are resolved. An arbitrary callable returning an already
  constructed dataclass supplies that completed value; Parsley copies it and
  does not rerun its initialization.
- Mutable values are copied so hooks and subsequent parses do not mutate
  supplied objects or share defaults. Programmatic input dataclasses contribute
  their **current field values** as overrides; the final target's hook still
  runs once. A caller's earlier initialization is not undone.

Intentional corrections from 0.2.0: root and nested hooks no longer run during
intermediate passes; partial CLI input no longer evaluates a parent factory
whose custom values would previously survive only for CLI, but not YAML.
For example, with `child=field(default_factory=lambda: Child(x=10, y=20))`,
supplying `child.x` uses `Child`'s declared default for `y`, consistently across
sources. Supply factory-specific values explicitly when composing such input.
Fields declared `init=False` are left to normal dataclass initialization and
`__post_init__`, rather than being overwritten after the hook.

Union selection uses declared types and discriminators without executing user
constructors as probes. Once selected, a constructor/`__post_init__` exception
propagates; Parsley does not retry another union arm to hide validation failure.
Existing contextual YAML errors remain unchanged. The
`parsley.parser.ArgsDataclassDefaultsError` import remains available for
compatibility; missing required input now uses `dacite.MissingValueError` after
composition. Invalid provided values still fail in the schema-validation stage
(including `FieldUnionParsingError` for generated union schemas).

An arbitrary factory returning an already constructed object with unresolved
preset references is unsupported: resolving it would require rebuilding an
object whose hook has already run. This raises
`parsley.construction.UnresolvedDefaultError`; use the dataclass type itself as
the factory, or return a fully resolved object. Recursive CLI schemas, required
`InitVar`/custom constructor arguments outside declared fields, and broader
dataclass-in-collection/union shapes are not added by this change. The standalone
generic `from_dict_with_union_handling` utility retains its existing behavior.

### Command-Line Arguments Handling

Parsley Coco integrates with `argparse` to handle command-line arguments. The precedence order is `extra_args > CLI > YAML > dataclass defaults`.

#### How It Works

1. **Automatic Argument Parsing**: Parsley Coco automatically generates command-line arguments based on the fields in your dataclass.
2. **Priority**: Command-line arguments override YAML and dataclass defaults. Values in `extra_args` override command-line arguments.
3. **Type Safety**: The types of the arguments are inferred from the dataclass fields, ensuring type safety.

#### Example

```python
from dataclasses import dataclass
from parsley import create_parsley, Parsley

@dataclass
class Config:
    x: int
    y: str

parser: Parsley[Config] = create_parsley(Config)

# Parse arguments from the command line
config = parser.parse_arguments()
print(config)
```

#### Command-Line Usage

If the script above is saved as `example.py`, you can run it with command-line arguments:

```bash
python example.py --x 42 --y "hello world"
```

#### Output

```python
Config(x=42, y="hello world")
```

#### Key Points:
1. **Automatic Argument Names**: The argument names are derived from the field names in the dataclass (e.g., `x` becomes `--x`).
2. **Type Conversion**: Parsley Coco automatically converts the command-line arguments to the appropriate types based on the dataclass field types.
3. **Help Message**: A help message is automatically generated for the command-line arguments.

#### Boolean Values

Boolean fields keep the `--field VALUE` syntax, including nested fields such as
`--child.enabled false` and optional `bool | None` fields. Accepted tokens are
case-insensitive `true` and `1` for `True`, and `false` and `0` for `False`.
Other tokens (including `yes`, `no`, `on`, `off`, `none`, and tokens with surrounding
whitespace) produce an argparse error. A value is required after the option.

Omitting a boolean option supplies no CLI override, so YAML or dataclass defaults
still apply. For optional booleans, omission preserves the configured value
(including `None`); explicit YAML `null` remains supported. Unknown CLI arguments
continue to be ignored by default to support layered parsing.

#### Explicit argv and CLI Composition

The public entrypoints on `Parsley[T]` are:

```python
parse_arguments(extra_args=None, config_file_path=None, *,
                argv: Sequence[str] | None = None, strict: bool = False) -> T
parse_known_arguments(extra_args=None, config_file_path=None, *,
                      argv: Sequence[str] | None = None) -> tuple[T, list[str]]
parse_command_line_arguments(args: Sequence[str] | None = None, *,
                             strict: bool = False) -> dict[str, Any]
```

`argv` excludes the program name. `None` retains process-command-line behavior;
`[]` supplies no CLI arguments. An explicit sequence is independent of `sys.argv`.
Neither the sequence nor `sys.argv` is modified. The existing `args=` keyword and
dictionary return type on the lower-level method are preserved.

For explicit input, define defaults and pass the tokens directly:

```python
from dataclasses import dataclass
from parsley import create_parsley

@dataclass
class Config:
    count: int = 1
    enabled: bool = True

parser = create_parsley(Config)
config = parser.parse_arguments(argv=["--count", "6", "--enabled", "false"])
assert config == Config(count=6, enabled=False)
assert parser.parse_arguments(argv=[]) == Config()
```

For a standalone command, opt into strict CLI parsing per call:

```python
config = parser.parse_arguments(argv=["--count", "6"], strict=True)
# In a script, parser.parse_arguments(strict=True) reads sys.argv[1:].
# --cout 6 would print an argparse error and exit with status 2.
```

For a larger application, pass the remainder to another parser without globals:

```python
import argparse
from collections.abc import Sequence

def parse_job(argv: Sequence[str]) -> tuple[Config, str]:
    config, remaining = create_parsley(Config).parse_known_arguments(argv=argv)
    dispatcher = argparse.ArgumentParser()
    dispatcher.add_argument("--job", choices=["train", "evaluate"], required=True)
    return config, dispatcher.parse_args(remaining).job

assert parse_job(["--job", "train", "--count", "6"]) == (Config(count=6), "train")
```

`parse_known_arguments` retains unconsumed tokens in argparse's returned order
and invokes the existing configuration merge pipeline once. It does not run a
second configuration parse to obtain the remainder. Existing argparse option
abbreviation behavior remains in effect: a recognized prefix can be consumed,
so use distinct option names across parsing stages.

With `should_parse_command_line_arguments=False`, both high-level methods ignore
CLI values, help, and errors; YAML and `extra_args` still apply. `parse_arguments`
also ignores `strict`. `parse_known_arguments` returns all supplied tokens (or
`sys.argv[1:]` when `argv=None`) unconsumed in a fresh list. Direct calls to the
lower-level `parse_command_line_arguments` still explicitly parse tokens,
regardless of that flag, as before.

When CLI parsing is enabled, `--help` prints help and exits with status 0,
including in parse-known mode. Missing values and invalid known values exit
with status 2 in every mode; unknown tokens cause an error only with `strict=True`.
Values and strictness do not carry over between calls. All entrypoints retain
`extra_args > CLI > YAML > dataclass defaults`; strictness applies only to CLI
tokens. Required values and defaults follow the
[configuration construction rules](#configuration-construction-and-factories).

#### Example with YAML and Command-Line Arguments

If a YAML file is provided along with command-line arguments, the command-line arguments will take precedence:

```yaml
# config.yaml
x: 10
y: "from_yaml"
```

Run the script with:

```bash
python example.py --x 42
```

Resulting configuration:

```python
Config(x=42, y="from_yaml")
```

This demonstrates how command-line arguments can override specific fields while retaining other values from the YAML file.

---

This section explains how Parsley Coco handles command-line arguments and their priority in the configuration merging process. Let me know if you need further clarification or adjustments!


### Using `extra_args` with `parse_arguments`

The `extra_args` parameter in the `parse_arguments` function allows you to programmatically provide additional arguments. These arguments are passed as an instance of a dataclass that extends the base dataclass. This extended dataclass is created using the `make_partial_dataclass_with_optional_paths` function.

---

### How `make_partial_dataclass_with_optional_paths` Works

The `make_partial_dataclass_with_optional_paths` function:
1. **Extends the Base Dataclass**: It adds optional fields for:
   - Paths to YAML files (e.g., `field_name_path_to_yaml_file`).
   - Overwrite values (e.g., `field_name_overwrite`).
2. **Makes All Fields Optional**: This allows partial instantiation of the dataclass, making it flexible for use with `extra_args`.

This function combines two steps:
- **`make_dataclass_with_optional_paths_and_overwrite`**: Adds optional fields for paths and overwrite values.
- **`make_partial_dataclass`**: Makes all fields in the dataclass optional, including nested dataclasses.

---

### Example

#### Base Dataclass

```python
from dataclasses import dataclass
from parsley import create_parsley, Parsley
from parsley.alternative_dataclasses import make_partial_dataclass_with_optional_paths

@dataclass
class NestedConfig:
    z: int

@dataclass
class Config:
    x: int
    y: str
    nested_config: NestedConfig
```

#### Extended Dataclass

Using `make_partial_dataclass_with_optional_paths`, we create an extended version of the `Config` dataclass:

```python
PartialConfig = make_partial_dataclass_with_optional_paths(Config)
```

This will generate a new dataclass with the following structure:
- All fields from `Config` are optional.
- Additional fields are added:
  - `nested_config_path_to_yaml_file: Optional[str]`
  - `nested_config_overwrite: Optional[NestedConfig]`

#### Using `extra_args` in `parse_arguments`

You can now use the extended dataclass to provide additional arguments via `extra_args`:

```python
# Create the parser
parser: Parsley[Config] = create_parsley(Config)

# Define extra arguments using the extended dataclass
extra_args = PartialConfig(
    x=20,  # Override the value of x
    nested_config_overwrite=NestedConfig(z=100)  # Override the nested configuration
)

# Parse arguments with extra_args
config = parser.parse_arguments(
    config_file_path="path/to/config.yaml",
    extra_args=extra_args
)

print(config)
```

#### Example YAML File

```yaml
# config.yaml
x: 10
y: "hello"
nested_config:
  z: 42
```

#### Output

```python
Config(x=20, y="hello", nested_config=NestedConfig(z=100))
```

---
### Using `package_name` for Package-Relative YAML Paths

Parsley Coco supports resolving YAML file paths that start with `package://` by allowing you to specify a `package_name` (or package root path) in several functions, such as `parse_arguments`, `resolve_yaml_file_to_base_dataclass`, and related utilities. This enables you to reference data files within a package using a consistent, package-relative syntax.

#### Why Use `package_name`?

When developing a Python package that includes internal YAML configuration files, you may want to reference those files using paths like `package://data/config.yaml`. This is especially useful when your package is imported and used by another script or project, and you want to ensure that YAML file paths are resolved relative to the package’s location, not the caller’s working directory.

#### Example Scenario

Suppose you have a package `my_package` with the following structure:

```
my_package/
  data/
    config.yaml
  main.py
```

And your YAML file references another YAML file using a package-relative path:

```yaml
# config.yaml
nested_config_path_to_yaml_file: "package://data/nested.yaml"
```

#### Code Example

```python
from parsley import create_parsley, Parsley

@dataclass
class NestedConfig:
    z: int

@dataclass
class Config:
    x: int
    y: str
    nested_config: NestedConfig

parser: Parsley[Config] = create_parsley(Config)

# Suppose your package root is '/home/user/my_package'
config = parser.parse_arguments(
    config_file_path="/home/user/my_package/data/config.yaml",
    package_name="/home/user/my_package"
)
print(config)
```

In this example:
- Any YAML path in your config that starts with `package://` will be resolved relative to `/home/user/my_package`.
- For instance, `package://data/nested.yaml` becomes `/home/user/my_package/data/nested.yaml`.

#### When Is This Needed?

- **Package Internal Data**: When your package ships with YAML data files and you want to reference them reliably.
- **Imported Usage**: When your package is imported by another script, and you want YAML references to resolve to your package’s data, not the importing script’s directory.
- **Portability**: Ensures that YAML references work regardless of where or how your package is used.

**Tip:**
Always use the `package_name` argument when you expect to resolve `package://` paths, especially in reusable libraries or packages.

### Key Points

1. **Extended Dataclass**: The `make_partial_dataclass_with_optional_paths` function creates an extended version of the base dataclass with optional fields for paths and overwrites.
2. **Partial Instantiation**: The extended dataclass allows partial instantiation, making it flexible for use with `extra_args`.
3. **Priority**: Values provided via `extra_args` take precedence over those in the YAML file or command-line arguments.

This approach provides a powerful way to programmatically override or extend configurations while maintaining type safety and flexibility.

## Testing

Run the tests using `tox`:

```bash
tox
```

## Development

### Setting Up the Environment

1. Clone the repository:

   ```bash
   git clone https://github.com/victorgabillon/parsley-coco.git
   cd parsley-coco
   ```

2. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install .
   ```

### Running Tests

Use `tox` to run the tests:

```bash
tox
```

### Code Formatting and Linting

- Format code with `black` and `isort`:

  ```bash
  tox -e black
  tox -e isort
  ```

- Lint code with `flake8`:

  ```bash
  tox -e flake8
  ```

- Type-check with `mypy`:

  ```bash
  tox -e mypy
  ```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/victorgabillon/parsley-coco).

## License

This project is licensed under the [GPL-3.0 License](LICENSE).

## Acknowledgments

- [dacite](https://github.com/konradhalas/dacite)
- [argparse](https://docs.python.org/3/library/argparse.html)
- [PyYAML](https://pyyaml.org/)
## Python 3.14 development

```bash
uv venv --python 3.14
uv pip install -e '.[test,dev]'
source .venv/bin/activate
tox
```

Annotations are resolved with `typing.get_type_hints` before dataclass fields
are copied or used to generate CLI arguments. This supports deferred annotations
and existing string forward references without mutating the input dataclass.
`typing.Union` and `A | B` share Python 3.14's `types.UnionType` representation.
