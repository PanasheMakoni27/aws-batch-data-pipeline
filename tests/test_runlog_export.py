from runlog_export import RUN_LOG_SCHEMA, rows_to_table


def test_empty_run_gives_empty_table_with_all_columns():
    table = rows_to_table([])
    assert table.num_rows == 0
    assert table.schema.names == RUN_LOG_SCHEMA.names


def test_one_row_round_trips():
    row = {"log_id": 1, "run_id": "abc", "table_name": "customers",
           "layer": "extract", "load_type": "incremental", "status": "SUCCESS",
           "rows_in": 1, "rows_out": 1}
    table = rows_to_table([row])
    assert table.num_rows == 1
    assert table.to_pylist()[0]["status"] == "SUCCESS"
    assert table.to_pylist()[0]["message"] is None
