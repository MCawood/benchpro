-- some_app 1.0 module file created by BenchPro
-- Created on 2025-06-18 09:35:22

local name = "some_app"
local version = "1.0"

-- Description
whatis("Name: some_app")
whatis("Version: 1.0")
whatis("Description: Application built by BenchPro")

-- Load dependencies


-- Add application binary directory to PATH
prepend_path("PATH", "/bin")

-- Set environment variables
setenv("BP_SOME_APP_DIR", "/Users/mcawood/dev/benchpro_2.0/dummy")
