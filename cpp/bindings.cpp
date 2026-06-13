#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "external_sort.h"

namespace py = pybind11;

PYBIND11_MODULE(external_sort_cpp, m) {
    m.doc() = "Внешняя сортировка на C++ для 5 колонок";

    py::class_<SortResult>(m, "SortResult")
        .def_readonly("split_seconds", &SortResult::split_seconds)
        .def_readonly("merge_seconds", &SortResult::merge_seconds)
        .def_readonly("total_seconds", &SortResult::total_seconds)
        .def_readonly("sort_key", &SortResult::sort_key)
        .def_readonly("chunks", &SortResult::chunks);

    m.def("external_sort", &external_sort_cpp,
          py::arg("input_path"),
          py::arg("output_path"),
          py::arg("sort_key") = "product_id",
          "Сортировка CSV файла (5 колонок: product_id, product_name, price, quantity, expiry_date)");

    m.def("check_sorted", &check_sorted_cpp,
          py::arg("file_path"),
          py::arg("sort_key"),
          py::arg("sample") = 100,
          "Проверка сортировки");

    m.def("read_preview", &read_preview_cpp,
          py::arg("file_path"),
          py::arg("lines") = 10,
          py::arg("from_end") = false,
          "Показать часть файла");
}
