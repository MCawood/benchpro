# Module File Creation

This document provides a detailed explanation of how module files are created in BenchPRO, with a focus on the recent enhancements to include module paths in the dependencies section.

## Module File Creation Process

When an application is built in BenchPRO, a corresponding module file is created to make the application easily loadable in a user's environment. The process involves several components working together:

1. The `Application.run()` method initiates the module file creation process after the application is built.
2. The `ModuleManager` class handles the actual creation of the module file.
3. The `WorkspaceManager` provides the necessary path information.

## Configuration Sources

Module file creation uses information from multiple sources:

1. **Application Configuration (YAML)**: Provides module dependencies and module paths:
   ```yaml
   environment:
     module_paths:
       - "/path/to/modulefiles"
     modules:
       - name: "intel"
         version: "24.0"
       - name: "impi"
         version: "21.11"
   ```

2. **Workspace Information**: Provides file paths and directory structure:
   ```yaml
   workspace:
     workspace_dir: "/path/to/workspace"
   ```

3. **Application Metadata**: Provides name, version, and binary path:
   ```yaml
   name: "hello_world_modules"
   version: "1.0"
   ```

## Module File Template

The module file template is a Jinja2 template that defines the structure of the generated Lua file:

```lua
-- {{ app_name }} {{ app_version }} module file created by BenchPro
-- Created on {{ creation_date }}

local name = "{{ app_name }}"
local version = "{{ app_version }}"

-- Description
whatis("Name: {{ app_name }}")
whatis("Version: {{ app_version }}")
whatis("Description: Application built by BenchPro")

-- Load dependencies
{% if module_paths and module_paths|length > 0 -%}
{%- for path in module_paths %}
prepend_path("MODULEPATH", "{{ path }}")
{%- endfor %}
{% endif -%}
{%- if dependencies and dependencies|length > 0 %}
{%- for dep in dependencies %}
{%- if dep is mapping and 'name' in dep %}
{%- if 'version' in dep and dep.version %}
depends_on("{{ dep.name }}/{{ dep.version }}"){% if 'description' in dep and dep.description %} -- {{ dep.description }}{% endif %}
{%- else %}
depends_on("{{ dep.name }}"){% if 'description' in dep and dep.description %} -- {{ dep.description }}{% endif %}
{%- endif %}
{%- elif dep is string %}
depends_on("{{ dep }}")
{%- endif %}
{%- endfor %}
{%- endif %}

-- Add application binary directory to PATH
prepend_path("PATH", "{{ binary_path }}")

-- Set environment variables
setenv("BP_{{ app_name_upper }}_DIR", "{{ workspace_dir }}")
```

## Module Path Support

A key enhancement to the module file creation process is the addition of module path support in the dependencies section. This ensures that dependencies specified in the configuration can be found when the module is loaded.

### How Module Paths Work

1. **Extraction from Configuration**: The `extract_module_paths_from_config()` method extracts module paths from the configuration:
   ```python
   def extract_module_paths_from_config(self, config: Dict[str, Any]) -> List[str]:
       module_paths = []
       
       if "environment" in config and "module_paths" in config["environment"]:
           paths = config["environment"]["module_paths"]
           
           for path in paths:
               if isinstance(path, str):
                   # Ensure path is absolute
                   if not os.path.isabs(path):
                       path = os.path.abspath(path)
                   module_paths.append(path)
                   
       return module_paths
   ```

2. **Module File Template**: The template includes a section to render module paths before dependencies:
   ```lua
   -- Load dependencies
   {% if module_paths and module_paths|length > 0 -%}
   {%- for path in module_paths %}
   prepend_path("MODULEPATH", "{{ path }}")
   {%- endfor %}
   {% endif -%}
   ```

3. **Application Task Integration**: The `Application.run()` and `submit_job()` methods extract and pass module paths:
   ```python
   # Extract module paths from config
   module_paths = module_manager.extract_module_paths_from_config(config)
   
   # Create the module file with direct parameters
   module_file = module_manager.create_module_file(
       app_name,
       app_version,
       workspace_dir,
       dependencies,
       binary_path,
       module_paths
   )
   ```

### Example Output

A generated module file with module paths looks like this:

```lua
-- hello_world_modules 1.0 module file created by BenchPro
-- Created on 2025-03-19 15:34:12

local name = "hello_world_modules"
local version = "1.0"

-- Description
whatis("Name: hello_world_modules")
whatis("Version: 1.0")
whatis("Description: Application built by BenchPro")

-- Load dependencies

prepend_path("MODULEPATH", "/Users/mcawood/dev/benchpro_2.0/modulefiles")

depends_on("intel/24.0")
depends_on("impi/21.11")

-- Add application binary directory to PATH
prepend_path("PATH", "/Users/mcawood/.benchpro/outputs/application/hello_world_modules_1742416452_azdtxc")

-- Set environment variables
setenv("BP_HELLO_WORLD_MODULES_DIR", "/Users/mcawood/.benchpro/outputs/application/hello_world_modules_1742416452_azdtxc")
```

## Whitespace Control

The template uses Jinja2 whitespace control to ensure the generated module file has clean formatting:

- `{%-` at the beginning of a control block removes whitespace before that block
- `-%}` at the end of a control block removes whitespace after that block

This prevents excessive blank lines in the generated module file.

## Error Handling

The module file creation process includes robust error handling:

1. **Directory Creation**: If the module file directory doesn't exist, it is created.
2. **Template Rendering**: Errors during template rendering are caught and reported.
3. **File Writing**: File I/O errors are caught and reported.
4. **Verification**: The generated module file is verified to ensure it contains all required elements.

## Integration with Application Registry

After a module file is created, its path is included in the application data stored in the registry:

```python
app_id = registry_manager.register_application(
    {
        "name": app_name,
        "version": app_version,
        "workspace_dir": workspace_dir,
        "binary_path": os.path.join(workspace_dir, app_name),
        "environment": config.get("environment", {"modules": []})
    }
)
```

This allows users to see information about the module file when using the `bp apps info` command.

## Best Practices

When working with module files in BenchPRO:

1. **Always include module paths**: If your application requires modules not in the standard module path, include the appropriate module_paths in your configuration.

2. **Use absolute paths**: Module paths should be absolute to ensure they can be found regardless of where the module is loaded.

3. **Include complete dependency information**: Always provide both name and version for dependencies to ensure proper resolution.

4. **Test module loading**: After building an application, test loading the module file to ensure it correctly sets up the environment.

## Troubleshooting

Common issues with module file creation and their solutions:

1. **Missing dependencies**: If a dependency can't be found when loading the module, check that the module path is correctly specified in the configuration.

2. **Path resolution issues**: If the binary path isn't correctly added to PATH, ensure the workspace directory is correctly specified in the configuration.

3. **Formatting issues**: If the module file has formatting issues, check the template whitespace control to ensure it's rendering correctly.

## Related Documentation

- [Module Manager](module_manager.md): Details on the ModuleManager class
- [Workspace Manager](workspace_manager.md): Information on workspace management
- [Application Tasks](../executor/task_composition.md): Integration with application tasks 