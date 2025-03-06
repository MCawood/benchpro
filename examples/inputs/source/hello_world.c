#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

int main() {
    printf("Hello, World!\n");
    
    // Simulate some work
    printf("Running benchmark...\n");
    
    // Simulate a random runtime between 0.5 and 2.5 seconds
    srand(time(NULL));
    double runtime = 0.5 + ((double)rand() / RAND_MAX) * 2.0;
    
    // Sleep for the runtime
    sleep((int)runtime);
    usleep((int)((runtime - (int)runtime) * 1000000));
    
    // Print the benchmark result
    printf("Result: %.3f seconds\n", runtime);
    
    return 0;
} 