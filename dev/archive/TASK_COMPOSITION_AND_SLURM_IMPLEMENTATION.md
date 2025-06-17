# Task Composition and Slurm Executor Implementation Plan

## Overview

This document outlines the implementation plan for two related architectural improvements:

1. **Task Composition System Refactoring**: Converting the current inheritance-based task hierarchy to use composition for better flexibility, testability, and extensibility.

2. **Slurm Executor Implementation**: Integrating Slurm scheduling capability that maintains a single-template approach where users don't need separate templates for local and Slurm execution.

## Current Architecture

The current system uses:
- A base `Task` class with derived `Application` and `Benchmark` classes
- Direct inheritance for code reuse and customization
- A `TaskFactory` that creates tasks based on type
- An existing but not fully integrated `Executor` class hierarchy with `LocalExecutor` and `SchedulerExecutor` implementations
- An existing but not fully utilized `Scheduler` interface with `SlurmScheduler` implementation

## Implementation Goals

### Task Composition Goals
- Replace inheritance with composition for flexibility
- Improve testability by allowing component mocking
- Improve extensibility for future task types
- Simplify customization of task behavior

### Slurm Executor Goals
- Support Slurm job submission using existing `SlurmScheduler`
- Generate Slurm directives from configuration automatically
- Maintain a single-template approach where templates are independent of execution mode
- Support basic Slurm functionality initially with room for future expansion

## Implementation Plan

### Phase 1: Component Interfaces ✅

1. **Define Component Interfaces** ✅
   - Created abstract base classes for each task responsibility
   - Ensured clean separation of concerns
   - Implemented in a new module: `benchpro/executor/components/interfaces.py`
   - Created comprehensive documentation in `docs/reference/executor/components.md`
   - Added basic tests in `benchpro/tests/test_component_interfaces.py`

```python
# Component interfaces
class ConfigComponent(ABC):
    def load_config(self, config_path: str) -> Dict[str, Any]: pass
    def get_config(self) -> Dict[str, Any]: pass
    def merge_config(self, override_config: Dict[str, Any]) -> Dict[str, Any]: pass

class ValidationComponent(ABC):
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]: pass
    def get_required_fields(self) -> List[str]: pass

class ScriptGenerationComponent(ABC):
    def generate_script(self, template_path: str, variables: Dict[str, Any]) -> str: pass
    def prepare_variables(self, config: Dict[str, Any]) -> Dict[str, Any]: pass

class ExecutionComponent(ABC):
    def execute(self, script_path: str) -> Tuple[bool, Optional[str]]: pass
    def get_status(self, job_id: str) -> str: pass
    def cancel_job(self, job_id: str) -> bool: pass
```

### Phase 2: Component Implementations ✅

2. **Implement Configuration Components** ✅
   - Created `BaseConfigComponent` with common functionality
   - Implemented `ApplicationConfigComponent` for application-specific configuration
   - Implemented `BenchmarkConfigComponent` for benchmark-specific configuration
   - Added integration with existing ConfigManager

3. **Implement Validation Components** ✅
   - Created `BaseValidationComponent` with common validation logic
   - Implemented `ApplicationValidationComponent` for application-specific validation
   - Implemented `BenchmarkValidationComponent` for benchmark-specific validation
   - Added proper error reporting for configuration issues

4. **Implement Script Generation Components** ✅
   - Created `BaseScriptGenerator` with common functionality
   - Implemented `LocalScriptGenerator` that renders templates directly
   - Implemented `SlurmScriptGenerator` that adds Slurm directives before template content
   - Ensured both generators use the same template files but produce different scripts

```python
class SlurmScriptGenerator(BaseScriptGenerator):
    def generate_script(self, template_path, variables):
        # Generate Slurm directives based on job config
        slurm_directives = self._generate_slurm_directives(variables)
        
        # Render the template with the provided variables
        template_content = self.template_engine.render(template_path, variables)
        
        # Combine directives with template content
        return slurm_directives + "\n\n" + template_content
```

5. **Implement Execution Components** ✅
   - Created `LocalExecutionComponent` that uses subprocess to run scripts
   - Implemented `SlurmExecutionComponent` that uses the existing `SlurmScheduler`
   - Added proper error handling and status reporting
   - Made components testable with dependency injection

```python
class LocalExecutionComponent(ExecutionComponent):
    def execute(self, script_path):
        # Execute locally using subprocess
        # Return process_id as job_id
        
class SlurmExecutionComponent(ExecutionComponent):
    def execute(self, script_path):
        # Submit to Slurm using SlurmScheduler
        # Return job_id from Slurm
```

6. **Implement Component Testing** ✅
   - Created comprehensive tests for all component implementations
   - Used mock objects to isolate components during testing
   - Verified proper behavior for both success and error cases
   - Ensured testability on systems without Slurm installed

### Phase 3: Task Refactoring ✅

7. **Refactor Task Base Class** ✅
   - Modified to accept components in constructor
   - Delegated behavior to components instead of implementing directly
   - Created a new file `task_composition.py` to avoid disrupting existing code
   - Implemented proper error handling and logging

```python
class Task:
    def __init__(self, 
                 config_component,
                 validation_component,
                 script_generation_component,
                 execution_component):
        self.config_component = config_component
        self.validation_component = validation_component
        self.script_generation_component = script_generation_component
        self.execution_component = execution_component
        
    def run(self):
        # Load and validate config
        config = self.config_component.get_config()
        is_valid, errors = self.validation_component.validate(config)
        
        # Generate script
        variables = self.script_generation_component.prepare_variables(config)
        script_content = self.script_generation_component.generate_script(
            template_path, variables
        )
        
        # Write script to file
        script_path = self._write_script_to_file(script_content)
        
        # Execute script
        success, job_id = self.execution_component.execute(script_path)
        
        return job_id
```

