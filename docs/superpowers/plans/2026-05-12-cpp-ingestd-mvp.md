# C++ Ingestd MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-shaped C++ `rapid-inbox-ingestd` that accepts SMTP mail into memory, drains normal shutdowns, and batch-writes existing Rapid Inbox SQLite/storage records while the Python HTTP app remains unchanged.

**Architecture:** Add a C++20 service under `cpp/ingestd` with small modules for config, IDs, storage paths, domain matching, SQLite access, queueing, batch writing, SMTP session parsing, and the TCP server. Phase 1 writes `parse_status='pending'` rows and raw/manifest artifacts; existing Python runtime continues parsing and serving UI/API. Parser migration is intentionally outside this MVP plan and should get its own plan after ingest throughput is proven.

**Tech Stack:** C++20, CMake, SQLite3 C API, OpenSSL SHA256, POSIX sockets/signals, existing Python pytest suite for black-box integration.

---

## Scope Check

This plan implements only Phase 1 from `docs/superpowers/specs/2026-05-12-cpp-ingestd-hybrid-design.md`: C++ SMTP ingest, domain cache, in-memory queue, normal drain, storage artifacts, SQLite pending records, documentation, and verification. C++ MIME parser workers, attachment extraction, and C++ verification-code extraction are separate follow-up work.

## File Structure

- Create: `cpp/ingestd/CMakeLists.txt` - C++ build, test targets, dependencies.
- Create: `cpp/ingestd/README.md` - local build/run commands and MVP semantics.
- Create: `cpp/ingestd/src/config.h`
- Create: `cpp/ingestd/src/config.cpp` - `.env` and environment variable loading.
- Create: `cpp/ingestd/src/time_utils.h`
- Create: `cpp/ingestd/src/time_utils.cpp` - UTC timestamps and date path parts.
- Create: `cpp/ingestd/src/id.h`
- Create: `cpp/ingestd/src/id.cpp` - `msg_`, `dlv_`, `smtp_` IDs.
- Create: `cpp/ingestd/src/sha256.h`
- Create: `cpp/ingestd/src/sha256.cpp` - raw message digest.
- Create: `cpp/ingestd/src/storage_path.h`
- Create: `cpp/ingestd/src/storage_path.cpp` - Rapid Inbox relative paths and safe filenames.
- Create: `cpp/ingestd/src/json_util.h`
- Create: `cpp/ingestd/src/json_util.cpp` - tiny JSON string escaping for manifests and logs.
- Create: `cpp/ingestd/src/domain_matcher.h`
- Create: `cpp/ingestd/src/domain_matcher.cpp` - C++ equivalent of Python domain matching.
- Create: `cpp/ingestd/src/sqlite_db.h`
- Create: `cpp/ingestd/src/sqlite_db.cpp` - RAII SQLite wrapper and statements.
- Create: `cpp/ingestd/src/domain_cache.h`
- Create: `cpp/ingestd/src/domain_cache.cpp` - load active domains from existing SQLite.
- Create: `cpp/ingestd/src/mail_job.h` - shared ingest job structs.
- Create: `cpp/ingestd/src/mail_queue.h`
- Create: `cpp/ingestd/src/mail_queue.cpp` - bounded queue and close/drain behavior.
- Create: `cpp/ingestd/src/batch_writer.h`
- Create: `cpp/ingestd/src/batch_writer.cpp` - batch storage + SQLite writer.
- Create: `cpp/ingestd/src/smtp_session.h`
- Create: `cpp/ingestd/src/smtp_session.cpp` - command parser and DATA collection.
- Create: `cpp/ingestd/src/smtp_server.h`
- Create: `cpp/ingestd/src/smtp_server.cpp` - listening socket, workers, shutdown.
- Create: `cpp/ingestd/src/main.cpp` - binary entrypoint.
- Create: `cpp/ingestd/tests/test_main.cpp` - test runner helpers.
- Create: `cpp/ingestd/tests/test_config.cpp`
- Create: `cpp/ingestd/tests/test_storage_utils.cpp`
- Create: `cpp/ingestd/tests/test_domain_matcher.cpp`
- Create: `cpp/ingestd/tests/test_domain_cache.cpp`
- Create: `cpp/ingestd/tests/test_mail_queue.cpp`
- Create: `cpp/ingestd/tests/test_batch_writer.cpp`
- Create: `cpp/ingestd/tests/test_smtp_session.cpp`
- Create: `tests/test_cpp_ingestd_integration.py` - black-box SMTP + existing Python runtime compatibility.
- Modify: `.gitignore` - ignore `cpp/ingestd/build*/`.
- Modify: `README.md` - document hybrid deployment and `250` memory-queue semantics.
- Modify: `CHANGELOG.md` - note planned C++ ingestd MVP under Unreleased.

---

### Task 1: C++ Build And Test Harness

**Files:**
- Create: `cpp/ingestd/CMakeLists.txt`
- Create: `cpp/ingestd/src/main.cpp`
- Create: `cpp/ingestd/tests/test_main.cpp`
- Modify: `.gitignore`

- [ ] **Step 1: Write the failing scaffold test**

Create `cpp/ingestd/tests/test_main.cpp`:

```cpp
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

int main() {
    try {
        test::check(true, "test harness must run");
        std::cout << "ingestd_tests ok\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& exc) {
        std::cerr << "ingestd_tests failed: " << exc.what() << "\n";
        return EXIT_FAILURE;
    }
}
```

- [ ] **Step 2: Run build to verify there is no CMake target yet**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
```

Expected: FAIL because `cpp/ingestd/CMakeLists.txt` does not exist.

- [ ] **Step 3: Add minimal CMake and binary entrypoint**

Create `cpp/ingestd/CMakeLists.txt`:

```cmake
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
```

Create `cpp/ingestd/src/main.cpp`:

```cpp
#include <iostream>

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;
    std::cout << "rapid-inbox-ingestd scaffold\n";
    return 0;
}
```

Modify `.gitignore` by adding:

```gitignore
cpp/ingestd/build*/
```

- [ ] **Step 4: Run scaffold verification**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: configure succeeds, build succeeds, `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore cpp/ingestd
git commit -m "feat: 添加 ingestd 构建骨架"
```

---

### Task 2: Configuration Loader

**Files:**
- Create: `cpp/ingestd/src/config.h`
- Create: `cpp/ingestd/src/config.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Modify: `cpp/ingestd/tests/test_main.cpp`
- Create: `cpp/ingestd/tests/test_config.cpp`

- [ ] **Step 1: Write the failing config tests**

Replace `cpp/ingestd/tests/test_main.cpp` with:

```cpp
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

int main() {
    try {
        test_config_defaults();
        test_config_dotenv_and_environment_override();
        std::cout << "ingestd_tests ok\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& exc) {
        std::cerr << "ingestd_tests failed: " << exc.what() << "\n";
        return EXIT_FAILURE;
    }
}
```

Create `cpp/ingestd/tests/test_config.cpp`:

```cpp
#include "../src/config.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>

namespace test {
void check(bool condition, const std::string& message);
}

void test_config_defaults() {
    rapid_inbox::ingestd::Config config =
        rapid_inbox::ingestd::Config::load(std::filesystem::path{RAPID_INBOX_REPO_ROOT});
    test::check(config.host == "127.0.0.1", "default host");
    test::check(config.port == 8000, "default HTTP port mirror");
    test::check(config.smtp_host == "127.0.0.1", "default SMTP host");
    test::check(config.smtp_port == 25, "default SMTP port");
    test::check(config.ingest_batch_max_messages == 250, "default ingest batch size");
    test::check(config.ingest_flush_interval_ms == 250, "default flush interval");
}

void test_config_dotenv_and_environment_override() {
    auto temp_dir = std::filesystem::temp_directory_path() / "rapid-inbox-config-test";
    std::filesystem::create_directories(temp_dir);
    {
        std::ofstream env(temp_dir / ".env");
        env << "SMTP_HOST=0.0.0.0\n";
        env << "SMTP_PORT=2525\n";
        env << "STORAGE_ROOT=custom-storage\n";
        env << "INGEST_BATCH_MAX_MESSAGES=123\n";
    }
    setenv("SMTP_PORT", "2526", 1);
    rapid_inbox::ingestd::Config config = rapid_inbox::ingestd::Config::load(temp_dir);
    unsetenv("SMTP_PORT");
    test::check(config.smtp_host == "0.0.0.0", "dotenv SMTP host");
    test::check(config.smtp_port == 2526, "environment overrides dotenv");
    test::check(config.storage_root == temp_dir / "custom-storage", "relative storage root resolves from base dir");
    test::check(config.database_path == config.storage_root / "app.db", "default database path follows storage root");
    test::check(config.ingest_batch_max_messages == 123, "dotenv batch size");
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: build FAILS with missing `config.h`.

- [ ] **Step 3: Implement config loader**

Create `cpp/ingestd/src/config.h`:

```cpp
#pragma once

#include <filesystem>
#include <string>
#include <unordered_map>

namespace rapid_inbox::ingestd {

struct Config {
    std::filesystem::path base_dir;
    std::filesystem::path storage_root;
    std::filesystem::path database_path;
    std::string host = "127.0.0.1";
    int port = 8000;
    std::string smtp_host = "127.0.0.1";
    int smtp_port = 25;
    int max_message_size_bytes = 52428800;
    int max_recipients_per_message = 20;
    int smtp_idle_timeout_seconds = 30;
    int ingest_queue_max_messages = 10000;
    int ingest_batch_max_messages = 250;
    int ingest_flush_interval_ms = 250;
    int ingest_sqlite_busy_timeout_ms = 5000;
    bool ingest_storage_fsync = false;

    static Config load(const std::filesystem::path& base_dir);
};

std::unordered_map<std::string, std::string> load_dotenv(const std::filesystem::path& dotenv_path);

}
```

Create `cpp/ingestd/src/config.cpp`:

```cpp
#include "config.h"

#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace rapid_inbox::ingestd {
namespace {

std::string trim(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return "";
    }
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string unquote(std::string value) {
    if (value.size() >= 2 && ((value.front() == '"' && value.back() == '"') ||
                              (value.front() == '\'' && value.back() == '\''))) {
        return value.substr(1, value.size() - 2);
    }
    return value;
}

std::string value_for(const std::unordered_map<std::string, std::string>& values,
                      const std::string& key,
                      const std::string& fallback) {
    if (const char* env_value = std::getenv(key.c_str())) {
        return std::string(env_value);
    }
    auto found = values.find(key);
    return found == values.end() ? fallback : found->second;
}

int int_for(const std::unordered_map<std::string, std::string>& values,
            const std::string& key,
            int fallback) {
    const std::string value = value_for(values, key, "");
    if (value.empty()) {
        return fallback;
    }
    return std::stoi(value);
}

bool bool_for(const std::unordered_map<std::string, std::string>& values,
              const std::string& key,
              bool fallback) {
    std::string value = value_for(values, key, "");
    if (value.empty()) {
        return fallback;
    }
    for (char& ch : value) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    return value == "1" || value == "true" || value == "yes" || value == "on";
}

std::filesystem::path resolve_path(const std::string& value,
                                   const std::filesystem::path& fallback,
                                   const std::filesystem::path& base_dir) {
    if (value.empty()) {
        return fallback;
    }
    std::filesystem::path path(value);
    if (path.is_relative()) {
        path = base_dir / path;
    }
    return path.lexically_normal();
}

}

