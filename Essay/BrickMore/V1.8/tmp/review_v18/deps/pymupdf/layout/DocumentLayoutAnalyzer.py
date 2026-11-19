from .MultiProcessWrapper import MultiProcessWrapper

__version__ = '260622'


def get_model(model_name='BoxRFDGNN', feature_set_name='imf+rf',
              input_type=None,
              config_path=None, model_path=None, imf_model_path=None,
              n_workers=1, use_gpu=False, use_sort=True,
              table_grid_model_ver='V4'):
    """
    Return a layout analysis model.

    Parameters
    ----------
    model_name           : currently only 'BoxRFDGNN' is supported
    feature_set_name     : feature set passed to BoxRFDGNN
    input_type           : '+'-separated input type string (e.g. 'text+image')
    config_path          : layout model YAML config path (None = auto)
    model_path           : layout model ONNX path        (None = auto)
    imf_model_path       : image feature ONNX path       (None = auto)
    n_workers            : number of worker processes.
                           1  -> MultiProcessWrapper (sequential, main process)
                           2+ -> MultiProcessWrapper (parallel, worker pool)
    table_grid_model_ver : table grid extractor version passed to BoxRFDGNN
                           one of V1, V1A, V1B, V2, V2A, V2B, V3, V4, V1T-A, V1T-B
    """
    if input_type is not None:
        input_type = tuple(input_type.split('+'))

    if model_name != 'BoxRFDGNN':
        raise Exception(f'Invalid model name = {model_name}')

    return MultiProcessWrapper(
        config_path          = config_path,
        model_path           = model_path,
        imf_model_path       = imf_model_path,
        feature_set_name     = feature_set_name,
        input_type           = input_type,
        n_workers            = n_workers,
        use_gpu              = use_gpu,
        use_sort             = use_sort,
        table_grid_model_ver = table_grid_model_ver,
    )
