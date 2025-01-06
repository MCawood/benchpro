#include "matrix_ops.h"
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <sys/time.h>
#include <string.h>
#include <math.h>

// Create a new matrix
Matrix* matrix_create(size_t rows, size_t cols) {
    Matrix* mat = (Matrix*)malloc(sizeof(Matrix));
    mat->rows = rows;
    mat->cols = cols;
    mat->data = (double*)calloc(rows * cols, sizeof(double));
    return mat;
}

// Free matrix memory
void matrix_free(Matrix* mat) {
    if (mat) {
        free(mat->data);
        free(mat);
    }
}

// Initialize matrix with random values
void matrix_init_random(Matrix* mat) {
    for (size_t i = 0; i < mat->rows * mat->cols; i++) {
        mat->data[i] = (double)rand() / RAND_MAX;
    }
}

// Print matrix (for small matrices or debugging)
void matrix_print(const Matrix* mat) {
    for (size_t i = 0; i < mat->rows; i++) {
        for (size_t j = 0; j < mat->cols; j++) {
            printf("%8.2f ", mat->data[i * mat->cols + j]);
        }
        printf("\n");
    }
}

// Standard matrix multiplication
void matrix_multiply_standard(const Matrix* a, const Matrix* b, Matrix* result) {
    for (size_t i = 0; i < a->rows; i++) {
        for (size_t j = 0; j < b->cols; j++) {
            double sum = 0.0;
            for (size_t k = 0; k < a->cols; k++) {
                sum += a->data[i * a->cols + k] * b->data[k * b->cols + j];
            }
            result->data[i * result->cols + j] = sum;
        }
    }
}

// Block matrix multiplication
void matrix_multiply_blocked(const Matrix* a, const Matrix* b, Matrix* result, size_t block_size) {
    for (size_t i = 0; i < a->rows; i += block_size) {
        for (size_t j = 0; j < b->cols; j += block_size) {
            for (size_t k = 0; k < a->cols; k += block_size) {
                // Process block
                for (size_t ii = i; ii < fmin(i + block_size, a->rows); ii++) {
                    for (size_t jj = j; jj < fmin(j + block_size, b->cols); jj++) {
                        double sum = result->data[ii * result->cols + jj];
                        for (size_t kk = k; kk < fmin(k + block_size, a->cols); kk++) {
                            sum += a->data[ii * a->cols + kk] * b->data[kk * b->cols + jj];
                        }
                        result->data[ii * result->cols + jj] = sum;
                    }
                }
            }
        }
    }
}

// Helper function for Strassen algorithm
static void matrix_add(const Matrix* a, const Matrix* b, Matrix* result) {
    for (size_t i = 0; i < a->rows * a->cols; i++) {
        result->data[i] = a->data[i] + b->data[i];
    }
}

// Helper function for Strassen algorithm
static void matrix_subtract(const Matrix* a, const Matrix* b, Matrix* result) {
    for (size_t i = 0; i < a->rows * a->cols; i++) {
        result->data[i] = a->data[i] - b->data[i];
    }
}

