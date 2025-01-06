Project Structure
================

Overview
--------
BenchPRO follows clean architecture principles with clear separation between domain logic, infrastructure, and interfaces.

Directory Structure
-----------------

.. code-block:: text

    benchpro/
    ├── benchpro/           # Main package source code
    │   ├── cli/           # Command Line Interface
    │   │   ├── __init__.py
    │   │   └── task.py    # Task management commands
    │   └── core/          # Core business logic
    │       ├── domain/    # Domain models and business rules
    │       ├── executor/  # Task execution implementations
    │       ├── infrastructure/  # External interfaces
    │       ├── ports/          # Interface definitions
    │       ├── services/       # Application services
    │       └── validation/     # Input validation
    │
    ├── tests/             # Test suite
    │   ├── unit/         # Unit tests
    │   └── data/         # Test data and templates
    │
    ├── docs/             # Documentation
    │   ├── architecture/
    │   ├── guides/
    │   └── api/
    │
    └── examples/         # Example code and templates
        ├── templates/
        └── workspaces/

Key Components
-------------

Core Domain
~~~~~~~~~~
The core domain contains the business logic and domain models:

* ``domain/``: Core business objects and rules
* ``executor/``: Task execution implementations
* ``ports/``: Interface definitions
* ``infrastructure/``: External service implementations
* ``validation/``: Input validation logic

CLI Interface
~~~~~~~~~~~~
The command-line interface provides user interaction:

* Task management commands
* Resource allocation
* Workspace management

Test Organization
~~~~~~~~~~~~~~~
Tests are organized to separate logic from data:

* ``unit/``: Unit tests for all components
* ``data/``: Test data and templates
    * ``templates/``: Test templates
    * ``workspaces/``: Test workspace configs

Example Code
~~~~~~~~~~
Examples demonstrate common use cases:

* ``templates/``: Example task templates
* ``workspaces/``: Example workspace setups

Template Organization
------------------

Test Templates
~~~~~~~~~~~~
Located in ``tests/data/templates/``:

* Organized by purpose (hello, basic, errors)
* Minimal complexity for testing
* Quick execution time

Example Templates
~~~~~~~~~~~~~~
Located in ``examples/templates/``:

* Well-documented for users
* Demonstrate best practices
* Include common use cases

Development Guidelines
-------------------

Testing Strategy
~~~~~~~~~~~~~
* Unit tests for all components
* Integration tests for workflows
* Test data separated from test logic
* Template-based testing for task execution

Documentation Strategy
~~~~~~~~~~~~~~~~~~
* Architecture documentation in ``docs/architecture/``
* User guides in ``docs/guides/``
* API reference in ``docs/api/``
* Code-level documentation in source files 