import itertools
from typing import List, Dict, Any
from benchpro.core.domain import Task, ResourceRequest, TaskStatus, Build, MetricDefinition

class Planner:
    @staticmethod
    def expand_matrix(suite_id: str, matrix: Dict[str, List[Any]], base_resources: Dict[str, Any], command_template: str = None, requirements: Dict[str, str] = None, metrics: List[Dict[str, str]] = None, template: str = None) -> List["Benchmark"]:
        """
        Expand a matrix of parameters into a list of Tasks.
        Follows the expansion order: nodes -> ranks_per_node -> threads -> gpus -> named_params
        """
        from benchpro.core.templating import TemplateEngine
        
        # Extract dimensions with defaults if missing
        nodes = matrix.get("nodes", [1])
        ranks = matrix.get("ranks_per_node", [1])
        threads = matrix.get("threads", [1])
        gpus = matrix.get("gpus", [0])
        
        # Extract arbitrary params
        params = matrix.get("params", {})
        param_keys = sorted(params.keys())
        param_values = [params[k] for k in param_keys]
        
        # Parse metrics
        metric_defs = []
        if metrics:
            for m in metrics:
                metric_defs.append(MetricDefinition(**m))
        
        tasks = []
        task_idx = 0
        
        # Cartesian product
        # Order: nodes, ranks, threads, gpus, *params
        for n in nodes:
            for r in ranks:
                for t in threads:
                    for g in gpus:
                        # For params, we need another product if there are any
                        if param_values:
                            param_product = itertools.product(*param_values)
                        else:
                            param_product = [()]
                            
                        for p_vals in param_product:
                            # Construct task
                            task_id = f"{suite_id}_task_{task_idx}"
                            
                            # Build param dict
                            current_params = dict(zip(param_keys, p_vals))
                            
                            # Build resources
                            # Start with base resources
                            res_args = base_resources.copy()
                            # Override with matrix values
                            res_args.update({
                                "nodes": n,
                                "ranks_per_node": r,
                                "threads": t,
                                "gpus": g
                            })
                            
                            res = ResourceRequest(**res_args)
                            
                            # Resolve build if requirements provided
                            activation_cmd = ""
                            if requirements:
                                from benchpro.core.resolver import Resolver
                                from benchpro.core.results import ResultStore
                                
                                store = ResultStore()
                                builds = [Build(**b) for b in store.get_builds()]
                                resolver = Resolver(builds)
                                
                                build = resolver.resolve(
                                    code=requirements.get("code"),
                                    version=requirements.get("version"),
                                    system=requirements.get("system"),
                                    build_label=requirements.get("build_label")
                                )
                                
                                if build:
                                    activation_cmd = f"{build.activation_script} && "
                                    # Check for active build job
                                    if build.status in [TaskStatus.PENDING, TaskStatus.RUNNING] and build.job_id:
                                        scheduler_deps = [str(build.job_id)]
                                    else:
                                        scheduler_deps = []
                                else:
                                    # TODO: Handle missing build (fail or warn)
                                    # For now, just warn in command
                                    activation_cmd = "echo 'WARNING: Build not found' && "

                            # Generate command
                            if command_template:
                                # Create context for templating
                                context = {
                                    "task_id": task_id,
                                    "nodes": n,
                                    "ranks_per_node": r,
                                    "threads": t,
                                    "gpus": g,
                                    **current_params
                                }
                                engine = TemplateEngine(context)
                                command = activation_cmd + engine.render(command_template)
                            else:
                                command = f"{activation_cmd}echo 'Running {task_id}'"

                            task = Task(
                                task_id=task_id,
                                suite_id=suite_id,
                                benchmark_id=f"{suite_id}_bench_{task_idx}",
                                parameters=current_params,
                                resources=res,
                                command=command,
                                metrics=metric_defs,
                                scheduler_dependencies=scheduler_deps if 'scheduler_deps' in locals() else [],
                                status=TaskStatus.PENDING
                            )
                            
                            # Create a Benchmark for this task
                            # Default strategy: 1 Task per Benchmark
                            from benchpro.core.domain import Benchmark
                            bench = Benchmark(
                                benchmark_id=f"{suite_id}_bench_{task_idx}",
                                suite_id=suite_id,
                                tasks=[task],
                                template=template
                            )
                            
                            tasks.append(bench)
                            task_idx += 1
                            
        return tasks
