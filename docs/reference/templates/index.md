# Template System Reference

The BenchPRO template system uses a block-based composition approach to generate execution scripts. This modular design simplifies templates, improves maintainability, and enhances flexibility.

## Overview

The BenchPRO template system consists of several key components:

1. **Template Blocks**: Modular script segments with specific roles
2. **Composition Engine**: Assembles blocks into complete scripts
3. **Standard Block Library**: Pre-built blocks for common script elements
4. **Script Generators**: Components that use the template system to generate execution scripts

This architecture separates concerns and reduces duplication across templates, allowing users to focus on task-specific commands rather than boilerplate script setup.

## Core Components

### Template Blocks

Template blocks represent reusable script segments with defined priorities and execution contexts. Each block is rendered independently and then assembled into a complete script.

```python
class TemplateBlock(ABC):
    """Abstract base class for template blocks."""
    
    def __init__(self, name: str, priority: int, 
                 description: str = "", 
                 contexts: Optional[List[str]] = None):
        # ...
        
    @abstractmethod
    def render(self, context: Dict[str, Any], execution_context: str) -> str:
        """Render this block with the given context variables."""
        pass
        
    def applies_to_context(self, execution_context: str) -> bool:
        """Check if this block applies to the given execution context."""
        pass
```

#### Block Types

There are three primary types of template blocks:

1. **StringTemplateBlock**: Contains inline template content, rendered with Jinja2
   ```python
   StringTemplateBlock(
       name="shebang",
       content="#!/bin/bash",
       priority=10,
       description="Bash shebang line"
   )
   ```

2. **FileTemplateBlock**: Loads a template from a file
   ```python
   FileTemplateBlock(
       name="user_commands",
       file_path="/path/to/template.j2",
       priority=100,
       description="User command script"
   )
   ```

3. **FunctionTemplateBlock**: Generates content using a Python function
   ```python
   FunctionTemplateBlock(
       name="dynamic_content",
       function=generate_dynamic_content,
       priority=50,
       description="Dynamically generated content"
   )
   ```

### Composition Engine

The `TemplateCompositionEngine` is responsible for assembling blocks into complete scripts:

1. Blocks are registered with the engine
2. The engine filters blocks by execution context
3. Remaining blocks are sorted by priority
4. Each block is rendered with provided variables
5. Rendered blocks are joined to create the final script

```python
engine = TemplateCompositionEngine()
engine.register_block(SHEBANG_BLOCK)
engine.register_block(USER_COMMANDS_BLOCK)
script = engine.compose(variables, execution_context="local")
```

### Script Generators

Script generators implement the `ScriptGenerationComponent` interface and use the composition engine to generate scripts:

```python
class ComposableScriptGenerator(ScriptGenerationComponent):
    """Script generator that uses template composition."""
    
    def __init__(self, execution_context: str):
        self.execution_context = execution_context
        self.composition_engine = TemplateCompositionEngine()
        register_standard_blocks(self.composition_engine, execution_context)
        
    def generate_script(self, template_path: str, variables: Dict[str, Any]) -> str:
        # Create a block for the user template
        user_block = FileTemplateBlock(
            name="user_commands",
            file_path=template_path,
            priority=PRIORITY_USER_COMMANDS
        )
        
        # Register the block and compose the script
        self.composition_engine.register_block(user_block)
        script = self.composition_engine.compose(variables, self.execution_context)
        
        # Clean up and return the script
        self.composition_engine.unregister_block("user_commands")
        return script
```

Two specialized generators are provided:

1. **LocalScriptGenerator**: For generating scripts for local execution
2. **SlurmScriptGenerator**: For generating scripts for SLURM execution

## Standard Blocks

BenchPRO provides a library of standard blocks for common script elements:

| Block Name | Description | Priority | Execution Context |
|------------|-------------|----------|-------------------|
| `shebang` | Bash interpreter directive | 10 | All |
| `slurm_directives` | SLURM job scheduler directives | 20 | SLURM only |
| `workspace_dir` | Workspace directory handling | 30 | All |
| `module_loading` | Module loading commands | 40 | All |
| `env_vars` | Environment variable setup | 50 | All |
| `start_timestamp` | Start time logging | 60 | All |
| `user_commands` | User-provided command script | 100 | All |
| `end_timestamp` | End time logging | 900 | All |

### Block Priorities

Block priorities determine the order in which blocks appear in the final script. Lower values come first. Standard priorities are:

```python
PRIORITY_SHEBANG = 10           # First: script interpreter
PRIORITY_HEADER_COMMENTS = 15   # Header comments and metadata
PRIORITY_SLURM_DIRECTIVES = 20  # SLURM-specific directives
PRIORITY_WORKSPACE_DIR = 30     # Workspace directory handling
PRIORITY_MODULE_LOADING = 40    # Module loading commands
PRIORITY_ENV_VARS = 50          # Environment variable setup
PRIORITY_START_TIMESTAMP = 60   # Start time logging
PRIORITY_USER_COMMANDS = 100    # User-provided commands
PRIORITY_END_TIMESTAMP = 900    # End time logging
PRIORITY_FOOTER = 1000          # Last: footer elements
```

## Using the Template System

### Creating Task Templates

When using the block-based template system, task templates can focus solely on task-specific commands:

```jinja
# Build the application
echo "Building application: {{ name }} v{{ version }}"
{% if build.compiler %}
{{ build.compiler }} {{ build.flags }} -o {{ build.output }} {{ build.source }}
{% endif %}
```

The system will automatically add headers, environment setup, and other boilerplate elements.

### Adding Custom Blocks

Custom blocks can be added to extend functionality:

```python
custom_block = StringTemplateBlock(
    name="custom_header",
    content="# This script was generated by BenchPRO v2.0",
    priority=15,  # After shebang, before directives
    description="Custom header comment"
)

engine = TemplateCompositionEngine()
register_standard_blocks(engine, "local")
engine.register_block(custom_block)
```

### Execution Context-Specific Blocks

Blocks can be limited to specific execution contexts:

```python
gpu_block = StringTemplateBlock(
    name="gpu_setup",
    content="# GPU Setup\nexport CUDA_VISIBLE_DEVICES=0,1",
    priority=55,
    description="GPU environment setup",
    contexts=["gpu", "slurm-gpu"]  # Only for GPU contexts
)
```

## Error Handling

The template system includes robust error handling through the `TemplateError` exception class:

```python
try:
    script = generator.generate_script(template_path, variables)
except TemplateError as e:
    print(f"Error generating script: {e}")
```

Common errors include:
- Missing template files
- Syntax errors in templates
- Variable references to undefined variables
- File system permission issues

## Best Practices

1. **Minimal User Templates**: Keep user templates focused on task-specific commands
2. **Appropriate Priorities**: Choose priorities carefully to ensure correct script order
3. **Descriptive Names**: Use clear names for custom blocks
4. **Context Filtering**: Use context filtering to limit blocks to appropriate scenarios
5. **Error Handling**: Implement proper error handling for template failures

## Integration with Task System

The template system integrates with the task composition architecture through the `ScriptGenerationComponent` interface:

```python
task = Task(
    config_component=config_component,
    validation_component=validation_component,
    script_generation_component=LocalScriptGenerator(),  # Template-based generator
    execution_component=execution_component
)
```

This allows tasks to leverage the template system while maintaining the benefits of the composition-based architecture. 