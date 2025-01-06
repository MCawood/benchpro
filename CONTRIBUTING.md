# Contributing to BenchPRO

This document serves as the primary guide for both human developers and AI assistants contributing to BenchPRO.

## Project Architecture

### Directory Structure
```
benchpro/
├── cli/            # Command Line Interface
│   ├── task.py     # CLI task commands
│   └── __init__.py # CLI initialization
├── core/           # Core domain logic
│   ├── domain/     # Domain models
│   │   ├── task.py
│   │   ├── job.py
│   │   └── templates/  # Template management
│   ├── services/   # Business logic
│   │   └── template_service.py
│   ├── ports/      # Interfaces
│   │   └── executor.py
│   ├── executor/   # Execution handling
│   │   ├── base.py    # Base executor class
│   │   └── local.py   # Local execution implementation
│   ├── validation/ # Input validation
│   │   └── validators.py  # Validation rules
│   └── infrastructure/ # Implementations
│       └── local_executor.py
├── docs/           # Project documentation
│   ├── architecture/  # Architecture documentation
│   │   ├── domain_models.rst
│   │   ├── executors.rst
│   │   ├── project_structure.rst
│   │   ├── templates.md
│   │   └── validation.rst
│   ├── api/           # API reference
│   ├── guides/        # User guides
│   └── planning/      # Project planning docs
├── examples/       # Example configurations
│   ├── templates/     # Example templates
│   │   ├── hello.sh
│   │   └── basic/
│   └── workspaces/   # Example workspace setups
├── repo/          # Repository management
│   └── benchpro/     # Package repository
├── templates/     # Job templates
│   └── applications/ # Application-specific templates
│       ├── hello_world/    # Basic hello world example
│       ├── matrix_mult/    # Matrix multiplication benchmark
│       └── pi_calculator/  # Pi calculation benchmark
└── tests/         # Test suite
```

### Key Design Decisions

1. **Domain-Driven Design**
   - Clear separation of concerns with core/domain, services, ports, and infrastructure
   - Domain models (Task, Job) are the source of truth
   - Business logic in services (template_service.py)
   - Infrastructure behind interfaces (executor.py)

2. **Asynchronous Execution**
   - All task and job operations are async (run, status, stop, cleanup)
   - Non-blocking process management with asyncio
   - Graceful task cancellation with timeouts
   - Event-based state transitions

3. **Resource Management**
   - Explicit resource validation (cores, memory)
   - Runtime monitoring of CPU, memory, and I/O
   - Automatic cleanup of processes and monitors
   - Resource usage tracking per task and job

4. **Configuration and Templates**
   - Schema-based validation with Pydantic models
   - Environment-aware task configuration
   - Template-based job execution
   - Standardized logging and output handling

## Development Process

We follow a strict test-driven development approach:

1. **Start with Tests**
   - Write comprehensive unit tests with pytest
   - Cover both success and error cases
   - Test async operations with pytest.mark.asyncio
   - Include fixtures for common test scenarios

2. **Implementation**
   - Follow type hints and Pydantic models
   - Use async/await for all I/O operations
   - Handle resource cleanup in finally blocks
   - Implement abstract base classes

3. **Testing Layers**
   - Unit tests for domain models
   - Integration tests for executors
   - CLI command testing with CliRunner
   - Mock external dependencies

4. **Error Handling**
   - Custom exception hierarchy
   - Graceful error state transitions
   - Resource cleanup on failure
   - Detailed error messages

## Code Quality Requirements

1. **Type Safety**
   - Use type hints consistently
   - Validate with Pydantic models
   - Custom validators for complex types
   - Strong exception hierarchy

2. **Documentation**
   - Docstrings for all modules
   - Function/method documentation with Args/Returns/Raises
   - Sphinx-compatible format
   - ReadTheDocs integration

3. **Testing**
   - Pytest for all components
   - Async test support
   - Comprehensive fixtures
   - Mock external dependencies

4. **Code Organization**
   - Domain-driven structure
   - Clear module boundaries
   - Interface-based design
   - Resource lifecycle management

## Pull Request Process

1. **Pre-Submission Checklist**
   - [ ] Tests written and passing
   - [ ] Documentation updated
   - [ ] Code follows quality rules
   - [ ] Performance impact assessed
   - [ ] Error handling complete

2. **Review Process**
   - Address all review comments
   - Update tests if needed
   - Verify CI pipeline passes
   - Get maintainer approval

3. **Post-Merge**
   - Monitor for issues
   - Update documentation
   - Help with user questions
   - Consider improvements

## For AI Assistants

When working on this project:

1. **Development Approach**
   - Follow test-first development
   - Make small, verifiable changes
   - Document decisions
   - Validate against requirements

2. **Code Generation**
   - Follow established patterns
   - Include comprehensive tests
   - Add detailed comments
   - Handle edge cases

3. **Review Process**
   - Verify test coverage
   - Check error handling
   - Assess performance
   - Validate documentation

## Getting Started

1. Set up your development environment:
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/benchpro.git
   cd benchpro

   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install development dependencies
   pip install -e ".[test,dev]"
   ```

2. Run the tests:
   ```bash
   pytest
   ```

3. Explore the codebase:
   - Start with domain models in `core/domain/`
   - Review service implementations in `core/services/`
   - Check interface definitions in `core/ports/`

## Resources

- [Project Documentation](docs/README.md)
- [API Reference](docs/api/README.md)
- [Testing Guide](docs/testing/README.md)
- [Architecture Guide](docs/architecture/README.md)

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