8. **Update Application and Benchmark Classes** ✅
   - Created composition-based versions of Application and Benchmark classes
   - Maintained integration with legacy components (registries, extractors)
   - Ensured backward compatibility with existing APIs
   - Added comprehensive tests for the new implementations

### Phase 4: Factory and Integration ✅

9. **Update TaskFactory** ✅
   - Created a new `TaskFactoryComposition` in a separate file
   - Implemented component creation and injection
   - Added configuration-based execution type selection
   - Ensured proper error handling and logging

```python
class TaskFactoryComposition:
    def create_task(self, task_type, execution_type=None, config=None):
        # Determine execution type from config if not specified
        if execution_type is None and config:
            execution_type = config.get('execution', {}).get('type', 'local')
        
        # Create components based on task_type and execution_type
        config_component = self._create_config_component(task_type)
        validation_component = self._create_validation_component(task_type)
        script_gen_component = self._create_script_generation_component(execution_type)
        execution_component = self._create_execution_component(execution_type)
        
        # Create and return the task instance
        if task_type == "application":
            return Application(
                config_component, 
                validation_component,
                script_gen_component, 
                execution_component,
                registry_manager=self.registry_manager
            )
        elif task_type == "benchmark":
            return Benchmark(
                config_component, 
                validation_component,
                script_gen_component, 
                execution_component,
                registry_manager=self.registry_manager
            )
```

10. **Create Comprehensive Tests** ✅
    - Implemented tests for the Task, Application, and Benchmark classes
    - Added tests for the TaskFactoryComposition
    - Verified component integration and behavior
    - Used mock objects to isolate tests from external dependencies

### Phase 5: CLI Integration ✅

11. **Integrate with CLI System** ✅
    - Created a new `TaskOrchestratorComposition` class that uses our component-based architecture
    - Updated CLI commands to support both original and composition-based architectures
    - Added command-line options for specifying execution type
    - Maintained backward compatibility with existing CLI
    - Implemented special handling for legacy executor types

```python
@cli.command()
@click.argument("profile", shell_complete=get_profile_names)
# ... other options ...
@click.option(
    "--executor",
    type=click.Choice(["local", "scheduler"]),
    help="Executor to use for running the build. If not specified, uses the default from configuration."
)
@click.option(
    "--execution-type",
    type=click.Choice(["local", "slurm"]),
    help="Execution type to use for running the build. If not specified, uses executor or the default from configuration."
)
@click.option(
    "--use-composition",
    is_flag=True,
    help="Use the composition-based task architecture."
)
def build(profile, output_dir=None, system=None, dry_run=False,
          executor=None, execution_type=None, force=False, version=None, use_composition=False):
    # ... implementation ...
```

12. **Add Migration Path** ✅
    - Added a `--use-composition` flag to CLI commands to opt into the new architecture
    - Provided clean mapping from legacy executor types to new execution types
    - Ensured both architectures can coexist during migration
    - Added comprehensive tests for the new TaskOrchestratorComposition

## Implementation Order and Dependencies

1. Component interfaces (no dependencies) ✅
2. Basic component implementations (depends on interfaces) ✅
3. Task base class refactoring (depends on components) ✅
4. Application/Benchmark refactoring (depends on Task base class) ✅
5. TaskFactory updates (depends on all components and Task classes) ✅
6. CLI integration (depends on TaskFactory) ✅
7. Testing (depends on all implementations) ✅

## Documentation

Documentation for the component architecture is maintained in:
- `docs/reference/executor/index.md`: Overview of the executor module
- `docs/reference/executor/components.md`: Detailed documentation of component interfaces and usage
- `docs/reference/executor/task_composition.md`: Documentation of the composition-based task architecture

## Current Progress

We have successfully implemented all phases of the plan:

1. **Component Interfaces**: Defined clear interfaces for all component types
2. **Component Implementations**: Created concrete implementations for all components
3. **Task Refactoring**: Implemented new Task classes using component composition
4. **Factory and Integration**: Created a factory to assemble tasks from components
5. **CLI Integration**: Updated CLI commands to use the new architecture

The implementation provides:
- A clean separation of concerns with single-responsibility components
- Improved testability through mock component injection
- Flexible configuration of task behavior through component selection
- Support for both local and Slurm execution with a single template approach
- Backward compatibility with existing code through gradual migration

## Migration Strategy

To allow for a gradual transition to the new architecture, we've implemented a migration strategy:

1. **Parallel Implementation**: The new architecture exists alongside the original one
2. **Opt-in Flag**: Users can opt into the new architecture using the `--use-composition` flag
3. **Configuration Support**: Both execution types can be specified in YAML or via CLI
4. **Compatibility Layer**: Legacy executor types are automatically mapped to new execution types
5. **Familiar API**: The CLI experience remains largely the same, with new options available

This approach allows for testing and validation of the new architecture in production while maintaining stability for existing users.

## Future Enhancements

After completing the initial implementation, consider these enhancements:

1. **Advanced Slurm Features**
   - Array jobs support
   - Job dependencies
   - More directive customization

2. **Additional Schedulers**
   - PBS/Torque support
   - LSF support
   - Grid Engine support

3. **Runtime Component Switching**
   - Allow switching execution components at runtime
   - Support for hybrid execution models

4. **Full Transition**
   - Once the new architecture is proven, make it the default
   - Consider eventually deprecating the inheritance-based implementation

## Conclusion

This implementation plan provided a roadmap for converting the task system to use composition over inheritance while simultaneously implementing Slurm execution support. The phased approach allowed for incremental progress and testing at each stage.

The resulting architecture is more flexible, extensible, and testable, providing a solid foundation for future enhancements to BenchPro's execution capabilities. 