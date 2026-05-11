#include <cstdlib>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace test {
inline void check(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}
}

void test_config_defaults();
void test_config_dotenv_and_environment_override();
void test_time_and_path_parts();
void test_ids_have_expected_prefixes();
void test_sha256_known_digest();
void test_storage_paths_match_python_layout();
void test_json_escape();

int main() {
    try {
        test_config_defaults();
        test_config_dotenv_and_environment_override();
        test_time_and_path_parts();
        test_ids_have_expected_prefixes();
        test_sha256_known_digest();
        test_storage_paths_match_python_layout();
        test_json_escape();
        std::cout << "ingestd_tests ok\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& exc) {
        std::cerr << "ingestd_tests failed: " << exc.what() << "\n";
        return EXIT_FAILURE;
    }
}
