Up to Five Follow-Up Questions

1. Task/Job Relationship

How does a Task progress from one state to another? Is there a central “state machine” approach or do services manually update state fields?

2. Future HPC Executor Adapters

What is the plan for a dedicated SlurmExecutor (or other schedulers)? Will each HPC system be its own adapter, or do you foresee a generic HPC adapter with system-specific configuration?

3. JobResources Validation

How do we validate HPC resource fields (e.g., memory, cores, nodes) beyond simple type checks? Are we ensuring realistic ranges or verifying a user-supplied HPC partition can accommodate them?

4. DatabaseService vs. Ports

Are there discussions about refactoring DatabaseService into a port + adapter model for consistent architecture? Or is SQLite enough of a stopgap that we’ll refactor it later if needed?

5. Handling Complex HPC Workflows

If a Job has multiple Tasks that depend on each other (e.g., build → test → benchmark), do we plan to manage dependencies within the domain, or will the HPC scheduler handle that externally?
