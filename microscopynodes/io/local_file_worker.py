import argparse
import importlib
import json
import sys
import traceback
from pathlib import Path


def worker_arguments():
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--package", required=True)
    return parser.parse_args(arguments)


def write_atomic(path, contents):
    path = Path(path)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(contents, encoding="utf-8")
    temporary_path.replace(path)


def main():
    arguments = worker_arguments()
    job_dir = Path(arguments.job_dir)
    data_model = importlib.import_module(f"{arguments.package}.data_model")
    generator = importlib.import_module(f"{arguments.package}.io.generate")
    progress = importlib.import_module(
        f"{arguments.package}.handle_blender_structs.progress_handling"
    )
    progress.set_progress_path(job_dir / "progress.txt")

    dataset = data_model.DatasetModel.model_validate_json(
        (job_dir / "request.json").read_text(encoding="utf-8")
    )
    generator.generate_local_files(dataset)
    write_atomic(job_dir / "result.json", dataset.model_dump_json())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        arguments = worker_arguments()
        write_atomic(
            Path(arguments.job_dir) / "error.json",
            json.dumps({"error": str(error), "traceback": traceback.format_exc()}),
        )
        raise
