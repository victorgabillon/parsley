# Parsley Coco

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Formatted with isort](https://img.shields.io/badge/isort-checked-green)](https://pycqa.github.io/isort/index.html)
[![Linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
[![Tests](https://github.com/victorgabillon/chipiron/actions/workflows/ci.yaml/badge.svg)](https://github.com/victorgabillon/chipiron/actions)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

## Overview

Parsley Coco is a Python library that combines the power of `dacite` and `argparse` to provide a flexible and extensible parser for command-line arguments and configuration files. It supports recursive YAML parsing, dataclass-based argument definitions, and merging of arguments from multiple sources.


## Features

- **Recursive YAML Parsing**: Parse nested YAML files into Python dataclasses.
- **Dataclass-Based Argument Parsing**: Define arguments using Python dataclasses for type safety and clarity.
- **Command-Line and Config File Integration**: Merge arguments from command-line inputs, YAML config files, and extra arguments.
- **`extra_args` Support**: Programmatically provide additional arguments using an extended version of the base dataclass, allowing for flexible overrides and dynamic configurations.
- **Overwrite Functionality**: Automatically resolve nested configurations and apply overwrite values from YAML files or programmatically provided arguments.


## Requirements

- Python 3.12 or higher

## Installation

To install the library, use `pip`:

```bash
pip install parsley-coco
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
from parsley_coco import create_parsley, Parsley

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
     - These arguments are merged with other sources and take precedence over YAML but are overridden by command-line arguments.
  2. **`config_file_path`** (optional):
     - A string specifying the path to a YAML configuration file.
     - If not provided, the parser looks for a `config_file_name` key in `extra_args` or command-line arguments.

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
from parsley_coco.alternative_dataclasses import make_dataclass_with_optional_paths_and_overwrite, make_partial_dataclass_with_optional_paths
from parsley_coco.factory import create_parsley

parser = create_parsley(Config)

# creating an extented config dataclass that allows more flexibility (more later in the readme)
ExtendedConfig = make_partial_dataclass_with_optional_paths(Config)

# Parse arguments
config = parser.parse_arguments(
    config_file_path="tests_parsley/yaml_files/config.yaml",
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
from parsley_coco import create_parsley, Parsley

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
from parsley_coco import create_parsley, Parsley

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

If no configuration file is provided, Parsley Coco will instantiate the dataclass using its default arguments. This means that all fields in your dataclass should either have default values or be optional to ensure proper initialization.

#### Example

```python
from dataclasses import dataclass
from parsley_coco import create_parsley, Parsley

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
1. **Default Values**: Fields in the dataclass should have default values or be optional to avoid errors when no configuration file is provided.
2. **Fallback Behavior**: This ensures that your application can run with default settings even if no external configuration is supplied.

By designing your dataclass with defaults, you make your application more robust and user-friendly.

### Command-Line Arguments Handling

Parsley Coco integrates seamlessly with `argparse` to handle command-line arguments. Command-line arguments take the highest priority when merging configurations from multiple sources (e.g., YAML files, `extra_args`, and defaults).

#### How It Works

1. **Automatic Argument Parsing**: Parsley Coco automatically generates command-line arguments based on the fields in your dataclass.
2. **Priority**: Command-line arguments override values from YAML files, `extra_args`, and default values in the dataclass.
3. **Type Safety**: The types of the arguments are inferred from the dataclass fields, ensuring type safety.

#### Example

```python
from dataclasses import dataclass
from parsley_coco import create_parsley, Parsley

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
from parsley_coco import create_parsley, Parsley
from parsley_coco.alternative_dataclasses import make_partial_dataclass_with_optional_paths

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