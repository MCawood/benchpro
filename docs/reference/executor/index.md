# Executor Reference

The executor module is responsible for task execution in BenchPRO, handling both application builds and benchmark runs.

## Overview

The executor module defines:

1. **Task Classes**: Base classes for applications and benchmarks
2. **Component Interfaces**: Abstractions for task behaviors
3. **Execution Systems**: Local and Slurm-based job execution

## Key Components

- [Task Components](components.md): Component interfaces for the composition-based task architecture
- [Task Composition](task_composition.md): Composition-based task architecture
- Executors: Classes for local and scheduler (Slurm) execution
- Task Factories: Classes for creating and configuring tasks
- Scheduler Integration: Support for job schedulers like Slurm

## Architecture

The executor system now uses a composition-based architecture where tasks are composed of interchangeable components:

1. **ConfigComponent**: Manages task configuration
2. **ValidationComponent**: Validates configuration
3. **ScriptGenerationComponent**: Generates execution scripts
4. **ExecutionComponent**: Executes scripts and monitors jobs

This architecture improves:
- **Flexibility**: Components can be swapped independently
- **Testability**: Components can be tested in isolation
- **Extensibility**: New components can be added easily
- **Reusability**: Components can be shared across task types

## Execution Modes

BenchPRO supports multiple execution modes:

### Local Execution

Local execution runs scripts directly on the current system using subprocess. This is useful for:
- Development and testing
- Simple tasks that don't require specialized resources
- Systems without a job scheduler

### Slurm Execution

Slurm execution submits jobs to a Slurm scheduler. This is useful for:
- HPC environments with Slurm
- Jobs requiring specific resource allocations
- Parallel and distributed workloads

The execution mode can be specified in the configuration or at runtime, and both modes use the same task templates 