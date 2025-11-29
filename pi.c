#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int main(int argc, char *argv[]) {
    long long n = 100000000;
    if (argc > 1) {
        n = atoll(argv[1]);
    }
    
    double h = 1.0 / (double)n;
    double sum = 0.0;
    
    for (long long i = 1; i <= n; i++) {
        double x = h * ((double)i - 0.5);
        sum += 4.0 / (1.0 + x*x);
    }
    
    double pi = h * sum;
    printf("Pi is approximately %.16f\n", pi);
    return 0;
}