std::unordered_map<std::string, std::string> load_dotenv(const std::filesystem::path& dotenv_path) {
    std::unordered_map<std::string, std::string> values;
    std::ifstream input(dotenv_path);
    std::string line;
    while (std::getline(input, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') {
            continue;
        }
        if (line.rfind("export ", 0) == 0) {
            line = trim(line.substr(7));
        }
        const auto equals = line.find('=');
        if (equals == std::string::npos) {
            continue;
        }
        std::string key = trim(line.substr(0, equals));
        std::string value = unquote(trim(line.substr(equals + 1)));
        if (!key.empty()) {
            values[key] = value;
        }
    }
    return values;
}

Config Config::load(const std::filesystem::path& base) {
    Config config;
    config.base_dir = std::filesystem::absolute(base).lexically_normal();
    const auto dotenv = load_dotenv(config.base_dir / ".env");
    config.host = value_for(dotenv, "HOST", "127.0.0.1");
    config.port = int_for(dotenv, "PORT", 8000);
    config.smtp_host = value_for(dotenv, "SMTP_HOST", "127.0.0.1");
    config.smtp_port = int_for(dotenv, "SMTP_PORT", 25);
    config.max_message_size_bytes = int_for(dotenv, "MAX_MESSAGE_SIZE_BYTES", 52428800);
    config.max_recipients_per_message = int_for(dotenv, "MAX_RECIPIENTS_PER_MESSAGE", 20);
    config.smtp_idle_timeout_seconds = int_for(dotenv, "SMTP_IDLE_TIMEOUT_SECONDS", 30);
    config.ingest_queue_max_messages = int_for(dotenv, "INGEST_QUEUE_MAX_MESSAGES", 10000);
    config.ingest_batch_max_messages = int_for(dotenv, "INGEST_BATCH_MAX_MESSAGES", 250);
    config.ingest_flush_interval_ms = int_for(dotenv, "INGEST_FLUSH_INTERVAL_MS", 250);
    config.ingest_sqlite_busy_timeout_ms = int_for(dotenv, "INGEST_SQLITE_BUSY_TIMEOUT_MS", 5000);
    config.ingest_storage_fsync = bool_for(dotenv, "INGEST_STORAGE_FSYNC", false);

    config.storage_root = resolve_path(value_for(dotenv, "STORAGE_ROOT", ""),
                                       config.base_dir / "storage",
                                       config.base_dir);
    config.database_path = resolve_path(value_for(dotenv, "DATABASE_PATH", ""),
                                        config.storage_root / "app.db",
                                        config.base_dir);
    return config;
}

}
```

Modify `cpp/ingestd/CMakeLists.txt`:

```cmake
set(INGESTD_LIB_SOURCES
    src/config.cpp
)

set(INGESTD_SOURCES
    src/main.cpp
)

