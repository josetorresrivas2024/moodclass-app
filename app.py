ValueError: Value of 'x' is not the name of a column in 'data_frame'. Expected one of ['emotion', 'count'] but received: index To use the index, pass it in directly as `df.index`.
Traceback:
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 129, in exec_func_with_error_handling
    result = func()
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 689, in code_to_exec
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/render/project/src/app.py", line 213, in <module>
    fig1 = px.bar(df["emotion"].value_counts().reset_index(), x="index", y="emotion", title="Frecuencia de Emociones")
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/plotly/express/_chart_types.py", line 381, in bar
    return make_figure(
        args=locals(),
    ...<2 lines>...
        layout_patch=dict(barmode=barmode),
    )
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/plotly/express/_core.py", line 2511, in make_figure
    args = build_dataframe(args, constructor)
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/plotly/express/_core.py", line 1757, in build_dataframe
    df_output, wide_id_vars = process_args_into_dataframe(
                              ~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        args,
        ^^^^^
    ...<4 lines>...
        native_namespace,
        ^^^^^^^^^^^^^^^^^
    )
    ^
File "/opt/render/project/src/.venv/lib/python3.14/site-packages/plotly/express/_core.py", line 1358, in process_args_into_dataframe
    raise ValueError(err_msg)
