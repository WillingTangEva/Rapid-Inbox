cmake_minimum_required(VERSION 3.25)
project(rapid_inbox_ingestd LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(SQLite3 REQUIRED)
find_package(OpenSSL REQUIRED)

set(INGESTD_SOURCES
    src/main.cpp
)

add_executable(rapid-inbox-ingestd ${INGESTD_SOURCES})
target_compile_options(rapid-inbox-ingestd PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(rapid-inbox-ingestd PRIVATE SQLite::SQLite3 OpenSSL::Crypto)

add_executable(ingestd_tests tests/test_main.cpp)
target_compile_options(ingestd_tests PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(ingestd_tests PRIVATE SQLite::SQLite3 OpenSSL::Crypto)
target_compile_definitions(ingestd_tests PRIVATE RAPID_INBOX_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/../..")

enable_testing()
add_test(NAME ingestd_tests COMMAND ingestd_tests)
