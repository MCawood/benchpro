# Task Interface Restructure

## Current Understanding
- The codebase currently exposes a low-level `task` CLI interface that allows direct task creation and execution
- Tasks are actually meant to be an internal implementation detail, used by higher-level operations
- There are two main types of tasks:
  1. Build tasks (persistent) - produce artifacts needed for subsequent operations
  2. Benchmark tasks (ephemeral) - run once for performance measurement

## Planned Changes
1. Make the task interface internal only
2. Expose only two main CLI commands:
   - `benchpro build` - for persistent build operations
   - `benchpro bench` - for ephemeral benchmark operations
3. Both commands would use tasks underneath but abstract this from users

## Implementation Notes
- The `BuildOrchestrator` already follows this pattern, using tasks internally
- Need to create a similar `BenchmarkOrchestrator` for benchmark operations
- Need to remove or make internal the current `task` CLI commands
- Should maintain backwards compatibility for any existing scripts

## Dependencies
- Get current test suite passing first
- Document intended architecture
- Create migration plan for existing users

## Questions to Address
- How to handle custom tasks that don't fit build/benchmark pattern?
- How to expose task status/control without exposing task interface?
- What level of task customization should be allowed through build/bench commands? 