add_library(ingestd_core ${INGESTD_LIB_SOURCES})
target_include_directories(ingestd_core PUBLIC src)
target_compile_options(ingestd_core PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(ingestd_core PUBLIC SQLite::SQLite3 OpenSSL::Crypto)

add_executable(rapid-inbox-ingestd ${INGESTD_SOURCES})
target_compile_options(rapid-inbox-ingestd PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(rapid-inbox-ingestd PRIVATE ingestd_core)

add_executable(ingestd_tests
    tests/test_main.cpp
    tests/test_config.cpp
)
target_compile_options(ingestd_tests PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(ingestd_tests PRIVATE ingestd_core)
target_compile_definitions(ingestd_tests PRIVATE RAPID_INBOX_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/../..")
```

Keep the existing `cmake_minimum_required`, `project`, `find_package`, `enable_testing`, and `add_test` lines around this replacement.

- [ ] **Step 4: Run config tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 添加 ingestd 配置加载"
```

---

### Task 3: Time, ID, SHA256, Storage Path Utilities

**Files:**
- Create: `cpp/ingestd/src/time_utils.h`
- Create: `cpp/ingestd/src/time_utils.cpp`
- Create: `cpp/ingestd/src/id.h`
- Create: `cpp/ingestd/src/id.cpp`
- Create: `cpp/ingestd/src/sha256.h`
- Create: `cpp/ingestd/src/sha256.cpp`
- Create: `cpp/ingestd/src/storage_path.h`
- Create: `cpp/ingestd/src/storage_path.cpp`
- Create: `cpp/ingestd/src/json_util.h`
- Create: `cpp/ingestd/src/json_util.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Modify: `cpp/ingestd/tests/test_main.cpp`
- Create: `cpp/ingestd/tests/test_storage_utils.cpp`

- [ ] **Step 1: Write failing utility tests**

Add declarations to `cpp/ingestd/tests/test_main.cpp` and call them before printing success:

```cpp
void test_time_and_path_parts();
void test_ids_have_expected_prefixes();
void test_sha256_known_digest();
void test_storage_paths_match_python_layout();
void test_json_escape();
```

Create `cpp/ingestd/tests/test_storage_utils.cpp`:

```cpp
#include "../src/id.h"
#include "../src/json_util.h"
#include "../src/sha256.h"
#include "../src/storage_path.h"
#include "../src/time_utils.h"

#include <regex>
#include <string>

namespace test {
void check(bool condition, const std::string& message);
}

void test_time_and_path_parts() {
    const std::string now = rapid_inbox::ingestd::utc_now();
    test::check(std::regex_match(now, std::regex(R"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")), "utc_now format");
    auto parts = rapid_inbox::ingestd::path_date_parts("2026-05-12T03:04:05Z");
    test::check(parts.year == "2026", "year part");
    test::check(parts.month == "05", "month part");
    test::check(parts.day == "12", "day part");
}

void test_ids_have_expected_prefixes() {
    const std::string message_id = rapid_inbox::ingestd::make_prefixed_id("msg_");
    const std::string delivery_id = rapid_inbox::ingestd::make_prefixed_id("dlv_");
    test::check(message_id.rfind("msg_", 0) == 0 && message_id.size() == 36, "message id shape");
    test::check(delivery_id.rfind("dlv_", 0) == 0 && delivery_id.size() == 36, "delivery id shape");
    test::check(message_id != rapid_inbox::ingestd::make_prefixed_id("msg_"), "ids vary");
}

void test_sha256_known_digest() {
    const std::string digest = rapid_inbox::ingestd::sha256_hex("abc");
    test::check(digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "sha256 abc");
}

void test_storage_paths_match_python_layout() {
    const std::string message_id = "msg_abc";
    const std::string received_at = "2026-05-12T03:04:05Z";
    test::check(rapid_inbox::ingestd::raw_message_path(message_id, received_at) == "raw/2026/05/12/msg_abc.eml", "raw path");
    test::check(rapid_inbox::ingestd::manifest_path(message_id, received_at) == "manifests/2026/05/12/msg_abc.json", "manifest path");
    test::check(rapid_inbox::ingestd::safe_filename("a/b c?.txt") == "a_b_c_.txt", "safe filename");
}

void test_json_escape() {
    test::check(rapid_inbox::ingestd::json_escape("a\"b\\c\n") == "a\\\"b\\\\c\\n", "json escape");
}
```

- [ ] **Step 2: Run utility tests to verify failure**

Run:

```bash
cmake --build cpp/ingestd/build
```

Expected: build FAILS with missing utility headers.

- [ ] **Step 3: Implement utility modules**

Create `cpp/ingestd/src/time_utils.h`:

```cpp
#pragma once

#include <string>

namespace rapid_inbox::ingestd {

struct DateParts {
    std::string year;
    std::string month;
    std::string day;
};

std::string utc_now();
DateParts path_date_parts(const std::string& timestamp);

}
```

Create `cpp/ingestd/src/time_utils.cpp`:

```cpp
#include "time_utils.h"

#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace rapid_inbox::ingestd {

std::string utc_now() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t time = std::chrono::system_clock::to_time_t(now);
    std::tm utc{};
    gmtime_r(&time, &utc);
    std::ostringstream output;
    output << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
    return output.str();
}

DateParts path_date_parts(const std::string& timestamp) {
    if (timestamp.size() < 10) {
        throw std::invalid_argument("timestamp must be ISO UTC");
    }
    return DateParts{timestamp.substr(0, 4), timestamp.substr(5, 2), timestamp.substr(8, 2)};
}

}
```

Create `cpp/ingestd/src/id.h`:

```cpp
#pragma once

#include <string>

namespace rapid_inbox::ingestd {

std::string make_prefixed_id(const std::string& prefix);

}
```

Create `cpp/ingestd/src/id.cpp`:

```cpp
#include "id.h"

#include <array>
#include <iomanip>
#include <random>
#include <sstream>

namespace rapid_inbox::ingestd {

std::string make_prefixed_id(const std::string& prefix) {
    static thread_local std::random_device device;
    static thread_local std::mt19937_64 generator(device());
    std::uniform_int_distribution<unsigned int> dist(0, 255);
    std::array<unsigned char, 16> bytes{};
    for (auto& byte : bytes) {
        byte = static_cast<unsigned char>(dist(generator));
    }
    std::ostringstream output;
    output << prefix << std::hex << std::setfill('0');
    for (unsigned char byte : bytes) {
        output << std::setw(2) << static_cast<int>(byte);
    }
    return output.str();
}

}
```

Create `cpp/ingestd/src/sha256.h`:

```cpp
#pragma once

#include <string>
#include <string_view>

namespace rapid_inbox::ingestd {

std::string sha256_hex(std::string_view content);

}
```

Create `cpp/ingestd/src/sha256.cpp`:

```cpp
#include "sha256.h"

#include <iomanip>
#include <openssl/sha.h>
#include <sstream>

namespace rapid_inbox::ingestd {

std::string sha256_hex(std::string_view content) {
    unsigned char digest[SHA256_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const unsigned char*>(content.data()), content.size(), digest);
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (unsigned char byte : digest) {
        output << std::setw(2) << static_cast<int>(byte);
    }
    return output.str();
}

}
```

Create `cpp/ingestd/src/storage_path.h`:

```cpp
#pragma once

#include <string>

namespace rapid_inbox::ingestd {

std::string safe_filename(const std::string& filename);
std::string raw_message_path(const std::string& message_id, const std::string& received_at);
std::string manifest_path(const std::string& message_id, const std::string& received_at);

}
```

Create `cpp/ingestd/src/storage_path.cpp`:

```cpp
#include "storage_path.h"

#include "time_utils.h"

#include <cctype>

namespace rapid_inbox::ingestd {

std::string safe_filename(const std::string& filename) {
    std::string output;
    for (unsigned char ch : filename.empty() ? std::string("attachment.bin") : filename) {
        if (std::isalnum(ch) || ch == '.' || ch == '_' || ch == '-') {
            output.push_back(static_cast<char>(ch));
        } else {
            output.push_back('_');
        }
    }
    while (!output.empty() && (output.front() == '.' || output.front() == '_')) {
        output.erase(output.begin());
    }
    while (!output.empty() && (output.back() == '.' || output.back() == '_')) {
        output.pop_back();
    }
    return output.empty() ? "attachment.bin" : output;
}

std::string raw_message_path(const std::string& message_id, const std::string& received_at) {
    const DateParts parts = path_date_parts(received_at);
    return "raw/" + parts.year + "/" + parts.month + "/" + parts.day + "/" + message_id + ".eml";
}

std::string manifest_path(const std::string& message_id, const std::string& received_at) {
    const DateParts parts = path_date_parts(received_at);
    return "manifests/" + parts.year + "/" + parts.month + "/" + parts.day + "/" + message_id + ".json";
}

}
```

Create `cpp/ingestd/src/json_util.h`:

```cpp
#pragma once

#include <string>

namespace rapid_inbox::ingestd {

std::string json_escape(const std::string& value);

}
```

Create `cpp/ingestd/src/json_util.cpp`:

```cpp
#include "json_util.h"

#include <iomanip>
#include <sstream>

namespace rapid_inbox::ingestd {

std::string json_escape(const std::string& value) {
    std::ostringstream output;
    for (unsigned char ch : value) {
        switch (ch) {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (ch < 0x20) {
                    output << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(ch);
                } else {
                    output << static_cast<char>(ch);
                }
        }
    }
    return output.str();
}

}
```

Add these sources to `INGESTD_LIB_SOURCES` in `cpp/ingestd/CMakeLists.txt`:

```cmake
    src/id.cpp
    src/json_util.cpp
    src/sha256.cpp
    src/storage_path.cpp
    src/time_utils.cpp
```

Add `tests/test_storage_utils.cpp` to `ingestd_tests`.

- [ ] **Step 4: Run utility tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 添加 ingestd 存储工具"
```

---

### Task 4: Domain Matcher Parity

**Files:**
- Create: `cpp/ingestd/src/domain_matcher.h`
- Create: `cpp/ingestd/src/domain_matcher.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Modify: `cpp/ingestd/tests/test_main.cpp`
- Create: `cpp/ingestd/tests/test_domain_matcher.cpp`

- [ ] **Step 1: Write failing matcher tests**

Add to `cpp/ingestd/tests/test_main.cpp`:

```cpp
void test_domain_matcher_exact_subdomain_and_longest_suffix();
void test_domain_matcher_plus_and_case_modes();
```

Create `cpp/ingestd/tests/test_domain_matcher.cpp`:

```cpp
#include "../src/domain_matcher.h"

#include <string>
#include <vector>

namespace test {
void check(bool condition, const std::string& message);
}

void test_domain_matcher_exact_subdomain_and_longest_suffix() {
    using namespace rapid_inbox::ingestd;
    DomainMatcher matcher({
        DomainRule{1, "adb.com", true, true, "keep", false},
        DomainRule{2, "x.adb.com", true, true, "keep", false},
        DomainRule{3, "exact-only.test", true, false, "keep", false},
    });
    auto root = matcher.match_address("Code@adb.com");
    test::check(root.has_value(), "root match");
    test::check(root->domain_id == 1, "root domain id");
    test::check(root->address_canonical == "code@adb.com", "root canonical");
    auto longest = matcher.match_address("User@deep.x.adb.com");
    test::check(longest.has_value(), "longest suffix match");
    test::check(longest->domain_id == 2, "longest suffix domain");
    auto rejected = matcher.match_address("a@sub.exact-only.test");
    test::check(!rejected.has_value(), "subdomain disabled");
}

void test_domain_matcher_plus_and_case_modes() {
    using namespace rapid_inbox::ingestd;
    DomainMatcher matcher({
        DomainRule{10, "strip.test", true, true, "strip", false},
        DomainRule{11, "case.test", true, true, "keep", true},
    });
    auto stripped = matcher.match_address("User+tag@strip.test");
    test::check(stripped.has_value(), "plus match");
    test::check(stripped->local_part_canonical == "user", "plus stripped and lower");
    test::check(stripped->address_canonical == "user@strip.test", "plus canonical");
    auto cased = matcher.match_address("User@case.test");
    test::check(cased.has_value(), "case match");
    test::check(cased->local_part_canonical == "User", "case preserved");
}
```

- [ ] **Step 2: Run matcher tests to verify failure**

Run:

```bash
cmake --build cpp/ingestd/build
```

Expected: build FAILS with missing `domain_matcher.h`.

- [ ] **Step 3: Implement matcher**

Create `cpp/ingestd/src/domain_matcher.h`:

```cpp
#pragma once

#include <optional>
#include <string>
#include <vector>

namespace rapid_inbox::ingestd {

struct DomainRule {
    int domain_id;
    std::string root_domain_ascii;
    bool accept_exact;
    bool accept_subdomains;
    std::string plus_addressing_mode;
    bool local_part_case_sensitive;
};

struct DomainMatch {
    int domain_id;
    std::string domain_ascii;
    std::string root_domain_ascii;
    std::string local_part;
    std::string local_part_canonical;
    std::string address_canonical;
};

std::string normalize_domain(std::string domain);

class DomainMatcher {
public:
    explicit DomainMatcher(std::vector<DomainRule> rules);
    std::optional<DomainMatch> match_address(const std::string& address) const;

private:
    std::vector<DomainRule> rules_;
};

}
```

Create `cpp/ingestd/src/domain_matcher.cpp`:

```cpp
#include "domain_matcher.h"

#include <algorithm>
#include <cctype>

namespace rapid_inbox::ingestd {
namespace {

std::string lower_ascii(std::string value) {
    for (char& ch : value) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    return value;
}

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

}

std::string normalize_domain(std::string domain) {
    while (!domain.empty() && domain.back() == '.') {
        domain.pop_back();
    }
    return lower_ascii(domain);
}

DomainMatcher::DomainMatcher(std::vector<DomainRule> rules) : rules_(std::move(rules)) {
    std::sort(rules_.begin(), rules_.end(), [](const DomainRule& left, const DomainRule& right) {
        return normalize_domain(left.root_domain_ascii).size() > normalize_domain(right.root_domain_ascii).size();
    });
}

std::optional<DomainMatch> DomainMatcher::match_address(const std::string& address) const {
    const auto at = address.rfind('@');
    if (at == std::string::npos) {
        return std::nullopt;
    }
    std::string local_part = address.substr(0, at);
    std::string domain = normalize_domain(address.substr(at + 1));
    for (const DomainRule& rule : rules_) {
        const std::string root = normalize_domain(rule.root_domain_ascii);
        const bool exact = domain == root;
        const bool subdomain = ends_with(domain, "." + root);
        if (!exact && !subdomain) {
            continue;
        }
        if (exact && !rule.accept_exact) {
            return std::nullopt;
        }
        if (subdomain && !rule.accept_subdomains) {
            return std::nullopt;
        }
        std::string canonical_local = local_part;
        if (rule.plus_addressing_mode == "strip") {
            const auto plus = canonical_local.find('+');
            if (plus != std::string::npos) {
                canonical_local = canonical_local.substr(0, plus);
            }
        }
        if (!rule.local_part_case_sensitive) {
            canonical_local = lower_ascii(canonical_local);
        }
        return DomainMatch{
            rule.domain_id,
            domain,
            root,
            local_part,
            canonical_local,
            canonical_local + "@" + domain,
        };
    }
    return std::nullopt;
}

}
```

Add `src/domain_matcher.cpp` and `tests/test_domain_matcher.cpp` to `cpp/ingestd/CMakeLists.txt`.

- [ ] **Step 4: Run matcher tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
.venv/bin/pytest tests/test_domain_matching.py -q
```

Expected: C++ tests pass and Python domain matching tests pass.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 对齐 ingestd 域名匹配规则"
```

---

### Task 5: SQLite Wrapper And Domain Cache

**Files:**
- Create: `cpp/ingestd/src/sqlite_db.h`
- Create: `cpp/ingestd/src/sqlite_db.cpp`
- Create: `cpp/ingestd/src/domain_cache.h`
- Create: `cpp/ingestd/src/domain_cache.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Modify: `cpp/ingestd/tests/test_main.cpp`
- Create: `cpp/ingestd/tests/test_domain_cache.cpp`

- [ ] **Step 1: Write failing domain cache test**

Add to `cpp/ingestd/tests/test_main.cpp`:

```cpp
void test_domain_cache_loads_active_rules();
```

Create `cpp/ingestd/tests/test_domain_cache.cpp`:

```cpp
#include "../src/domain_cache.h"
#include "../src/sqlite_db.h"

#include <filesystem>
#include <string>

namespace test {
void check(bool condition, const std::string& message);
}

void test_domain_cache_loads_active_rules() {
    namespace fs = std::filesystem;
    const fs::path db_path = fs::temp_directory_path() / "rapid-inbox-domain-cache.sqlite";
    fs::remove(db_path);
    rapid_inbox::ingestd::SqliteDb db(db_path, 5000);
    db.exec("CREATE TABLE domains (id INTEGER PRIMARY KEY, root_domain_ascii TEXT, accept_exact INTEGER, accept_subdomains INTEGER, plus_addressing_mode TEXT, local_part_case_sensitive INTEGER, is_active INTEGER)");
    db.exec("INSERT INTO domains VALUES (1, 'adb.com', 1, 1, 'keep', 0, 1)");
    db.exec("INSERT INTO domains VALUES (2, 'disabled.com', 1, 1, 'keep', 0, 0)");
    rapid_inbox::ingestd::DomainCache cache(db_path, 5000);
    cache.reload();
    auto allowed = cache.match_address("A@adb.com");
    test::check(allowed.has_value(), "active domain matches");
    test::check(allowed->address_canonical == "a@adb.com", "active domain canonical");
    auto disabled = cache.match_address("a@disabled.com");
    test::check(!disabled.has_value(), "inactive domain skipped");
}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cmake --build cpp/ingestd/build
```

Expected: build FAILS with missing `domain_cache.h` or `sqlite_db.h`.

- [ ] **Step 3: Implement SQLite wrapper and domain cache**

Create `cpp/ingestd/src/sqlite_db.h`:

```cpp
#pragma once

#include <filesystem>
#include <sqlite3.h>
#include <string>

namespace rapid_inbox::ingestd {

class SqliteDb {
public:
    SqliteDb(const std::filesystem::path& path, int busy_timeout_ms);
    ~SqliteDb();
    SqliteDb(const SqliteDb&) = delete;
    SqliteDb& operator=(const SqliteDb&) = delete;

    sqlite3* handle() const { return db_; }
    void exec(const std::string& sql) const;

private:
    sqlite3* db_ = nullptr;
};

class Statement {
public:
    Statement(sqlite3* db, const std::string& sql);
    ~Statement();
    Statement(const Statement&) = delete;
    Statement& operator=(const Statement&) = delete;

    sqlite3_stmt* get() const { return stmt_; }
    bool step_row();
    void step_done();
    void reset();

private:
    sqlite3_stmt* stmt_ = nullptr;
};

}
```

Create `cpp/ingestd/src/sqlite_db.cpp`:

```cpp
#include "sqlite_db.h"

#include <stdexcept>

namespace rapid_inbox::ingestd {
namespace {

std::runtime_error sqlite_error(sqlite3* db, const std::string& prefix) {
    return std::runtime_error(prefix + ": " + sqlite3_errmsg(db));
}

}

SqliteDb::SqliteDb(const std::filesystem::path& path, int busy_timeout_ms) {
    if (sqlite3_open(path.string().c_str(), &db_) != SQLITE_OK) {
        std::string message = sqlite3_errmsg(db_);
        sqlite3_close(db_);
        db_ = nullptr;
        throw std::runtime_error("sqlite open failed: " + message);
    }
    exec("PRAGMA journal_mode = WAL");
    exec("PRAGMA foreign_keys = ON");
    exec("PRAGMA synchronous = FULL");
    exec("PRAGMA busy_timeout = " + std::to_string(busy_timeout_ms));
}

SqliteDb::~SqliteDb() {
    if (db_ != nullptr) {
        sqlite3_close(db_);
    }
}

void SqliteDb::exec(const std::string& sql) const {
    char* error = nullptr;
    if (sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &error) != SQLITE_OK) {
        std::string message = error == nullptr ? sqlite3_errmsg(db_) : error;
        sqlite3_free(error);
        throw std::runtime_error("sqlite exec failed: " + message);
    }
}

Statement::Statement(sqlite3* db, const std::string& sql) {
    if (sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt_, nullptr) != SQLITE_OK) {
        throw sqlite_error(db, "sqlite prepare failed");
    }
}

Statement::~Statement() {
    if (stmt_ != nullptr) {
        sqlite3_finalize(stmt_);
    }
}

bool Statement::step_row() {
    const int rc = sqlite3_step(stmt_);
    if (rc == SQLITE_ROW) {
        return true;
    }
    if (rc == SQLITE_DONE) {
        return false;
    }
    throw std::runtime_error("sqlite step failed");
}

void Statement::step_done() {
    const int rc = sqlite3_step(stmt_);
    if (rc != SQLITE_DONE) {
        throw std::runtime_error("sqlite step done failed");
    }
}

void Statement::reset() {
    sqlite3_reset(stmt_);
    sqlite3_clear_bindings(stmt_);
}

}
```

Create `cpp/ingestd/src/domain_cache.h`:

```cpp
#pragma once

#include "domain_matcher.h"

#include <filesystem>
#include <mutex>
#include <optional>

namespace rapid_inbox::ingestd {

class DomainCache {
public:
    DomainCache(std::filesystem::path database_path, int busy_timeout_ms);
    void reload();
    std::optional<DomainMatch> match_address(const std::string& address) const;

private:
    std::filesystem::path database_path_;
    int busy_timeout_ms_;
    mutable std::mutex mutex_;
    DomainMatcher matcher_;
};

}
```

Create `cpp/ingestd/src/domain_cache.cpp`:

```cpp
#include "domain_cache.h"

#include "sqlite_db.h"

#include <sqlite3.h>
#include <utility>
#include <vector>

namespace rapid_inbox::ingestd {

DomainCache::DomainCache(std::filesystem::path database_path, int busy_timeout_ms)
    : database_path_(std::move(database_path)), busy_timeout_ms_(busy_timeout_ms), matcher_({}) {}

void DomainCache::reload() {
    SqliteDb db(database_path_, busy_timeout_ms_);
    Statement stmt(db.handle(),
        "SELECT id, root_domain_ascii, accept_exact, accept_subdomains, plus_addressing_mode, local_part_case_sensitive "
        "FROM domains WHERE is_active = 1");
    std::vector<DomainRule> rules;
    while (stmt.step_row()) {
        rules.push_back(DomainRule{
            sqlite3_column_int(stmt.get(), 0),
            reinterpret_cast<const char*>(sqlite3_column_text(stmt.get(), 1)),
            sqlite3_column_int(stmt.get(), 2) != 0,
            sqlite3_column_int(stmt.get(), 3) != 0,
            reinterpret_cast<const char*>(sqlite3_column_text(stmt.get(), 4)),
            sqlite3_column_int(stmt.get(), 5) != 0,
        });
    }
    std::lock_guard<std::mutex> guard(mutex_);
    matcher_ = DomainMatcher(std::move(rules));
}

std::optional<DomainMatch> DomainCache::match_address(const std::string& address) const {
    std::lock_guard<std::mutex> guard(mutex_);
    return matcher_.match_address(address);
}

}
```

Add `src/sqlite_db.cpp`, `src/domain_cache.cpp`, and `tests/test_domain_cache.cpp` to `cpp/ingestd/CMakeLists.txt`.

- [ ] **Step 4: Run cache tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 添加 ingestd 域名缓存"
```

---

### Task 6: Mail Job And Bounded Queue

**Files:**
- Create: `cpp/ingestd/src/mail_job.h`
- Create: `cpp/ingestd/src/mail_queue.h`
- Create: `cpp/ingestd/src/mail_queue.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Modify: `cpp/ingestd/tests/test_main.cpp`
- Create: `cpp/ingestd/tests/test_mail_queue.cpp`

- [ ] **Step 1: Write failing queue tests**

Add to `cpp/ingestd/tests/test_main.cpp`:

```cpp
void test_mail_queue_capacity_and_close();
```

Create `cpp/ingestd/tests/test_mail_queue.cpp`:

```cpp
#include "../src/mail_queue.h"

#include <chrono>
#include <string>
#include <vector>

namespace test {
void check(bool condition, const std::string& message);
}

void test_mail_queue_capacity_and_close() {
    rapid_inbox::ingestd::MailQueue queue(1);
    rapid_inbox::ingestd::MailJob job;
    job.message_id = "msg_1";
    test::check(queue.try_push(job), "first push fits");
    test::check(!queue.try_push(job), "second push rejected by capacity");
    auto popped = queue.pop_batch(10, std::chrono::milliseconds(1));
    test::check(popped.size() == 1, "pop one item");
    test::check(popped[0].message_id == "msg_1", "popped message id");
    queue.close();
    test::check(!queue.try_push(job), "push rejected after close");
    auto empty = queue.pop_batch(10, std::chrono::milliseconds(1));
    test::check(empty.empty(), "closed empty queue returns empty batch");
}
```

- [ ] **Step 2: Run queue tests to verify failure**

Run:

```bash
cmake --build cpp/ingestd/build
```

Expected: build FAILS with missing `mail_queue.h`.

- [ ] **Step 3: Implement job structs and queue**

Create `cpp/ingestd/src/mail_job.h`:

```cpp
#pragma once

#include "domain_matcher.h"

#include <string>
#include <vector>

namespace rapid_inbox::ingestd {

struct RecipientDelivery {
    std::string delivery_id;
    std::string rcpt_to;
    DomainMatch match;
};

struct MailJob {
    std::string smtp_session_id;
    std::string message_id;
    std::string envelope_from;
    std::string received_at;
    std::string raw_path;
    std::string manifest_path;
    std::string raw_sha256;
    std::string raw_content;
    std::vector<RecipientDelivery> recipients;
};

}
```

Create `cpp/ingestd/src/mail_queue.h`:

```cpp
#pragma once

#include "mail_job.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <mutex>
#include <queue>
#include <vector>

namespace rapid_inbox::ingestd {

class MailQueue {
public:
    explicit MailQueue(std::size_t capacity);
    bool try_push(const MailJob& job);
    std::vector<MailJob> pop_batch(std::size_t max_items, std::chrono::milliseconds wait_for);
    void close();
    bool closed() const;
    std::size_t size() const;

private:
    std::size_t capacity_;
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    std::queue<MailJob> queue_;
    bool closed_ = false;
};

}
```

Create `cpp/ingestd/src/mail_queue.cpp`:

```cpp
#include "mail_queue.h"

namespace rapid_inbox::ingestd {

MailQueue::MailQueue(std::size_t capacity) : capacity_(capacity) {}

bool MailQueue::try_push(const MailJob& job) {
    {
        std::lock_guard<std::mutex> guard(mutex_);
        if (closed_ || queue_.size() >= capacity_) {
            return false;
        }
        queue_.push(job);
    }
    changed_.notify_one();
    return true;
}

std::vector<MailJob> MailQueue::pop_batch(std::size_t max_items, std::chrono::milliseconds wait_for) {
    std::unique_lock<std::mutex> lock(mutex_);
    changed_.wait_for(lock, wait_for, [&] { return closed_ || !queue_.empty(); });
    std::vector<MailJob> batch;
    while (!queue_.empty() && batch.size() < max_items) {
        batch.push_back(std::move(queue_.front()));
        queue_.pop();
    }
    return batch;
}

void MailQueue::close() {
    {
        std::lock_guard<std::mutex> guard(mutex_);
        closed_ = true;
    }
    changed_.notify_all();
}

bool MailQueue::closed() const {
    std::lock_guard<std::mutex> guard(mutex_);
    return closed_;
}

std::size_t MailQueue::size() const {
    std::lock_guard<std::mutex> guard(mutex_);
    return queue_.size();
}

}
```

Add `src/mail_queue.cpp` and `tests/test_mail_queue.cpp` to `cpp/ingestd/CMakeLists.txt`.

- [ ] **Step 4: Run queue tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 添加 ingestd 内存队列"
```

---

### Task 7: Batch Writer Storage Artifacts

**Files:**
- Create: `cpp/ingestd/src/batch_writer.h`
- Create: `cpp/ingestd/src/batch_writer.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Modify: `cpp/ingestd/tests/test_main.cpp`
- Create: `cpp/ingestd/tests/test_batch_writer.cpp`

- [ ] **Step 1: Write failing storage writer test**

Add to `cpp/ingestd/tests/test_main.cpp`:

```cpp
void test_batch_writer_writes_raw_and_manifest();
```

Create `cpp/ingestd/tests/test_batch_writer.cpp`:

```cpp
#include "../src/batch_writer.h"
#include "../src/mail_job.h"
#include "../src/storage_path.h"

#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace test {
void check(bool condition, const std::string& message);
}

static rapid_inbox::ingestd::MailJob sample_job() {
    rapid_inbox::ingestd::MailJob job;
    job.smtp_session_id = "smtp_1";
    job.message_id = "msg_1";
    job.envelope_from = "sender@example.com";
    job.received_at = "2026-05-12T03:04:05Z";
    job.raw_content = "Subject: Hello\r\n\r\nBody";
    job.raw_sha256 = "digest";
    job.raw_path = rapid_inbox::ingestd::raw_message_path(job.message_id, job.received_at);
    job.manifest_path = rapid_inbox::ingestd::manifest_path(job.message_id, job.received_at);
    rapid_inbox::ingestd::DomainMatch match{1, "adb.com", "adb.com", "code", "code", "code@adb.com"};
    job.recipients.push_back({"dlv_1", "code@adb.com", match});
    return job;
}

void test_batch_writer_writes_raw_and_manifest() {
    namespace fs = std::filesystem;
    const fs::path root = fs::temp_directory_path() / "rapid-inbox-writer-storage";
    fs::remove_all(root);
    rapid_inbox::ingestd::BatchWriter writer(root, root / "app.db", 5000, false);
    const rapid_inbox::ingestd::MailJob job = sample_job();
    writer.write_storage_artifacts({job});
    const fs::path raw = root / job.raw_path;
    const fs::path manifest = root / job.manifest_path;
    test::check(fs::exists(raw), "raw file exists");
    test::check(fs::exists(manifest), "manifest file exists");
    std::ifstream raw_input(raw);
    std::string raw_content((std::istreambuf_iterator<char>(raw_input)), std::istreambuf_iterator<char>());
    test::check(raw_content == job.raw_content, "raw content");
    std::ifstream manifest_input(manifest);
    std::string manifest_content((std::istreambuf_iterator<char>(manifest_input)), std::istreambuf_iterator<char>());
    test::check(manifest_content.find("\"message_id\":\"msg_1\"") != std::string::npos, "manifest message id");
    test::check(manifest_content.find("\"rcpt_to\":\"code@adb.com\"") != std::string::npos, "manifest recipient");
}
```

- [ ] **Step 2: Run storage writer test to verify failure**

Run:

```bash
cmake --build cpp/ingestd/build
```

Expected: build FAILS with missing `batch_writer.h`.

- [ ] **Step 3: Implement storage artifact writer**

Create `cpp/ingestd/src/batch_writer.h`:

```cpp
#pragma once

#include "mail_job.h"

#include <filesystem>
#include <vector>

namespace rapid_inbox::ingestd {

class BatchWriter {
public:
    BatchWriter(std::filesystem::path storage_root,
                std::filesystem::path database_path,
                int busy_timeout_ms,
                bool fsync_storage);

    void write_storage_artifacts(const std::vector<MailJob>& jobs) const;
    void write_sqlite_records(const std::vector<MailJob>& jobs) const;
    void write_batch(const std::vector<MailJob>& jobs) const;

private:
    std::filesystem::path resolve_storage_path(const std::string& relative_path) const;
    void write_file_atomic(const std::string& relative_path, const std::string& content) const;
    std::string build_manifest(const MailJob& job) const;

    std::filesystem::path storage_root_;
    std::filesystem::path database_path_;
    int busy_timeout_ms_;
    bool fsync_storage_;
};

}
```

Create the storage part of `cpp/ingestd/src/batch_writer.cpp`:

```cpp
#include "batch_writer.h"

#include "json_util.h"
#include "sqlite_db.h"

#include <fcntl.h>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <unistd.h>

namespace rapid_inbox::ingestd {
namespace {

void fsync_directory(const std::filesystem::path& path) {
    const int fd = ::open(path.c_str(), O_RDONLY | O_DIRECTORY);
    if (fd >= 0) {
        ::fsync(fd);
        ::close(fd);
    }
}

}

BatchWriter::BatchWriter(std::filesystem::path storage_root,
                         std::filesystem::path database_path,
                         int busy_timeout_ms,
                         bool fsync_storage)
    : storage_root_(std::move(storage_root)),
      database_path_(std::move(database_path)),
      busy_timeout_ms_(busy_timeout_ms),
      fsync_storage_(fsync_storage) {}

std::filesystem::path BatchWriter::resolve_storage_path(const std::string& relative_path) const {
    std::filesystem::path relative(relative_path);
    if (relative.is_absolute()) {
        throw std::runtime_error("storage path must be relative");
    }
    const auto root = std::filesystem::weakly_canonical(storage_root_);
    const auto target = std::filesystem::weakly_canonical(root / relative);
    const auto root_text = root.string();
    const auto target_text = target.string();
    if (target_text.rfind(root_text, 0) != 0) {
        throw std::runtime_error("storage path escapes storage root");
    }
    return target;
}

void BatchWriter::write_file_atomic(const std::string& relative_path, const std::string& content) const {
    const auto target = resolve_storage_path(relative_path);
    std::filesystem::create_directories(target.parent_path());
    const auto part = target.parent_path() / ("." + target.filename().string() + ".part");
    {
        std::ofstream output(part, std::ios::binary);
        output.write(content.data(), static_cast<std::streamsize>(content.size()));
        output.flush();
        if (!output) {
            throw std::runtime_error("write failed: " + part.string());
        }
    }
    if (fsync_storage_) {
        const int fd = ::open(part.c_str(), O_RDONLY);
        if (fd >= 0) {
            ::fsync(fd);
            ::close(fd);
        }
    }
    std::filesystem::rename(part, target);
    if (fsync_storage_) {
        fsync_directory(target.parent_path());
    }
}

std::string BatchWriter::build_manifest(const MailJob& job) const {
    std::ostringstream output;
    output << "{";
    output << "\"message_id\":\"" << json_escape(job.message_id) << "\",";
    output << "\"smtp_session_id\":\"" << json_escape(job.smtp_session_id) << "\",";
    output << "\"envelope_from\":\"" << json_escape(job.envelope_from) << "\",";
    output << "\"received_at\":\"" << json_escape(job.received_at) << "\",";
    output << "\"raw_path\":\"" << json_escape(job.raw_path) << "\",";
    output << "\"raw_sha256\":\"" << json_escape(job.raw_sha256) << "\",";
    output << "\"raw_size_bytes\":" << job.raw_content.size() << ",";
    output << "\"rcpt_tos\":[";
    for (std::size_t i = 0; i < job.recipients.size(); ++i) {
        if (i != 0) {
            output << ",";
        }
        output << "\"" << json_escape(job.recipients[i].rcpt_to) << "\"";
    }
    output << "],\"recipients\":[";
    for (std::size_t i = 0; i < job.recipients.size(); ++i) {
        const auto& recipient = job.recipients[i];
        if (i != 0) {
            output << ",";
        }
        output << "{";
        output << "\"rcpt_to\":\"" << json_escape(recipient.rcpt_to) << "\",";
        output << "\"domain_id\":" << recipient.match.domain_id << ",";
        output << "\"domain_ascii\":\"" << json_escape(recipient.match.domain_ascii) << "\",";
        output << "\"root_domain_ascii\":\"" << json_escape(recipient.match.root_domain_ascii) << "\",";
        output << "\"local_part_canonical\":\"" << json_escape(recipient.match.local_part_canonical) << "\",";
        output << "\"address_canonical\":\"" << json_escape(recipient.match.address_canonical) << "\"";
        output << "}";
    }
    output << "]}";
    return output.str();
}

void BatchWriter::write_storage_artifacts(const std::vector<MailJob>& jobs) const {
    for (const MailJob& job : jobs) {
        write_file_atomic(job.manifest_path, build_manifest(job));
        write_file_atomic(job.raw_path, job.raw_content);
    }
}

void BatchWriter::write_sqlite_records(const std::vector<MailJob>& jobs) const {
    (void)jobs;
}

void BatchWriter::write_batch(const std::vector<MailJob>& jobs) const {
    write_storage_artifacts(jobs);
    write_sqlite_records(jobs);
}

}
```

Add `src/batch_writer.cpp` and `tests/test_batch_writer.cpp` to `cpp/ingestd/CMakeLists.txt`.

- [ ] **Step 4: Run storage artifact tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 写入 ingestd 邮件落盘文件"
```

---

### Task 8: Batch Writer SQLite Pending Records

**Files:**
- Modify: `cpp/ingestd/src/batch_writer.cpp`
- Modify: `cpp/ingestd/tests/test_batch_writer.cpp`

- [ ] **Step 1: Write failing SQLite writer test**

Append this test to `cpp/ingestd/tests/test_batch_writer.cpp` and call it from `test_main.cpp`:

```cpp
void test_batch_writer_writes_sqlite_pending_records() {
    namespace fs = std::filesystem;
    const fs::path root = fs::temp_directory_path() / "rapid-inbox-writer-sqlite";
    fs::remove_all(root);
    fs::create_directories(root);
    const fs::path db_path = root / "app.db";
    {
        rapid_inbox::ingestd::SqliteDb db(db_path, 5000);
        const fs::path schema_path = fs::path(RAPID_INBOX_REPO_ROOT) / "sqlite_schema.sql";
        std::ifstream schema(schema_path);
        std::string sql((std::istreambuf_iterator<char>(schema)), std::istreambuf_iterator<char>());
        db.exec(sql);
        db.exec("INSERT INTO domains (id, root_domain_ascii, root_domain_unicode, created_at, updated_at) VALUES (1, 'adb.com', 'adb.com', '2026-05-12T03:04:05Z', '2026-05-12T03:04:05Z')");
    }
    rapid_inbox::ingestd::BatchWriter writer(root, db_path, 5000, false);
    const rapid_inbox::ingestd::MailJob job = sample_job();
    writer.write_batch({job});
    rapid_inbox::ingestd::SqliteDb db(db_path, 5000);
    rapid_inbox::ingestd::Statement message(db.handle(), "SELECT parse_status, raw_path, envelope_from FROM messages WHERE id = 'msg_1'");
    test::check(message.step_row(), "message row exists");
    test::check(std::string(reinterpret_cast<const char*>(sqlite3_column_text(message.get(), 0))) == "pending", "message pending");
    test::check(std::string(reinterpret_cast<const char*>(sqlite3_column_text(message.get(), 1))) == job.raw_path, "message raw path");
    test::check(std::string(reinterpret_cast<const char*>(sqlite3_column_text(message.get(), 2))) == "sender@example.com", "message envelope from");
    rapid_inbox::ingestd::Statement mailbox(db.handle(), "SELECT message_count, address_canonical FROM mailboxes WHERE address_canonical = 'code@adb.com'");
    test::check(mailbox.step_row(), "mailbox row exists");
    test::check(sqlite3_column_int(mailbox.get(), 0) == 1, "mailbox count");
    rapid_inbox::ingestd::Statement delivery(db.handle(), "SELECT id FROM message_deliveries WHERE message_id = 'msg_1'");
    test::check(delivery.step_row(), "delivery exists");
}
```

Add includes to the top of `test_batch_writer.cpp`:

```cpp
#include "../src/sqlite_db.h"
#include <sqlite3.h>
```

- [ ] **Step 2: Run SQLite writer test to verify failure**

Run:

```bash
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: test FAILS because `write_sqlite_records` does nothing.

- [ ] **Step 3: Implement SQLite pending writes**

Replace `BatchWriter::write_sqlite_records` in `cpp/ingestd/src/batch_writer.cpp` with:

```cpp
void BatchWriter::write_sqlite_records(const std::vector<MailJob>& jobs) const {
    if (jobs.empty()) {
        return;
    }
    SqliteDb db(database_path_, busy_timeout_ms_);
    db.exec("BEGIN IMMEDIATE");
    try {
        Statement insert_session(db.handle(),
            "INSERT INTO smtp_sessions (id, remote_ip, remote_port, helo_name, status, tls_used, connect_at, first_command_at, last_command_at, last_mail_from, bytes_received, message_count) "
            "VALUES (?, 'unknown', NULL, NULL, 'closed', 0, ?, ?, ?, ?, ?, 1) "
            "ON CONFLICT(id) DO UPDATE SET last_command_at = excluded.last_command_at, message_count = smtp_sessions.message_count + 1, bytes_received = smtp_sessions.bytes_received + excluded.bytes_received");
        Statement insert_message(db.handle(),
            "INSERT INTO messages (id, smtp_session_id, raw_path, raw_sha256, raw_size_bytes, envelope_from, from_addr, received_at, parse_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')");
        Statement upsert_mailbox(db.handle(),
            "INSERT INTO mailboxes (domain_id, local_part_canonical, rcpt_domain_ascii, address_canonical, address_display, first_seen_at, last_seen_at, latest_message_at, message_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1) "
            "ON CONFLICT(address_canonical) DO UPDATE SET last_seen_at = excluded.last_seen_at, latest_message_at = excluded.latest_message_at, message_count = mailboxes.message_count + 1");
        Statement select_mailbox(db.handle(), "SELECT id FROM mailboxes WHERE address_canonical = ?");
        Statement insert_delivery(db.handle(),
            "INSERT INTO message_deliveries (id, message_id, mailbox_id, rcpt_to, delivered_at) VALUES (?, ?, ?, ?, ?)");
        Statement metric(db.handle(),
            "INSERT INTO mail_metric_buckets (bucket_ts, deliveries, parse_failures) VALUES (?, ?, 0) "
            "ON CONFLICT(bucket_ts) DO UPDATE SET deliveries = deliveries + excluded.deliveries");

        for (const MailJob& job : jobs) {
            sqlite3_bind_text(insert_session.get(), 1, job.smtp_session_id.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_session.get(), 2, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_session.get(), 3, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_session.get(), 4, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_session.get(), 5, job.envelope_from.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_int64(insert_session.get(), 6, static_cast<sqlite3_int64>(job.raw_content.size()));
            insert_session.step_done();
            insert_session.reset();

            sqlite3_bind_text(insert_message.get(), 1, job.message_id.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_message.get(), 2, job.smtp_session_id.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_message.get(), 3, job.raw_path.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_message.get(), 4, job.raw_sha256.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_int64(insert_message.get(), 5, static_cast<sqlite3_int64>(job.raw_content.size()));
            sqlite3_bind_text(insert_message.get(), 6, job.envelope_from.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_message.get(), 7, job.envelope_from.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(insert_message.get(), 8, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
            insert_message.step_done();
            insert_message.reset();

            int deliveries = 0;
            for (const RecipientDelivery& recipient : job.recipients) {
                sqlite3_bind_int(upsert_mailbox.get(), 1, recipient.match.domain_id);
                sqlite3_bind_text(upsert_mailbox.get(), 2, recipient.match.local_part_canonical.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(upsert_mailbox.get(), 3, recipient.match.domain_ascii.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(upsert_mailbox.get(), 4, recipient.match.address_canonical.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(upsert_mailbox.get(), 5, recipient.match.address_canonical.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(upsert_mailbox.get(), 6, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(upsert_mailbox.get(), 7, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(upsert_mailbox.get(), 8, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
                upsert_mailbox.step_done();
                upsert_mailbox.reset();

                sqlite3_bind_text(select_mailbox.get(), 1, recipient.match.address_canonical.c_str(), -1, SQLITE_TRANSIENT);
                if (!select_mailbox.step_row()) {
                    throw std::runtime_error("mailbox select failed after upsert");
                }
                const int mailbox_id = sqlite3_column_int(select_mailbox.get(), 0);
                select_mailbox.reset();

                sqlite3_bind_text(insert_delivery.get(), 1, recipient.delivery_id.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(insert_delivery.get(), 2, job.message_id.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_int(insert_delivery.get(), 3, mailbox_id);
                sqlite3_bind_text(insert_delivery.get(), 4, recipient.rcpt_to.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_text(insert_delivery.get(), 5, job.received_at.c_str(), -1, SQLITE_TRANSIENT);
                insert_delivery.step_done();
                insert_delivery.reset();
                deliveries += 1;
            }

            const std::string bucket = job.received_at.substr(0, 19) + "Z";
            sqlite3_bind_text(metric.get(), 1, bucket.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_int(metric.get(), 2, deliveries);
            metric.step_done();
            metric.reset();
        }
        db.exec("COMMIT");
    } catch (...) {
        db.exec("ROLLBACK");
        throw;
    }
}
```

- [ ] **Step 4: Run writer tests and Python DB-adjacent tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
.venv/bin/pytest tests/test_ingest_pipeline.py tests/test_public_routes.py tests/test_admin_views.py -q
```

Expected: C++ tests pass and selected Python tests pass.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 批量写入 ingestd SQLite 记录"
```

---

### Task 9: SMTP Session Parser

**Files:**
- Create: `cpp/ingestd/src/smtp_session.h`
- Create: `cpp/ingestd/src/smtp_session.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Modify: `cpp/ingestd/tests/test_main.cpp`
- Create: `cpp/ingestd/tests/test_smtp_session.cpp`

- [ ] **Step 1: Write failing SMTP parser tests**

Add to `cpp/ingestd/tests/test_main.cpp`:

```cpp
void test_smtp_session_accepts_valid_message();
void test_smtp_session_rejects_unknown_domain();
```

Create `cpp/ingestd/tests/test_smtp_session.cpp`:

```cpp
#include "../src/domain_matcher.h"
#include "../src/mail_queue.h"
#include "../src/smtp_session.h"

#include <string>

namespace test {
void check(bool condition, const std::string& message);
}

void test_smtp_session_accepts_valid_message() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("EHLO client") == "250 rapid-inbox-ingestd", "ehlo");
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "rcpt");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "data");
    test::check(session.handle_line("Subject: Hi") == "", "data line no response");
    test::check(session.handle_line("") == "", "blank data line");
    const std::string queued = session.handle_line(".");
    test::check(queued.rfind("250 queued as msg_", 0) == 0, "queued response");
    auto batch = queue.pop_batch(10, std::chrono::milliseconds(1));
    test::check(batch.size() == 1, "queued one job");
    test::check(batch[0].recipients[0].match.address_canonical == "code@adb.com", "canonical recipient");
}

