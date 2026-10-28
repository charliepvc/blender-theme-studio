from pathlib import Path


def verify_saved_preferences(result, path):
    path = Path(path)
    if result != {"FINISHED"} or not path.is_file() or path.stat().st_size == 0:
        raise OSError("Il salvataggio delle preferenze non è stato verificato.")
