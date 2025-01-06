#ifndef MATRIX_OPS_H
#define MATRIX_OPS_H

#include <stddef.h>

// Matrix structure
typedef struct {
    size_t rows;
    size_t cols;
    double* data;
} Matrix;

// Matrix operations
Matrix* matrix_create(size_t rows, size_t cols);
void matrix_free(Matrix* mat);
void matrix_init_random(Matrix* mat);
void matrix_print(const Matrix* mat);

// Matrix multiplication algorithms
void matrix_multiply_standard(const Matrix* a, const Matrix* b, Matrix* result);
void matrix_multiply_blocked(const Matrix* a, const Matrix* b, Matrix* result, size_t block_size);
void matrix_multiply_strassen(const Matrix* a, const Matrix* b, Matrix* result);

// Performance measurement
double get_time(void);
void print_performance(const char* algorithm, double time, size_t matrix_size);

#endif // MATRIX_OPS_H 