void test_smtp_session_rejects_unknown_domain() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@unknown.com>") == "550 domain not allowed", "unknown rejected");
}
```

- [ ] **Step 2: Run parser tests to verify failure**

Run:

```bash
cmake --build cpp/ingestd/build
```

Expected: build FAILS with missing `smtp_session.h`.

- [ ] **Step 3: Implement SMTP session parser**

Create `cpp/ingestd/src/smtp_session.h`:

```cpp
#pragma once

#include "domain_matcher.h"
#include "mail_queue.h"

#include <optional>
#include <string>
#include <vector>

namespace rapid_inbox::ingestd {

class SmtpSession {
public:
    SmtpSession(const DomainMatcher& matcher,
                MailQueue& queue,
                int max_recipients,
                int max_message_size_bytes);

    std::string greeting() const;
    std::string handle_line(const std::string& line);

private:
    std::string handle_command(const std::string& line);
    std::string finish_data();
    std::optional<std::string> extract_path_argument(const std::string& line) const;

    const DomainMatcher& matcher_;
    MailQueue& queue_;
    int max_recipients_;
    int max_message_size_bytes_;
    std::string session_id_;
    std::string mail_from_;
    std::vector<RecipientDelivery> recipients_;
    bool in_data_ = false;
    std::string data_;
};

}
```

Create `cpp/ingestd/src/smtp_session.cpp`:

```cpp
#include "smtp_session.h"

