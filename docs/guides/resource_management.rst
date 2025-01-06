Resource Management
==================

This guide explains how to manage computational resources in BenchPRO.

Resource Types
------------

BenchPRO supports the following resource types:

* CPU cores
* Memory
* Wall time
* GPU (optional)

Specifying Resources
-----------------

.. code-block:: python

    from benchpro.core.domain import JobResources

    resources = JobResources(
        cores=4,
        memory="8G",
        walltime=3600,
        gpu=False
    )

Memory Formats
------------

Memory can be specified in various formats:

* Bytes: "1000000"
* Kilobytes: "1000K"
* Megabytes: "100M"
* Gigabytes: "8G"
* Terabytes: "1T"

Resource Validation
----------------

Resources are validated to ensure:

1. Memory format is correct
2. Core count is positive integer
3. Wall time is positive integer
4. GPU flag is boolean

Best Practices
------------

1. Request only needed resources
2. Monitor resource usage
3. Clean up unused resources
4. Set appropriate timeouts
5. Handle resource allocation failures 