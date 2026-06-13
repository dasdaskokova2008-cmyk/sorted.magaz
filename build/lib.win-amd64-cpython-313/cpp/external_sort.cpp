#include "external_sort.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <queue>
#include <sstream>
#include <stdexcept>
#include <vector>
#include <ctime>
#include <iomanip>

namespace fs = std::filesystem;

static fs::path to_path(const std::string& utf8_path) {
    return fs::u8path(utf8_path);
}

static void require_file(const std::string& path) {
    fs::path p = to_path(path);
    if (!fs::exists(p) || !fs::is_regular_file(p)) {
        throw std::runtime_error(
            "Файл не найден: " + path + ". Сначала нажми 'Сгенерировать' или выбери другой CSV."
        );
    }
}

struct Row {
    int product_id = 0;
    std::string product_name;
    double price = 0.0;
    int quantity = 0;
    std::time_t expiry_date = 0;
    std::string raw;
};

static int key_index(const std::string& sort_key) {
    if (sort_key == "product_name") return 1;
    if (sort_key == "price") return 2;
    if (sort_key == "quantity") return 3;
    if (sort_key == "expiry_date") return 4;
    return 0; // product_id
}

static std::time_t parse_date(const std::string& date_str) {
    std::tm tm = {};
    std::istringstream ss(date_str);
    ss >> std::get_time(&tm, "%Y-%m-%d");
    return std::mktime(&tm);
}

static bool less_by_key(const Row& a, const Row& b, int key) {
    if (key == 0) return a.product_id < b.product_id;
    if (key == 1) return a.product_name < b.product_name;
    if (key == 2) return a.price < b.price;
    if (key == 3) return a.quantity < b.quantity;
    return a.expiry_date < b.expiry_date;
}

static Row parse_row(const std::string& line) {
    Row r;
    r.raw = line;
    std::stringstream ss(line);
    std::string part;
    
    if (std::getline(ss, part, ',')) r.product_id = std::stoi(part);
    if (std::getline(ss, part, ',')) r.product_name = part;
    if (std::getline(ss, part, ',')) r.price = std::stod(part);
    if (std::getline(ss, part, ',')) r.quantity = std::stoi(part);
    if (std::getline(ss, part, ',')) r.expiry_date = parse_date(part);
    
    return r;
}

static long long file_size_bytes(const std::string& path) {
    require_file(path);
    return (long long)fs::file_size(to_path(path));
}

static long long memory_limit(const std::string& input_path) {
    long long sz = file_size_bytes(input_path);
    long long limit = sz / 10;
    if (limit < 5LL * 1024 * 1024) limit = 5LL * 1024 * 1024;
    return limit;
}

static std::vector<std::string> split_and_sort(
    const std::string& input_path,
    const std::string& temp_dir,
    int key,
    double& split_seconds
) {
    auto t0 = std::chrono::steady_clock::now();

    require_file(input_path);
    std::ifstream in(to_path(input_path));
    if (!in) {
        throw std::runtime_error("Не удалось открыть файл: " + input_path);
    }
    std::string header;
    std::getline(in, header);

    long long mem_limit = memory_limit(input_path);
    long long used = 0;
    int row_bytes = 30;
    int chunk_id = 0;
    std::vector<std::string> chunk_files;
    std::vector<Row> batch;

    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        if (batch.empty()) row_bytes = (int)line.size() + 1;

        batch.push_back(parse_row(line));
        used += row_bytes;

        if (used >= mem_limit) {
            std::sort(batch.begin(), batch.end(), [&](const Row& a, const Row& b) {
                return less_by_key(a, b, key);
            });

            fs::path chunk_path = to_path(temp_dir) / ("chunk_" + std::to_string(chunk_id) + ".tmp");
            std::ofstream out(chunk_path);
            for (const auto& r : batch) out << r.raw << "\n";
            out.close();

            chunk_files.push_back(chunk_path.u8string());
            chunk_id++;
            batch.clear();
            used = 0;
        }
    }

    if (!batch.empty()) {
        std::sort(batch.begin(), batch.end(), [&](const Row& a, const Row& b) {
            return less_by_key(a, b, key);
        });
        fs::path chunk_path = to_path(temp_dir) / ("chunk_" + std::to_string(chunk_id) + ".tmp");
        std::ofstream out(chunk_path);
        for (const auto& r : batch) out << r.raw << "\n";
        out.close();
        chunk_files.push_back(chunk_path.u8string());
    }

    in.close();
    auto t1 = std::chrono::steady_clock::now();
    split_seconds = std::chrono::duration<double>(t1 - t0).count();
    return chunk_files;
}