// Strassen matrix multiplication (simplified version)
void matrix_multiply_strassen(const Matrix* a, const Matrix* b, Matrix* result) {
    // For small matrices, use standard multiplication
    if (a->rows <= 64) {
        matrix_multiply_standard(a, b, result);
        return;
    }

    size_t n = a->rows / 2;
    
    // Create submatrices
    Matrix* a11 = matrix_create(n, n);
    Matrix* a12 = matrix_create(n, n);
    Matrix* a21 = matrix_create(n, n);
    Matrix* a22 = matrix_create(n, n);
    Matrix* b11 = matrix_create(n, n);
    Matrix* b12 = matrix_create(n, n);
    Matrix* b21 = matrix_create(n, n);
    Matrix* b22 = matrix_create(n, n);
    
    // Split matrices
    for (size_t i = 0; i < n; i++) {
        for (size_t j = 0; j < n; j++) {
            a11->data[i * n + j] = a->data[i * a->cols + j];
            a12->data[i * n + j] = a->data[i * a->cols + (j + n)];
            a21->data[i * n + j] = a->data[(i + n) * a->cols + j];
            a22->data[i * n + j] = a->data[(i + n) * a->cols + (j + n)];
            
            b11->data[i * n + j] = b->data[i * b->cols + j];
            b12->data[i * n + j] = b->data[i * b->cols + (j + n)];
            b21->data[i * n + j] = b->data[(i + n) * b->cols + j];
            b22->data[i * n + j] = b->data[(i + n) * b->cols + (j + n)];
        }
    }
    
    // Temporary matrices
    Matrix* m1 = matrix_create(n, n);
    Matrix* m2 = matrix_create(n, n);
    Matrix* m3 = matrix_create(n, n);
    Matrix* m4 = matrix_create(n, n);
    Matrix* m5 = matrix_create(n, n);
    Matrix* m6 = matrix_create(n, n);
    Matrix* m7 = matrix_create(n, n);
    Matrix* temp1 = matrix_create(n, n);
    Matrix* temp2 = matrix_create(n, n);
    
    // Strassen's seven multiplications
    matrix_add(a11, a22, temp1);
    matrix_add(b11, b22, temp2);
    matrix_multiply_strassen(temp1, temp2, m1);
    
    matrix_add(a21, a22, temp1);
    matrix_multiply_strassen(temp1, b11, m2);
    
    matrix_subtract(b12, b22, temp1);
    matrix_multiply_strassen(a11, temp1, m3);
    
    matrix_subtract(b21, b11, temp1);
    matrix_multiply_strassen(a22, temp1, m4);
    
    matrix_add(a11, a12, temp1);
    matrix_multiply_strassen(temp1, b22, m5);
    
    matrix_subtract(a21, a11, temp1);
    matrix_add(b11, b12, temp2);
    matrix_multiply_strassen(temp1, temp2, m6);
    
    matrix_subtract(a12, a22, temp1);
    matrix_add(b21, b22, temp2);
    matrix_multiply_strassen(temp1, temp2, m7);
    
    // Calculate result quadrants
    matrix_add(m1, m4, temp1);
    matrix_subtract(temp1, m5, temp2);
    matrix_add(temp2, m7, temp1);  // C11
    
    matrix_add(m3, m5, temp2);     // C12
    
    matrix_add(m2, m4, temp1);     // C21
    
    matrix_add(m1, m3, temp2);
    matrix_subtract(temp2, m2, temp1);
    matrix_add(temp1, m6, temp2);  // C22
    
    // Combine results
    for (size_t i = 0; i < n; i++) {
        for (size_t j = 0; j < n; j++) {
            result->data[i * result->cols + j] = temp1->data[i * n + j];
            result->data[i * result->cols + (j + n)] = temp2->data[i * n + j];
            result->data[(i + n) * result->cols + j] = temp1->data[i * n + j];
            result->data[(i + n) * result->cols + (j + n)] = temp2->data[i * n + j];
        }
    }
    
    // Free temporary matrices
    matrix_free(a11); matrix_free(a12); matrix_free(a21); matrix_free(a22);
    matrix_free(b11); matrix_free(b12); matrix_free(b21); matrix_free(b22);
    matrix_free(m1); matrix_free(m2); matrix_free(m3); matrix_free(m4);
    matrix_free(m5); matrix_free(m6); matrix_free(m7);
    matrix_free(temp1); matrix_free(temp2);
}

// Get current time in seconds
double get_time(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

// Print performance metrics
void print_performance(const char* algorithm, double time, size_t matrix_size) {
    double flops = 2.0 * pow(matrix_size, 3);  // Multiply-add for each element
    double gflops = (flops / time) / 1e9;
    printf("Algorithm: %s\n", algorithm);
    printf("Matrix size: %zux%zu\n", matrix_size, matrix_size);
    printf("Time: %.3f seconds\n", time);
    printf("Performance: %.2f GFLOPS\n\n", gflops);
} 