#include "id.h"
#include "sha256.h"
#include "storage_path.h"
#include "time_utils.h"

#include <algorithm>
#include <cctype>

namespace rapid_inbox::ingestd {
namespace {

std::string upper_ascii(std::string value) {
    for (char& ch : value) {
        ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
    }
    return value;
}

bool starts_with_ci(const std::string& value, const std::string& prefix) {
    return upper_ascii(value.substr(0, prefix.size())) == upper_ascii(prefix);
}

}

SmtpSession::SmtpSession(const DomainMatcher& matcher,
                         MailQueue& queue,
                         int max_recipients,
                         int max_message_size_bytes)
    : matcher_(matcher),
      queue_(queue),
      max_recipients_(max_recipients),
      max_message_size_bytes_(max_message_size_bytes),
      session_id_(make_prefixed_id("smtp_")) {}

std::string SmtpSession::greeting() const {
    return "220 rapid-inbox-ingestd";
}

std::string SmtpSession::handle_line(const std::string& line) {
    if (in_data_) {
        if (line == ".") {
            return finish_data();
        }
        std::string content_line = line;
        if (!content_line.empty() && content_line[0] == '.') {
            content_line.erase(content_line.begin());
        }
        data_ += content_line;
        data_ += "\r\n";
        if (static_cast<int>(data_.size()) > max_message_size_bytes_) {
            in_data_ = false;
            data_.clear();
            return "552 message too large";
        }
        return "";
    }
    return handle_command(line);
}

std::string SmtpSession::handle_command(const std::string& line) {
    if (starts_with_ci(line, "EHLO") || starts_with_ci(line, "HELO")) {
        return "250 rapid-inbox-ingestd";
    }
    if (starts_with_ci(line, "QUIT")) {
        return "221 2.0.0 Bye";
    }
    if (starts_with_ci(line, "RSET")) {
        mail_from_.clear();
        recipients_.clear();
        data_.clear();
        in_data_ = false;
        return "250 OK";
    }
    if (starts_with_ci(line, "MAIL FROM:")) {
        auto value = extract_path_argument(line);
        mail_from_ = value.value_or("");
        recipients_.clear();
        return "250 OK";
    }
    if (starts_with_ci(line, "RCPT TO:")) {
        if (static_cast<int>(recipients_.size()) >= max_recipients_) {
            return "552 too many recipients";
        }
        auto value = extract_path_argument(line);
        if (!value.has_value()) {
            return "501 invalid recipient";
        }
        auto match = matcher_.match_address(*value);
        if (!match.has_value()) {
            return "550 domain not allowed";
        }
        recipients_.push_back(RecipientDelivery{make_prefixed_id("dlv_"), *value, *match});
        return "250 OK";
    }
    if (starts_with_ci(line, "DATA")) {
        if (recipients_.empty()) {
            return "554 no valid recipients";
        }
        in_data_ = true;
        data_.clear();
        return "354 End data with <CR><LF>.<CR><LF>";
    }
    return "502 command not implemented";
}

std::string SmtpSession::finish_data() {
    in_data_ = false;
    const std::string received_at = utc_now();
    MailJob job;
    job.smtp_session_id = session_id_;
    job.message_id = make_prefixed_id("msg_");
    job.envelope_from = mail_from_;
    job.received_at = received_at;
    job.raw_content = data_;
    job.raw_sha256 = sha256_hex(data_);
    job.raw_path = raw_message_path(job.message_id, received_at);
    job.manifest_path = manifest_path(job.message_id, received_at);
    job.recipients = recipients_;
    data_.clear();
    if (!queue_.try_push(job)) {
        return "451 temporary queue full";
    }
    return "250 queued as " + job.message_id;
}

std::optional<std::string> SmtpSession::extract_path_argument(const std::string& line) const {
    const auto colon = line.find(':');
    if (colon == std::string::npos) {
        return std::nullopt;
    }
    std::string value = line.substr(colon + 1);
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), [](unsigned char ch) { return !std::isspace(ch); }));
    value.erase(std::find_if(value.rbegin(), value.rend(), [](unsigned char ch) { return !std::isspace(ch); }).base(), value.end());
    if (value.size() >= 2 && value.front() == '<' && value.back() == '>') {
        value = value.substr(1, value.size() - 2);
    }
    return value.empty() ? std::nullopt : std::optional<std::string>(value);
}

}
```

Add `src/smtp_session.cpp` and `tests/test_smtp_session.cpp` to `cpp/ingestd/CMakeLists.txt`.

- [ ] **Step 4: Run SMTP parser tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 实现 ingestd SMTP 会话解析"
```