static double merge_chunks(
    const std::string& header,
    const std::vector<std::string>& chunk_files,
    const std::string& output_path,
    int key
) {
    auto t0 = std::chrono::steady_clock::now();

    std::vector<std::ifstream> files;
    std::vector<std::string> lines;
    files.reserve(chunk_files.size());
    lines.resize(chunk_files.size());

    for (const auto& p : chunk_files) {
        files.emplace_back(to_path(p));
    }

    struct PQItem {
        int idx;
        Row row;
    };

    auto pq_cmp = [&](const PQItem& a, const PQItem& b) {
        return less_by_key(b.row, a.row, key);
    };

    std::priority_queue<PQItem, std::vector<PQItem>, decltype(pq_cmp)> pq(pq_cmp);

    for (int i = 0; i < (int)files.size(); i++) {
        if (std::getline(files[i], lines[i])) {
            pq.push({i, parse_row(lines[i])});
        }
    }

    std::ofstream out(to_path(output_path));
    if (!out) {
        throw std::runtime_error("Не удалось создать файл: " + output_path);
    }
    out << "# " << header << "\n";

    while (!pq.empty()) {
        auto top = pq.top();
        pq.pop();
        out << top.row.raw << "\n";

        int i = top.idx;
        if (std::getline(files[i], lines[i])) {
            pq.push({i, parse_row(lines[i])});
        }
    }

    for (auto& f : files) f.close();
    out.close();

    auto t1 = std::chrono::steady_clock::now();
    return std::chrono::duration<double>(t1 - t0).count();
}

SortResult external_sort_cpp(
    const std::string& input_path,
    const std::string& output_path,
    const std::string& sort_key
) {
    SortResult result;
    result.sort_key = sort_key;
    int key = key_index(sort_key);

    require_file(input_path);

    std::string temp_dir = output_path + "_tmp_chunks";
    fs::create_directories(to_path(temp_dir));

    auto total0 = std::chrono::steady_clock::now();
    double split_time = 0.0;

    std::vector<std::string> chunks;
    try {
        chunks = split_and_sort(input_path, temp_dir, key, split_time);

        std::ifstream in(to_path(input_path));
        std::string header;
        std::getline(in, header);
        in.close();

        double merge_time = merge_chunks(header, chunks, output_path, key);

        result.split_seconds = split_time;
        result.merge_seconds = merge_time;
        result.chunks = (int)chunks.size();
    } catch (...) {
        fs::remove_all(to_path(temp_dir));
        throw;
    }

    fs::remove_all(to_path(temp_dir));

    auto total1 = std::chrono::steady_clock::now();
    result.total_seconds = std::chrono::duration<double>(total1 - total0).count();
    return result;
}

bool check_sorted_cpp(const std::string& file_path, const std::string& sort_key, int sample) {
    int key = key_index(sort_key);
    require_file(file_path);
    std::ifstream in(to_path(file_path));
    std::string line;

    Row prev;
    bool has_prev = false;
    int count = 0;

    while (std::getline(in, line) && count < sample) {
        if (line.empty() || line[0] == '#') continue;
        Row cur = parse_row(line);
        if (has_prev && less_by_key(cur, prev, key)) {
            return false;
        }
        prev = cur;
        has_prev = true;
        count++;
    }
    return true;
}

std::string read_preview_cpp(const std::string& file_path, int lines, bool from_end) {
    if (!fs::exists(to_path(file_path))) {
        return "Файл не найден";
    }
    std::ifstream in(to_path(file_path));
    if (!in) return "Файл не найден";

    if (!from_end) {
        std::string result;
        std::string line;
        int n = 0;
        while (std::getline(in, line) && n < lines) {
            if (!result.empty()) result += "\n";
            result += line;
            n++;
        }
        return result;
    }

    std::vector<std::string> all;
    std::string line;
    while (std::getline(in, line)) {
        all.push_back(line);
    }
    std::string result;
    int start = std::max(0, (int)all.size() - lines);
    for (int i = start; i < (int)all.size(); i++) {
        if (!result.empty()) result += "\n";
        result += all[i];
    }
    return result;
}