#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    const char *message = getenv("MESSAGE");
    if (!message) {
        message = "Hello, World!";
    }
    
    int repeat_count = 1;
    const char *repeat_str = getenv("REPEAT_COUNT");
    if (repeat_str) {
        repeat_count = atoi(repeat_str);
    }
    
    for (int i = 0; i < repeat_count; i++) {
        printf("%s\n", message);
        sleep(1);  // Add a delay to simulate work
    }
    
    return 0;
} 