---

### Task 10: Writer Worker And Binary Main Loop

**Files:**
- Modify: `cpp/ingestd/src/main.cpp`
- Create: `cpp/ingestd/src/ingest_app.h`
- Create: `cpp/ingestd/src/ingest_app.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`

- [ ] **Step 1: Write a manual smoke expectation**

Run:

```bash
cpp/ingestd/build/rapid-inbox-ingestd --help
```

Expected: current scaffold prints `rapid-inbox-ingestd scaffold`; this does not expose runtime config.

- [ ] **Step 2: Add app class with writer thread**

Create `cpp/ingestd/src/ingest_app.h`:

```cpp
#pragma once

#include "batch_writer.h"
#include "config.h"
#include "domain_cache.h"
#include "mail_queue.h"

#include <atomic>
#include <thread>

namespace rapid_inbox::ingestd {

class IngestApp {
public:
    explicit IngestApp(Config config);
    ~IngestApp();
    IngestApp(const IngestApp&) = delete;
    IngestApp& operator=(const IngestApp&) = delete;

    void start_writer();
    void stop_and_drain();
    MailQueue& queue() { return queue_; }
    DomainCache& domains() { return domains_; }

private:
    void writer_loop();

    Config config_;
    MailQueue queue_;
    DomainCache domains_;
    BatchWriter writer_;
    std::atomic<bool> running_{false};
    std::thread writer_thread_;
};

}
```

