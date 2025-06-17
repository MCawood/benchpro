# BenchPRO Master Development Plan

## 1. Overview

This document serves as the central source of truth for the development of BenchPRO. It outlines the current state of the project, our strategic goals, and the immediate roadmap. The project has recently undergone a significant architectural refactoring, moving from an inheritance-based task system to a more flexible composition-based model. A major outcome of this work is the initial implementation of the **Slurm execution environment**.

Our immediate goal is to **validate, document, and extend** this new functionality.

## 2. Current Status

- **Task Composition Architecture**: Implemented and available via the `--use-composition` flag. This is the new standard for execution.
- **Slurm Executor**: A `SlurmScriptGenerator` and `SlurmExecutionComponent` have been implemented. This allows BenchPRO to generate and submit jobs to a Slurm scheduler.
- **Local Executor**: The legacy local executor remains functional.
- **Architectural Vision**: There is a clear, documented vision for improving the testability and flexibility of the codebase by refactoring core components like `ConfigManager` and `UserDirManager`. The status of these refactorings is yet to be confirmed.
- **Documentation**: The development and planning documents in the `dev/` directory are currently disorganized. They contain a mix of completed, in-progress, and outdated plans.

---

## 3. Development Roadmap

Our development is structured into the following phases.

### Phase 1: Validation and Documentation (Current Focus)

The top priority is to ensure the recently implemented Slurm functionality is robust, well-understood, and ready for use.

- **[ ] Action Item: End-to-End Validation**
    - Create a simple "hello-slurm" benchmark profile.
    - Execute it on a test Slurm environment to confirm end-to-end functionality.
    - Review and run the existing test suite (`pytest`) to ensure all tests are passing.

- **[ ] Action Item: Create User Documentation**
    - Write a guide for users on how to configure BenchPRO to use the Slurm scheduler.
    - Document the required configuration fields (e.g., in `system.yml` or a profile).
    - Provide an example of a benchmark profile that runs via Slurm.

- **[ ] Action Item: Consolidate Development Docs**
    - Reorganize the `dev/` directory to separate active plans from reference material and archives.
    - This `master_plan.md` will be the single source of truth for the development roadmap.

- **[ ] Action Item: Assess Other Refactorings**
    - Investigate whether the high-priority refactoring for `ConfigManager` and `UserDirManager` (as outlined in `dev/archive/PRIORITIZED_IMPROVEMENTS.md`) has been completed.
    - Update this plan with the findings.

### Phase 2: Enhancing Scheduler Support

Once the existing implementation is validated, we will extend its capabilities based on the "Future Enhancements" outlined in the original plan.

- **[ ] Epic: Advanced Slurm Features**
    - **[ ] Story:** Implement support for array jobs (`sbatch --array`).
    - **[ ] Story:** Implement support for job dependencies (`sbatch --dependency`).
    - **[ ] Story:** Allow for more flexible customization of Slurm `#SBATCH` directives from the benchmark profile.

- **[ ] Epic: Add New Schedulers**
    - **[ ] Story:** Implement a `PBS/Torque` execution component.
    - **[ ] Story:** Implement an `LSF` execution component.

### Phase 3: Codebase Modernization

- **[ ] Epic: Deprecate Legacy Architecture**
    - **[ ] Story:** Create a migration guide for any users of the old inheritance-based task system.
    - **[ ] Story:** Plan the removal of the old architecture to simplify the codebase.
    - **[ ] Story:** Make the composition-based architecture the default (remove the `--use-composition` flag).

---

## 4. Key Architectural Principles

As we continue development, we will adhere to the principles outlined in the architectural assessments:
- **Composition over Inheritance**: New functionality should be added via composable components.
- **Dependency Injection**: Avoid singletons; components should receive their dependencies.
- **Testability**: All new code must be accompanied by unit and integration tests. Test-specific code paths in production code are forbidden. 