-- hello_world_app 1.0 module file created by BenchPro
-- Created on 2025-06-18 09:35:22

local name = "hello_world_app"
local version = "1.0"

-- Description
whatis("Name: hello_world_app")
whatis("Version: 1.0")
whatis("Description: Application built by BenchPro")

-- Load dependencies


-- Add application binary directory to PATH
prepend_path("PATH", "/private/var/folders/r4/c2kvh3zs7230vndy5xy0rkg40000gp/T/pytest-of-mcawood/pytest-69/test_benchmark_execution_passe0/outputs/application")

-- Set environment variables
setenv("BP_HELLO_WORLD_APP_DIR", "/Users/mcawood/dev/benchpro_2.0/dummy")
