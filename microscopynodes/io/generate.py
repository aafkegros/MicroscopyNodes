from ..handle_blender_structs.min_keys import min_keys
from .factories import DataIOFactory


def generate_local_files(dataset_model):
    for channel in dataset_model.channels:
        for output_type in (min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK):
            if not getattr(channel.viz, output_type.name.lower(), False):
                continue
            data_io = DataIOFactory(output_type)
            generated = channel.files_for(output_type)
            generated.constructors = data_io.make_local_files(channel)
            generated.metadata = data_io.get_metadata(generated.constructors)
    return dataset_model
