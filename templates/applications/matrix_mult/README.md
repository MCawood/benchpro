# Matrix Multiplication Benchmark

This benchmark implements and compares different matrix multiplication algorithms to evaluate CPU performance, cache utilization, and memory bandwidth.

## Algorithms

1. **Standard Multiplication**
   - Basic triple-nested loop implementation
   - O(n³) time complexity
   - Poor cache utilization
   - Baseline for comparison

2. **Blocked Multiplication**
   - Cache-friendly implementation using blocks
   - O(n³) time complexity but better cache performance
   - Configurable block size for optimization
   - Best for most practical cases

3. **Strassen's Algorithm**
   - Recursive divide-and-conquer approach
   - O(n^2.807) theoretical time complexity
   - Higher memory usage
   - Better for very large matrices

## Building

```bash
# Build with GCC
gcc -O3 -fopenmp matrix_mult.c matrix_ops.c -o bin/matrix_mult -lm

# Build with Intel compiler
icc -O3 -qopenmp matrix_mult.c matrix_ops.c -o bin/matrix_mult -lm
```

## Configuration

Set the following environment variables to control the benchmark:

- `MATRIX_SIZE`: Size of square matrices (default: 1024)
- `ALGORITHM`: Multiplication algorithm [standard, blocked, strassen] (default: standard)
- `BLOCK_SIZE`: Block size for blocked algorithm (default: 32)
- `NUM_THREADS`: Number of OpenMP threads (default: 1)

## Example Usage

```bash
# Run standard algorithm with default settings
./matrix_mult

# Run blocked algorithm with custom settings
export MATRIX_SIZE=2048
export ALGORITHM=blocked
export BLOCK_SIZE=64
export NUM_THREADS=4
./matrix_mult

# Run Strassen's algorithm
export ALGORITHM=strassen
export MATRIX_SIZE=4096
./matrix_mult
```

## Performance Metrics

The benchmark reports:
- Execution time in seconds
- Performance in GFLOPS (billion floating-point operations per second)
- Matrix dimensions and algorithm used

## Results Format

Results are output in JSON format containing:
- Algorithm name
- Matrix size
- Block size (if applicable)
- Number of threads used
- Execution time
- GFLOPS achieved
- Memory bandwidth utilization

## Optimization Tips

1. **Block Size Selection**
   - Choose block size based on cache size
   - Typical values: 32-64 for L1 cache, 128-256 for L2 cache
   - Experiment to find optimal size for your system

2. **Thread Count**
   - Start with number of physical cores
   - Consider NUMA effects on multi-socket systems
   - Test with and without hyperthreading

3. **Algorithm Selection**
   - Standard: Good for small matrices (<512x512)
   - Blocked: Best for medium to large matrices
   - Strassen: May help for very large matrices (>4096x4096)

## References

1. Goto, K., & van de Geijn, R. A. (2008). Anatomy of high-performance matrix multiplication. ACM Transactions on Mathematical Software.
2. Strassen, V. (1969). Gaussian elimination is not optimal. Numerische Mathematik.
3. Intel Math Kernel Library documentation 