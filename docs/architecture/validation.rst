Validation System
===============

BenchPRO includes a robust validation system to ensure data integrity and proper resource usage. The validation system is built around custom validators and clear error messages.

Core Validators
-------------

The system includes several specialized validators:

DirectoryPath Validator
^^^^^^^^^^^^^^^^^^^^

Validates and ensures directory paths exist:

.. code-block:: python

    class DirectoryPathValidator:
        def __call__(self, path: Path) -> None:
            if not path.exists():
                raise ValidationError(f"Directory does not exist: {path}")
            if not path.is_dir():
                raise ValidationError(f"Path is not a directory: {path}")

FileValidator
^^^^^^^^^^^

Validates file paths and permissions:

.. code-block:: python

    class FileValidator:
        def __call__(self, path: Path) -> None:
            if not path.exists():
                raise ValidationError(f"File does not exist: {path}")
            if not path.is_file():
                raise ValidationError(f"Path is not a file: {path}")
            if not os.access(path, os.X_OK):
                raise ValidationError(f"File is not executable: {path}")

MemoryString Validator
^^^^^^^^^^^^^^^^^^

Validates memory specifications:

.. code-block:: python

    class MemoryStringValidator:
        def __call__(self, value: str) -> None:
            pattern = r'^\d+(\.\d+)?[KMGT]?$'
            if not re.match(pattern, value):
                raise ValidationError(
                    f"Invalid memory format: {value}. "
                    "Expected format: NUMBER[UNIT], e.g., 8G, 512M"
                )

Variables Validator
^^^^^^^^^^^^^^^

Validates task variables:

.. code-block:: python

    class VariablesValidator:
        def __call__(self, variables: Dict[str, Any]) -> None:
            for key, value in variables.items():
                if not isinstance(key, str):
                    raise ValidationError(f"Variable key must be string: {key}")
                if not isinstance(value, (str, int, float, bool)):
                    raise ValidationError(
                        f"Variable value must be primitive type: {value}"
                    )

Usage in Models
-------------

Validators are used in model field definitions:

.. code-block:: python

    class Task:
        working_dir: Path = Field(validator=DirectoryPathValidator())
        template_path: Path = Field(validator=FileValidator())
        variables: Dict[str, Any] = Field(validator=VariablesValidator())

    class JobResources:
        memory: str = Field(validator=MemoryStringValidator())

Validation Process
---------------

1. **Field Level**: Each field is validated independently
2. **Model Level**: Cross-field validations are performed
3. **Runtime**: Additional validations during execution

Error Handling
------------

Validation errors provide clear messages:

.. code-block:: python

    try:
        task = Task(
            working_dir="/nonexistent",
            template_path="/also/nonexistent",
            variables={"invalid": object()}
        )
    except ValidationError as e:
        print(e)  # Clear error message with context

Best Practices
------------

1. **Early Validation**: Validate inputs before processing
2. **Clear Messages**: Provide actionable error messages
3. **Fail Fast**: Catch invalid states early
4. **Consistent Format**: Use consistent error message format

Custom Validators
--------------

Creating custom validators:

.. code-block:: python

    class CustomValidator:
        def __init__(self, **options):
            self.options = options

        def __call__(self, value: Any) -> None:
            if not self._is_valid(value):
                raise ValidationError(f"Invalid value: {value}")

        def _is_valid(self, value: Any) -> bool:
            # Custom validation logic
            return True

Future Enhancements
----------------

Planned validation improvements:

* Schema-based validation
* Async validation support
* Custom validation rules
* Validation rule composition 