from benchpro.core.planner import Planner

def test_expand_matrix_basic():
    matrix = {
        "nodes": [1, 2],
        "ranks_per_node": [4]
    }
    base_res = {"threads": 1, "gpus": 0}
    
    tasks = Planner.expand_matrix("test_suite", matrix, base_res)
    
    assert len(tasks) == 2
    assert tasks[0].resources.nodes == 1
    assert tasks[1].resources.nodes == 2
    assert tasks[0].resources.ranks_per_node == 4

def test_expand_matrix_full_product():
    matrix = {
        "nodes": [1, 2],
        "ranks_per_node": [1, 2],
        "threads": [1],
        "gpus": [0]
    }
    base_res = {}
    
    tasks = Planner.expand_matrix("test_suite", matrix, base_res)
    # 2 nodes * 2 ranks * 1 thread * 1 gpu = 4 tasks
    assert len(tasks) == 4

def test_expand_matrix_params():
    matrix = {
        "nodes": [1],
        "params": {
            "p1": ["a", "b"],
            "p2": [10]
        }
    }
    base_res = {"ranks_per_node": 1, "threads": 1, "gpus": 0}
    
    tasks = Planner.expand_matrix("test_suite", matrix, base_res)
    # 1 node * 2 p1 * 1 p2 = 2 tasks
    assert len(tasks) == 2
    assert tasks[0].parameters["p1"] == "a"
    assert tasks[0].parameters["p2"] == 10
    assert tasks[1].parameters["p1"] == "b"
