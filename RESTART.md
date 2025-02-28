# BenchPro - Minimal Working System (MWS)

## Core Principles
1. **Simplicity First**
   - Start with the absolute minimum needed to run a script
   - No premature optimization or abstraction
   - Each feature must be fully functional before moving on

2. **Test-Driven Development**
   - Write tests for the minimal functionality first
   - Get tests passing before adding complexity
   - Keep test coverage high but focused

3. **Incremental Development**
   - Build in small, verifiable steps
   - Each step must maintain a working system
   - Document decisions and trade-offs

## Phase 1: Hello World
### Goal
Run a simple hello world script and verify its output.

### Implementation Steps
1. **Basic Project Structure**
   ```
   benchpro/
   ├── cli/
   │   └── task.py (init, create, run commands)
   ├── core/
   │   ├── task.py (Task class)
   │   └── executor.py (local execution)
   └── tests/
       └── test_hello_world.py
   ```

2. **Minimal Task Class**
   ```python
   class Task:
       def __init__(self, name: str, script_path: str, working_dir: str):
           self.name = name
           self.script_path = script_path
           self.working_dir = working_dir
   ```

3. **Simple Executor**
   ```python
   class Executor:
       def run(self, task: Task) -> bool:
           # Copy script to working dir
           # Execute script
           # Return success/failure
   ```

4. **Basic CLI**
   ```python
   @click.group()
   def cli():
       pass

   @cli.command()
   def run(script: str):
       # Create task
       # Run task
       # Show output
   ```

### Success Criteria
- [ ] Can run hello world script
- [ ] Can verify script output
- [ ] All tests pass
- [ ] No complex features

## Phase 2: Basic Task Management
### Goal
Create, list, and run tasks with basic state tracking.

### Implementation Steps
1. **Task States**
   ```python
   class TaskState(Enum):
       CREATED = "created"
       RUNNING = "running"
       COMPLETED = "completed"
       FAILED = "failed"
   ```

2. **Task Operations**
   - Create task from template
   - List existing tasks
   - Get task status
   - View task output

### Success Criteria
- [ ] Can create task from template
- [ ] Can list tasks
- [ ] Can track task state
- [ ] Can view task output

## Phase 3: Resource Management
### Goal
Add basic resource limits and tracking.

### Implementation Steps
1. **Resource Specification**
   ```python
   class Resources:
       def __init__(self, cores: int = 1, memory: str = "1G"):
           self.cores = cores
           self.memory = memory
   ```

2. **Resource Validation**
   - Validate available resources
   - Track resource usage
   - Enforce resource limits

### Success Criteria
- [ ] Can specify resource requirements
- [ ] Can validate available resources
- [ ] Can enforce resource limits

## Development Guidelines

### 1. Code Changes
- Make small, focused changes
- Test each change thoroughly
- Document why changes are made
- Keep changes reversible

### 2. Testing
- Write tests before implementation
- Keep tests simple and focused
- Test error cases explicitly
- Maintain test coverage

### 3. Documentation
- Document design decisions
- Keep documentation current
- Include examples
- Document limitations

### 4. Review Process
- Review changes in small batches
- Verify tests pass
- Check documentation
- Ensure backward compatibility

## Common Pitfalls to Avoid

1. **Over-engineering**
   - Don't add features "just in case"
   - Avoid premature optimization
   - Keep interfaces simple
   - Don't over-abstract

2. **Complexity Creep**
   - Don't add async until needed
   - Keep state management simple
   - Minimize dependencies
   - Avoid complex inheritance

3. **Feature Creep**
   - Stick to core requirements
   - Don't add "nice to have" features
   - Keep scope focused
   - Build one thing at a time

## Next Steps After MWS

Only after the MWS is stable and well-tested:

1. **Advanced Features**
   - Multiple executor types
   - Advanced resource management
   - Job queuing
   - Monitoring and metrics

2. **Performance Improvements**
   - Async execution
   - Parallel task running
   - Resource optimization
   - Caching

3. **Integration**
   - External schedulers
   - Cloud providers
   - Monitoring systems
   - Authentication

Remember: Each addition must maintain system stability and simplicity. 