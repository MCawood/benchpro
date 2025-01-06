Architecture Documentation
========================

This section provides detailed information about BenchPRO's architecture and design decisions.

.. toctree::
   :maxdepth: 2

   project_structure
   domain_models
   executors
   validation

Core Concepts
------------

BenchPRO is built around several key architectural concepts:

1. **Domain-Driven Design**: The architecture is organized around business concepts and domain logic.
2. **Clean Architecture**: Clear separation between domain logic and technical implementations.
3. **Ports and Adapters**: Flexible integration with different execution environments.
4. **Asynchronous Execution**: Non-blocking operations for improved performance.

Layer Organization
----------------

The codebase is organized into the following layers:

Domain Layer (``benchpro.core.domain``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Contains the core business logic and entities:

* Task and Job models
* State management
* Resource specifications
* Domain events and validation rules

Infrastructure Layer (``benchpro.core.infrastructure``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implements technical concerns:

* Local executor implementation
* Resource monitoring
* Process management
* File system operations

Ports Layer (``benchpro.core.ports``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines interfaces and protocols:

* Executor interface
* Resource management protocols
* Error handling contracts

Services Layer (``benchpro.core.services``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implements application use cases:

* Job submission and management
* Resource allocation
* Task scheduling

Design Principles
---------------

1. **Separation of Concerns**: Each component has a single, well-defined responsibility.
2. **Interface Segregation**: Clean interfaces for different types of operations.
3. **Dependency Inversion**: High-level modules don't depend on low-level implementations.
4. **Single Responsibility**: Each class and module has one reason to change. 