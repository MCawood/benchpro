#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int main(int argc, char *argv[]) {
    long long iterations = 1000000;
    if (argc > 1) {
        iterations = atoll(argv[1]);
    }
    
    double pi = 0.0;
    for (long long i = 0; i < iterations; i++) {
        pi += pow(-1, i) / (2 * i + 1);
    }
    pi *= 4;
    
    printf("Pi approximation after %lld iterations: %.15f\n", iterations, pi);
    return 0;
}

