#include <iostream>
#include <random>
#include <omp.h>
#include <cstdlib>

int main() {
    long long num_points = std::atoll(std::getenv("NUM_POINTS") ? std::getenv("NUM_POINTS") : "1000000");
    int num_threads = std::atoi(std::getenv("NUM_THREADS") ? std::getenv("NUM_THREADS") : "1");
    
    omp_set_num_threads(num_threads);
    
    long long points_inside = 0;
    
    #pragma omp parallel reduction(+:points_inside)
    {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<> dis(-1.0, 1.0);
        
        #pragma omp for
        for (long long i = 0; i < num_points; i++) {
            double x = dis(gen);
            double y = dis(gen);
            if (x*x + y*y <= 1.0) {
                points_inside++;
            }
        }
    }
    
    double pi = 4.0 * points_inside / num_points;
    std::cout << "Estimated π = " << pi << std::endl;
    std::cout << "Points used: " << num_points << std::endl;
    std::cout << "Threads used: " << num_threads << std::endl;
    
    return 0;
} 