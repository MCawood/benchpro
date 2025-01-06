#include "matrix_ops.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <omp.h>

int main(int argc, char *argv[]) {
    // Get parameters from environment variables
    const char* size_str = getenv("MATRIX_SIZE");
    const char* algorithm = getenv("ALGORITHM");
    const char* block_size_str = getenv("BLOCK_SIZE");
    const char* num_threads_str = getenv("NUM_THREADS");

    // Set defaults if not provided
    size_t matrix_size = size_str ? atoi(size_str) : 1024;
    size_t block_size = block_size_str ? atoi(block_size_str) : 32;
    int num_threads = num_threads_str ? atoi(num_threads_str) : 1;

    // Set number of threads
    omp_set_num_threads(num_threads);

    // Initialize random seed
    srand(time(NULL));

    // Create matrices
    Matrix* a = matrix_create(matrix_size, matrix_size);
    Matrix* b = matrix_create(matrix_size, matrix_size);
    Matrix* c = matrix_create(matrix_size, matrix_size);

    // Initialize matrices with random values
    matrix_init_random(a);
    matrix_init_random(b);

    // Perform multiplication based on selected algorithm
    double start_time = get_time();

    if (!algorithm || strcmp(algorithm, "standard") == 0) {
        matrix_multiply_standard(a, b, c);
        print_performance("Standard", get_time() - start_time, matrix_size);
    }
    else if (strcmp(algorithm, "blocked") == 0) {
        matrix_multiply_blocked(a, b, c, block_size);
        print_performance("Blocked", get_time() - start_time, matrix_size);
    }
    else if (strcmp(algorithm, "strassen") == 0) {
        matrix_multiply_strassen(a, b, c);
        print_performance("Strassen", get_time() - start_time, matrix_size);
    }
    else {
        fprintf(stderr, "Unknown algorithm: %s\n", algorithm);
        fprintf(stderr, "Supported algorithms: standard, blocked, strassen\n");
        return 1;
    }

    // Clean up
    matrix_free(a);
    matrix_free(b);
    matrix_free(c);

    return 0;
} 