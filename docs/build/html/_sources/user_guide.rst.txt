User Guide
==========

Introduction
------------
BenchPRO-NG allows you to define, build, and run benchmarks deterministically.

Workflows
---------

1. **Ad-hoc Tasks**: Use ``bp task run`` for quick experiments.
2. **Application Building**: Use ``bp build run`` to compile software from source.
3. **Benchmark Suites**: Use ``bp suite run`` to execute complex parameter sweeps.

Configuration
-------------
BenchPRO uses a layered configuration system. You can define defaults in ``~/.config/benchpro/config.yaml`` or the project-local ``.benchpro/config.yaml``.
