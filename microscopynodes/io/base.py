from pathlib import Path


class DataIO:
    min_type = None
    TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "res{resolution}_c{channel_ix}_t{t}"

    def base_constructor(self, ch):
        cache_path = Path(ch.cache_path)
        return {
            "cache_path": str(cache_path),
            "cache_dir": str(cache_path.parent),
            "dataset_hash": cache_path.name,
            "original_path": ch.data.source,
        }

    def generate_file_constructors(self, ch):
        return []

    def export_ch(self, ch, file_constructors):
        return []

    def make_local_files(self, ch):
        file_constructors = self.generate_file_constructors(ch)
        self.export_ch(ch, file_constructors)
        return file_constructors

    def get_metadata(self, file_constructors):
        return {}