Create `cpp/ingestd/src/ingest_app.cpp`:

```cpp
#include "ingest_app.h"

#include <chrono>
#include <iostream>

namespace rapid_inbox::ingestd {

IngestApp::IngestApp(Config config)
    : config_(std::move(config)),
      queue_(static_cast<std::size_t>(config_.ingest_queue_max_messages)),
      domains_(config_.database_path, config_.ingest_sqlite_busy_timeout_ms),
      writer_(config_.storage_root, config_.database_path, config_.ingest_sqlite_busy_timeout_ms, config_.ingest_storage_fsync) {}

IngestApp::~IngestApp() {
    stop_and_drain();
}

void IngestApp::start_writer() {
    domains_.reload();
    running_ = true;
    writer_thread_ = std::thread([this] { writer_loop(); });
}

void IngestApp::stop_and_drain() {
    queue_.close();
    running_ = false;
    if (writer_thread_.joinable()) {
        writer_thread_.join();
    }
}

void IngestApp::writer_loop() {
    while (running_ || queue_.size() > 0) {
        auto batch = queue_.pop_batch(static_cast<std::size_t>(config_.ingest_batch_max_messages),
                                     std::chrono::milliseconds(config_.ingest_flush_interval_ms));
        if (batch.empty()) {
            continue;
        }
        bool written = false;
        while (!written) {
            try {
                writer_.write_batch(batch);
                written = true;
            } catch (const std::exception& exc) {
                std::cerr << "ingestd writer retry after error: " << exc.what() << "\n";
                std::this_thread::sleep_for(std::chrono::milliseconds(250));
            }
        }
    }
}

}
```

Replace `cpp/ingestd/src/main.cpp`:

```cpp
#include "config.h"
#include "ingest_app.h"

#include <chrono>
#include <filesystem>
#include <iostream>
#include <string>
#include <thread>

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--help") {
        std::cout << "usage: rapid-inbox-ingestd [--base-dir PATH] [--writer-smoke]\n";
        return 0;
    }

    std::filesystem::path base_dir = std::filesystem::current_path();
    bool writer_smoke = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--base-dir" && i + 1 < argc) {
            base_dir = argv[++i];
        } else if (arg == "--writer-smoke") {
            writer_smoke = true;
        }
    }

    try {
        auto config = rapid_inbox::ingestd::Config::load(base_dir);
        rapid_inbox::ingestd::IngestApp app(config);
        app.start_writer();
        if (writer_smoke) {
            app.stop_and_drain();
            std::cout << "writer smoke ok\n";
            return 0;
        }
        std::cout << "rapid-inbox-ingestd writer started; SMTP server is added in the next task\n";
        app.stop_and_drain();
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "rapid-inbox-ingestd failed: " << exc.what() << "\n";
        return 1;
    }
}
```

Add `src/ingest_app.cpp` to `INGESTD_LIB_SOURCES`.

- [ ] **Step 3: Run app smoke**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
cpp/ingestd/build/rapid-inbox-ingestd --help
```

Expected: prints `usage: rapid-inbox-ingestd [--base-dir PATH] [--writer-smoke]`.

- [ ] **Step 4: Run tests**

Run:

```bash
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: `100% tests passed`.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd
git commit -m "feat: 添加 ingestd 写入工作线程"
```

---

### Task 11: TCP SMTP Server

**Files:**
- Create: `cpp/ingestd/src/smtp_server.h`
- Create: `cpp/ingestd/src/smtp_server.cpp`
- Modify: `cpp/ingestd/src/main.cpp`
- Modify: `cpp/ingestd/CMakeLists.txt`
- Create: `tests/test_cpp_ingestd_integration.py`

- [ ] **Step 1: Write failing Python black-box SMTP test**

Create `tests/test_cpp_ingestd_integration.py`:

```python
from __future__ import annotations

import asyncio
import os
import smtplib
import socket
import subprocess
from email.message import EmailMessage
from pathlib import Path

import pytest

