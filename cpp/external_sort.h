#pragma once

#include <string>

struct SortResult {
    double split_seconds = 0.0;
    double merge_seconds = 0.0;
    double total_seconds = 0.0;
    std::string sort_key;
    int chunks = 0;
};

// sort_key: "product_id", "product_name", "price", "quantity", "expiry_date"
SortResult external_sort_cpp(
    const std::string& input_path,
    const std::string& output_path,
    const std::string& sort_key
);

bool check_sorted_cpp(const std::string& file_path, const std::string& sort_key, int sample = 100);
std::string read_preview_cpp(const std::string& file_path, int lines = 10, bool from_end = false);