from app.config import Settings
from app.db.connection import initialize_database
from app.runtime import RapidInboxRuntime


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.asyncio
async def test_cpp_ingestd_accepts_mail_and_python_reads_it(tmp_path: Path) -> None:
    build_dir = Path("cpp/ingestd/build")
    binary = build_dir / "rapid-inbox-ingestd"
    if not binary.exists():
        pytest.skip("rapid-inbox-ingestd has not been built")

    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "storage" / "app.db")
    settings.ensure_directories()
    initialize_database(settings.database_path)
    runtime = RapidInboxRuntime(settings)
    await runtime.start()
    try:
        await runtime.create_domain("adb.com")
    finally:
        await runtime.stop()

    port = _free_port()
    env = {
        **os.environ,
        "SMTP_HOST": "127.0.0.1",
        "SMTP_PORT": str(port),
        "STORAGE_ROOT": str(settings.storage_root),
        "DATABASE_PATH": str(settings.database_path),
        "INGEST_FLUSH_INTERVAL_MS": "50",
        "INGEST_BATCH_MAX_MESSAGES": "10",
    }
    process = subprocess.Popen(
        [str(binary), "--base-dir", str(tmp_path)],
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                await asyncio.sleep(0.05)
        else:
            stdout, stderr = process.communicate(timeout=1)
            raise AssertionError(f"ingestd did not listen\nstdout={stdout}\nstderr={stderr}")

        msg = EmailMessage()
        msg["Subject"] = "Hello"
        msg["From"] = "sender@example.com"
        msg["To"] = "code@adb.com"
        msg.set_content("Your code is 123456")
        with smtplib.SMTP("127.0.0.1", port, timeout=5) as smtp:
            smtp.send_message(msg)

        deadline = asyncio.get_running_loop().time() + 5
        while True:
            runtime = RapidInboxRuntime(settings)
            await runtime.start()
            try:
                mailbox = await runtime.get_mailbox_view("code@adb.com")
                if mailbox["message_count"] == 1:
                    break
            finally:
                await runtime.stop()
            if asyncio.get_running_loop().time() >= deadline:
                raise AssertionError("message was not visible to Python runtime")
            await asyncio.sleep(0.1)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
```

- [ ] **Step 2: Run integration test to verify failure**

Run:

```bash
.venv/bin/pytest tests/test_cpp_ingestd_integration.py -q
```

Expected: SKIP if binary missing, or FAIL because ingestd does not listen on SMTP yet.

- [ ] **Step 3: Add a snapshot method for SMTP sessions**

Add to `DomainCache` in `domain_cache.h`:

```cpp
DomainMatcher snapshot_matcher() const;
```

Add to `domain_cache.cpp`:

```cpp
DomainMatcher DomainCache::snapshot_matcher() const {
    std::lock_guard<std::mutex> guard(mutex_);
    return matcher_;
}
```

- [ ] **Step 4: Implement blocking TCP SMTP server**

Create `cpp/ingestd/src/smtp_server.h`:

```cpp
#pragma once

#include "domain_cache.h"
#include "mail_queue.h"

#include <atomic>
#include <string>
#include <thread>
#include <vector>

namespace rapid_inbox::ingestd {

class SmtpServer {
public:
    SmtpServer(std::string host,
               int port,
               DomainCache& domains,
               MailQueue& queue,
               int max_recipients,
               int max_message_size_bytes);
    ~SmtpServer();

    void start();
    void stop();

private:
    void accept_loop();
    void handle_client(int client_fd);

    std::string host_;
    int port_;
    DomainCache& domains_;
    MailQueue& queue_;
    int max_recipients_;
    int max_message_size_bytes_;
    std::atomic<bool> running_{false};
    int listen_fd_ = -1;
    std::thread accept_thread_;
    std::vector<std::thread> client_threads_;
};

}
```

Create `cpp/ingestd/src/smtp_server.cpp`:

```cpp
#include "smtp_server.h"

#include "smtp_session.h"

#include <arpa/inet.h>
#include <cstring>
#include <iostream>
#include <netinet/in.h>
#include <stdexcept>
#include <sys/socket.h>
#include <unistd.h>

namespace rapid_inbox::ingestd {
namespace {

void send_line(int fd, const std::string& line) {
    const std::string payload = line + "\r\n";
    ::send(fd, payload.data(), payload.size(), MSG_NOSIGNAL);
}

bool recv_line(int fd, std::string& line) {
    line.clear();
    char ch = 0;
    while (true) {
        const ssize_t got = ::recv(fd, &ch, 1, 0);
        if (got <= 0) {
            return false;
        }
        if (ch == '\n') {
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            return true;
        }
        line.push_back(ch);
    }
}

}

SmtpServer::SmtpServer(std::string host,
                       int port,
                       DomainCache& domains,
                       MailQueue& queue,
                       int max_recipients,
                       int max_message_size_bytes)
    : host_(std::move(host)),
      port_(port),
      domains_(domains),
      queue_(queue),
      max_recipients_(max_recipients),
      max_message_size_bytes_(max_message_size_bytes) {}

SmtpServer::~SmtpServer() {
    stop();
}

void SmtpServer::start() {
    listen_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd_ < 0) {
        throw std::runtime_error("socket failed");
    }
    int reuse = 1;
    ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_port = htons(static_cast<uint16_t>(port_));
    if (::inet_pton(AF_INET, host_.c_str(), &address.sin_addr) != 1) {
        throw std::runtime_error("invalid SMTP_HOST for MVP IPv4 server");
    }
    if (::bind(listen_fd_, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
        throw std::runtime_error("bind failed: " + std::string(std::strerror(errno)));
    }
    if (::listen(listen_fd_, 1024) != 0) {
        throw std::runtime_error("listen failed");
    }
    running_ = true;
    accept_thread_ = std::thread([this] { accept_loop(); });
}

void SmtpServer::stop() {
    running_ = false;
    if (listen_fd_ >= 0) {
        ::shutdown(listen_fd_, SHUT_RDWR);
        ::close(listen_fd_);
        listen_fd_ = -1;
    }
    if (accept_thread_.joinable()) {
        accept_thread_.join();
    }
    for (std::thread& thread : client_threads_) {
        if (thread.joinable()) {
            thread.join();
        }
    }
}

void SmtpServer::accept_loop() {
    while (running_) {
        const int client_fd = ::accept(listen_fd_, nullptr, nullptr);
        if (client_fd < 0) {
            if (running_) {
                std::cerr << "accept failed\n";
            }
            continue;
        }
        client_threads_.emplace_back([this, client_fd] { handle_client(client_fd); });
    }
}

void SmtpServer::handle_client(int client_fd) {
    try {
        DomainMatcher matcher = domains_.snapshot_matcher();
        SmtpSession session(matcher, queue_, max_recipients_, max_message_size_bytes_);
        send_line(client_fd, session.greeting());
        std::string line;
        while (recv_line(client_fd, line)) {
            const std::string response = session.handle_line(line);
            if (!response.empty()) {
                send_line(client_fd, response);
                if (response.rfind("221", 0) == 0) {
                    break;
                }
            }
        }
    } catch (const std::exception& exc) {
        std::cerr << "smtp client failed: " << exc.what() << "\n";
    }
    ::close(client_fd);
}

}
```

Modify `cpp/ingestd/src/main.cpp` to start SMTP server:

```cpp
#include "smtp_server.h"

// after app.start_writer()
rapid_inbox::ingestd::SmtpServer server(
    config.smtp_host,
    config.smtp_port,
    app.domains(),
    app.queue(),
    config.max_recipients_per_message,
    config.max_message_size_bytes);
server.start();
std::cout << "rapid-inbox-ingestd listening on " << config.smtp_host << ":" << config.smtp_port << "\n";
while (true) {
    std::this_thread::sleep_for(std::chrono::seconds(1));
}
```

Keep `--writer-smoke` returning before server startup so CMake smoke remains fast.

Add `src/smtp_server.cpp` to `INGESTD_LIB_SOURCES`.

- [ ] **Step 5: Run SMTP integration**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
.venv/bin/pytest tests/test_cpp_ingestd_integration.py -q
```

Expected: C++ tests pass and integration test passes.

- [ ] **Step 6: Commit**

```bash
git add cpp/ingestd tests/test_cpp_ingestd_integration.py
git commit -m "feat: 添加 ingestd SMTP 服务"
```

---

### Task 12: Normal Shutdown Drain

**Files:**
- Modify: `cpp/ingestd/src/main.cpp`
- Modify: `cpp/ingestd/src/smtp_server.h`
- Modify: `cpp/ingestd/src/smtp_server.cpp`
- Modify: `tests/test_cpp_ingestd_integration.py`

- [ ] **Step 1: Write failing shutdown-drain integration test**

Append to `tests/test_cpp_ingestd_integration.py`:

```python
@pytest.mark.asyncio
async def test_cpp_ingestd_sigterm_drains_returned_250_mail(tmp_path: Path) -> None:
    binary = Path("cpp/ingestd/build/rapid-inbox-ingestd")
    if not binary.exists():
        pytest.skip("rapid-inbox-ingestd has not been built")
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "storage" / "app.db")
    settings.ensure_directories()
    initialize_database(settings.database_path)
    runtime = RapidInboxRuntime(settings)
    await runtime.start()
    try:
        await runtime.create_domain("adb.com")
    finally:
        await runtime.stop()

    port = _free_port()
    env = {**os.environ, "SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(port), "STORAGE_ROOT": str(settings.storage_root), "DATABASE_PATH": str(settings.database_path), "INGEST_FLUSH_INTERVAL_MS": "1000"}
    process = subprocess.Popen([str(binary), "--base-dir", str(tmp_path)], cwd=Path.cwd(), env=env, text=True)
    try:
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                await asyncio.sleep(0.05)
        msg = EmailMessage()
        msg["Subject"] = "Drain"
        msg["From"] = "sender@example.com"
        msg["To"] = "code@adb.com"
        msg.set_content("Drain body")
        with smtplib.SMTP("127.0.0.1", port, timeout=5) as smtp:
            smtp.send_message(msg)
        process.terminate()
        process.wait(timeout=5)
        runtime = RapidInboxRuntime(settings)
        await runtime.start()
        try:
            mailbox = await runtime.get_mailbox_view("code@adb.com")
            assert mailbox["message_count"] == 1
        finally:
            await runtime.stop()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
```

- [ ] **Step 2: Run shutdown test to verify failure**

Run:

```bash
.venv/bin/pytest tests/test_cpp_ingestd_integration.py::test_cpp_ingestd_sigterm_drains_returned_250_mail -q
```

Expected: FAIL because `main.cpp` does not catch SIGTERM and drain.

- [ ] **Step 3: Implement signal-controlled drain**

Modify `cpp/ingestd/src/main.cpp`:

```cpp
#include <atomic>
#include <csignal>

namespace {
std::atomic<bool> g_stop_requested{false};

void request_stop(int) {
    g_stop_requested = true;
}
}

int main(int argc, char** argv) {
    std::signal(SIGTERM, request_stop);
    std::signal(SIGINT, request_stop);
    // keep existing argument parsing and config load
    // replace infinite loop with:
    while (!g_stop_requested) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    server.stop();
    app.stop_and_drain();
    std::cout << "rapid-inbox-ingestd stopped after drain\n";
    return 0;
}
```

Modify `SmtpServer::stop()` so it is idempotent by checking `listen_fd_ >= 0` before shutdown and safely joining only joinable threads. Keep current join logic.

- [ ] **Step 4: Run shutdown tests**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
.venv/bin/pytest tests/test_cpp_ingestd_integration.py -q
```

Expected: integration tests pass.

- [ ] **Step 5: Commit**

```bash
git add cpp/ingestd tests/test_cpp_ingestd_integration.py
git commit -m "feat: 支持 ingestd 正常停机 drain"
```

---

### Task 13: Documentation And Changelog

**Files:**
- Create: `cpp/ingestd/README.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write docs**

Create `cpp/ingestd/README.md`:

```markdown
# rapid-inbox-ingestd

`rapid-inbox-ingestd` is the C++ SMTP ingest process for Rapid Inbox.

Phase 1 accepts SMTP mail, returns `250 queued as <message_id>` after the message enters the in-memory queue, and batch-writes raw mail, recovery manifests, and SQLite pending records. The Python HTTP app remains responsible for admin/public UI and parsing pending messages.

## Build

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

## Run

```bash
SMTP_HOST=127.0.0.1 SMTP_PORT=2525 \
  cpp/ingestd/build/rapid-inbox-ingestd --base-dir .
```

## Durability Semantics

`250 queued` means the message is in the ingestd process memory queue. A normal SIGTERM/SIGINT stops accepting new connections and drains returned-250 mail to storage and SQLite before exit. A crash, kill -9, machine reboot, or power loss can lose messages that have not yet been written.
```

Add a short production note to `README.md` under startup modes:

```markdown
<details>
<summary><b>C++ SMTP ingestd + Python HTTP</b>（高吞吐生产模式）</summary>

```bash
# 1. 启动 Python HTTP，不启用内嵌 SMTP
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. 启动 C++ SMTP 收件入口
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
SMTP_HOST=0.0.0.0 SMTP_PORT=25 cpp/ingestd/build/rapid-inbox-ingestd --base-dir .
```

C++ ingestd 的 `250 queued` 表示邮件已进入内存队列；正常停止会 drain，异常崩溃或断电可能丢失尚未落盘的内存队列邮件。

</details>
```

Add to `CHANGELOG.md` under `[Unreleased]` / `新增`:

```markdown
- 规划并开始引入 C++ `rapid-inbox-ingestd` 高吞吐 SMTP 收件入口，保留 Python HTTP 后台与公开页面。
```

- [ ] **Step 2: Run docs checks**

Run:

```bash
git diff --check
rg -n "rapid-inbox-ingestd|250 queued|SIGTERM" README.md CHANGELOG.md cpp/ingestd/README.md
```

Expected: `git diff --check` has no output; `rg` shows the new docs entries.

- [ ] **Step 3: Commit**

```bash
git add README.md CHANGELOG.md cpp/ingestd/README.md
git commit -m "docs: 说明 ingestd 混合部署"
```

---

### Task 14: Full Verification And Performance Smoke

**Files:**
- No source changes expected unless verification exposes a defect.

- [ ] **Step 1: Run full C++ verification**

Run:

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

Expected: build succeeds and `100% tests passed`.

- [ ] **Step 2: Run targeted Python integration**

Run:

```bash
.venv/bin/pytest tests/test_cpp_ingestd_integration.py tests/test_ingest_pipeline.py tests/test_public_routes.py tests/test_admin_views.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run full Python regression**

Run:

```bash
.venv/bin/pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: Run manual throughput smoke**

Start the service against a temporary database seeded with `adb.com`, then send 1000 small messages with Python `smtplib` using a small script in `/tmp/rapid_inbox_bench.py`:

```python
import smtplib
import time
from email.message import EmailMessage

start = time.perf_counter()
for index in range(1000):
    msg = EmailMessage()
    msg["Subject"] = f"Bench {index}"
    msg["From"] = "sender@example.com"
    msg["To"] = f"code{index}@adb.com"
    msg.set_content("hello")
    with smtplib.SMTP("127.0.0.1", 2525, timeout=5) as smtp:
        smtp.send_message(msg)
elapsed = time.perf_counter() - start
print({"messages": 1000, "elapsed": elapsed, "messages_per_second": 1000 / elapsed})
```

Run:

```bash
python3 /tmp/rapid_inbox_bench.py
```

Expected: record the measured messages per second in the final implementation summary. If the smoke is below 1000/s, report the exact number and treat epoll or connection reuse as the next performance task instead of claiming the target is met.

- [ ] **Step 5: Final status**

Run:

```bash
git status --short --branch
git log --oneline -5
```

Expected: working tree clean; recent commits show the ingestd work.
